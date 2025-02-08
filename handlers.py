
import aiohttp
from bs4 import BeautifulSoup
import os
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from config import LOGIN, COURSE_SELECTION
from utils import setup_logger

logger = setup_logger()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Welcome! Please send your login credentials in this format:\n"
        "email password"
    )
    return LOGIN

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    credentials = update.message.text.split()
    
    if len(credentials) != 2:
        await update.message.reply_text("Please provide both email and password separated by space.")
        return LOGIN
    
    email, password = credentials
    context.user_data['credentials'] = {'email': email, 'password': password}
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get('https://app.khanglobalstudies.com/login') as response:
                html = await response.text()
            
            login_data = {'email': email, 'password': password}
            async with session.post('https://app.khanglobalstudies.com/login', data=login_data) as response:
                if response.status == 200:
                    courses = await fetch_courses(session)
                    context.user_data['courses'] = courses
                    await update.message.reply_text(
                        "Here are your courses:\n" + "\n".join(courses) +
                        "\n\nPlease send the course ID you want to extract:"
                    )
                    return COURSE_SELECTION
                else:
                    await update.message.reply_text("Login failed. Please try again with correct credentials.")
                    return LOGIN
                    
        except Exception as e:
            logger.error(f"Error during login: {e}")
            await update.message.reply_text("An error occurred. Please try again.")
            return LOGIN

async def extract_course(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    course_id = update.message.text.strip()
    
    async with aiohttp.ClientSession() as session:
        try:
            credentials = context.user_data['credentials']
            login_data = {'email': credentials['email'], 'password': credentials['password']}
            await session.post('https://app.khanglobalstudies.com/login', data=login_data)
            
            links = await fetch_course_links(session, course_id)
            filename = f'course_{course_id}_links.txt'
            
            with open(filename, 'w') as f:
                f.write(links)
            
            await update.message.reply_document(
                document=open(filename, 'rb'),
                filename=filename
            )
            
            os.remove(filename)
            await update.message.reply_text("Extraction complete! You can start a new extraction with /start")
            return ConversationHandler.END
                
        except Exception as e:
            logger.error(f"Error during course extraction: {e}")
            await update.message.reply_text("An error occurred. Please try again with /start")
            return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operation cancelled. Use /start to begin again.")
    return ConversationHandler.END

async def fetch_courses(session):
    async with session.get('https://app.khanglobalstudies.com/dashboard') as response:
        html = await response.text()
        soup = BeautifulSoup(html, 'html.parser')
        courses = soup.find_all('div', class_='course-card')
        return [f"ID: {course.get('data-course-id', '')} - {course.find('h3').text.strip()}" 
                for course in courses]

async def fetch_course_links(session, course_id):
    async with session.get(f'https://app.khanglobalstudies.com/course/{course_id}') as response:
        html = await response.text()
        soup = BeautifulSoup(html, 'html.parser')
        video_links = [a['href'] for a in soup.find_all('a', href=True) if 'video' in a['href'].lower()]
        pdf_links = [a['href'] for a in soup.find_all('a', href=True) if '.pdf' in a['href'].lower()]
        
        return "Video Links:\n" + '\n'.join(video_links) + "\n\nPDF Links:\n" + '\n'.join(pdf_links)
