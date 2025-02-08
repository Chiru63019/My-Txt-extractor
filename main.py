# core.py
import os
import logging
import asyncio
import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import aiohttp
from bs4 import BeautifulSoup

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# States
LOGIN, COURSE_SELECTION = range(2)

class TelegramBot:
    def __init__(self, token='YOUR_TELEGRAM_BOT_TOKEN'):
        self.token = token
        self.application = None
        self.user_data = {}

    async def start(self, update: telegram.Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.message.reply_text(
            "Welcome! Please send your login credentials in this format:\n"
            "email password"
        )
        return LOGIN

    async def login(self, update: telegram.Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        credentials = update.message.text.split()

        if len(credentials) != 2:
            await update.message.reply_text(
                "Please provide both email and password separated by space."
            )
            return LOGIN

        email, password = credentials

        # Store credentials in user_data
        context.user_data['credentials'] = {'email': email, 'password': password}

        # Login to the website
        async with aiohttp.ClientSession() as session:
            try:
                # First get the login page to get any CSRF token if needed
                async with session.get(
                        'https://app.khanglobalstudies.com/login') as response:
                    html = await response.text()

                # Perform login
                login_data = {'email': email, 'password': password}
                async with session.post('https://app.khanglobalstudies.com/login',
                                        data=login_data) as response:
                    if response.status == 200:
                        # Get course list
                        async with session.get(
                                'https://app.khanglobalstudies.com/dashboard'
                        ) as courses_response:
                            courses_html = await courses_response.text()
                            soup = BeautifulSoup(courses_html, 'html.parser')
                            courses = soup.find_all(
                                'div', class_='course-card'
                            )  # Adjust class based on actual HTML

                            course_list = []
                            for course in courses:
                                course_id = course.get(
                                    'data-course-id',
                                    ''
                                )  # Adjust based on actual HTML
                                course_name = course.find('h3').text.strip(
                                )  # Adjust based on actual HTML
                                course_list.append(
                                    f"ID: {course_id} - {course_name}"
                                )

                            context.user_data['courses'] = course_list

                            await update.message.reply_text(
                                "Here are your courses:\n" +
                                "\n".join(course_list) +
                                "\n\nPlease send the course ID you want to extract:"
                            )
                            return COURSE_SELECTION
                    else:
                        await update.message.reply_text(
                            "Login failed. Please try again with correct credentials."
                        )
                        return LOGIN

            except Exception as e:
                logger.error(f"Error during login: {e}")
                await update.message.reply_text(
                    "An error occurred. Please try again."
                )
                return LOGIN

    async def extract_course(self, update: telegram.Update,
                             context: ContextTypes.DEFAULT_TYPE) -> int:
        course_id = update.message.text.strip()

        async with aiohttp.ClientSession() as session:
            try:
                # Use stored credentials
                credentials = context.user_data['credentials']

                # Login again to ensure session is valid
                login_data = {
                    'email': credentials['email'],
                    'password': credentials['password']
                }
                await session.post('https://app.khanglobalstudies.com/login',
                                   data=login_data)

                # Get course content
                async with session.get(
                        f'https://app.khanglobalstudies.com/course/{course_id}'
                ) as response:
                    course_html = await response.text()
                    soup = BeautifulSoup(course_html, 'html.parser')

                    # Extract links (adjust selectors based on actual HTML)
                    video_links = [
                        a['href'] for a in soup.find_all('a', href=True)
                        if 'video' in a['href'].lower()
                    ]
                    pdf_links = [
                        a['href'] for a in soup.find_all('a', href=True)
                        if '.pdf' in a['href'].lower()
                    ]

                    # Create text file with links
                    with open(f'course_{course_id}_links.txt', 'w') as f:
                        f.write("Video Links:\n")
                        f.write('\n'.join(video_links))
                        f.write("\n\nPDF Links:\n")
                        f.write('\n'.join(pdf_links))

                    # Send file to user
                    await update.message.reply_document(
                        document=open(f'course_{course_id}_links.txt', 'rb'),
                        filename=f'course_{course_id}_links.txt'
                    )

                    # Cleanup
                    os.remove(f'course_{course_id}_links.txt')

                    await update.message.reply_text(
                        "Extraction complete! You can start a new extraction with /start"
                    )
                    return ConversationHandler.END

            except Exception as e:
                logger.error(f"Error during course extraction: {e}")
                await update.message.reply_text(
                    "An error occurred. Please try again with /start"
                )
                return ConversationHandler.END

    async def cancel(self, update: telegram.Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.message.reply_text(
            "Operation cancelled. Use /start to begin again."
        )
        return ConversationHandler.END

    def run(self):
        # Create application
        self.application = Application.builder().token(self.token).build()

        # Add conversation handler
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.login)],
                COURSE_SELECTION:
                [MessageHandler(filters.TEXT & ~filters.COMMAND, self.extract_course)],
            },
            fallbacks=[CommandHandler('cancel', self.cancel)],
        )

        self.application.add_handler(conv_handler)

        # Run the bot
        self.application.run_polling()


# main.py
from core import TelegramBot

from aiohttp import web
import asyncio

async def health_check(request):
    return web.Response(text='OK')

async def run_web_server():
    app = web.Application()
    app.router.add_get('/health', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()

async def main():
    bot = TelegramBot()
    
    # Start both the bot and web server
    await asyncio.gather(
        run_web_server(),
        bot.application.run_polling(allowed_updates=Update.ALL_TYPES)
    )

if __name__ == '__main__':
    asyncio.run(main())
