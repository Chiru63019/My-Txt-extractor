
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from utils import setup_logger
from handlers import start, login, extract_course, cancel
from config import TELEGRAM_BOT_TOKEN, LOGIN, COURSE_SELECTION

logger = setup_logger()

class TelegramBot:
    def __init__(self):
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self._setup_handlers()

    def _setup_handlers(self):
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, login)],
                COURSE_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, extract_course)],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )
        self.application.add_handler(conv_handler)

    def run(self):
        self.application.run_polling()
