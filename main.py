import telebot
import requests
from bs4 import BeautifulSoup
import os

# Replace with your Telegram Bot Token
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_TELEGRAM_BOT_TOKEN')

# Replace with your website's login URL and course URL
LOGIN_URL = os.getenv('LOGIN_URL', 'https://example.com/login')
COURSE_URL = os.getenv('COURSE_URL', 'https://example.com/course')

# Initialize the bot
bot = telebot.TeleBot(BOT_TOKEN)

# Session to persist cookies
session = requests.Session()

# Global variables to store credentials
user_credentials = {}

# Function to log in to the website
def login(username, password):
    login_data = {
        'username': username,
        'password': password
    }
    response = session.post(LOGIN_URL, data=login_data)
    if response.status_code == 200:
        return True
    else:
        return False

# Function to extract video and PDF links
def extract_links():
    response = session.get(COURSE_URL)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Extract video links (adjust selectors as needed)
    video_links = [a['href'] for a in soup.select('a[href*="video"]')]
    
    # Extract PDF links (adjust selectors as needed)
    pdf_links = [a['href'] for a in soup.select('a[href*="pdf"]')]
    
    return video_links, pdf_links

# Function to save links to a text file
def save_links_to_file(video_links, pdf_links, filename='course_links.txt'):
    with open(filename, 'w') as f:
        f.write("Video Links:\n")
        for link in video_links:
            f.write(link + '\n')
        f.write("\nPDF Links:\n")
        for link in pdf_links:
            f.write(link + '\n')

# Telegram bot command: /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Welcome! Use /setcredentials to set your username and password.")

# Telegram bot command: /setcredentials
@bot.message_handler(commands=['setcredentials'])
def ask_for_credentials(message):
    msg = bot.reply_to(message, "Please enter your username and password in the format:\n`username:password`")
    bot.register_next_step_handler(msg, process_credentials)

# Process credentials input
def process_credentials(message):
    try:
        credentials = message.text.split(':')
        if len(credentials) != 2:
            bot.reply_to(message, "Invalid format. Please use `username:password`.")
            return
        
        username, password = credentials
        user_credentials['username'] = username.strip()
        user_credentials['password'] = password.strip()
        
        bot.reply_to(message, "Credentials saved successfully! Use /login to log in.")
    except Exception as e:
        bot.reply_to(message, f"An error occurred: {e}")

# Telegram bot command: /login
@bot.message_handler(commands=['login'])
def handle_login(message):
    if 'username' not in user_credentials or 'password' not in user_credentials:
        bot.reply_to(message, "Credentials not set. Use /setcredentials first.")
        return
    
    if login(user_credentials['username'], user_credentials['password']):
        bot.reply_to(message, "Logged in successfully!")
    else:
        bot.reply_to(message, "Failed to log in. Please check your credentials.")

# Telegram bot command: /getlinks
@bot.message_handler(commands=['getlinks'])
def handle_getlinks(message):
    if 'username' not in user_credentials or 'password' not in user_credentials:
        bot.reply_to(message, "Credentials not set. Use /setcredentials first.")
        return
    
    if not login(user_credentials['username'], user_credentials['password']):
        bot.reply_to(message, "Failed to log in. Please check your credentials.")
        return
    
    video_links, pdf_links = extract_links()
    if video_links or pdf_links:
        save_links_to_file(video_links, pdf_links)
        bot.reply_to(message, "Links extracted and saved to course_links.txt")
    else:
        bot.reply_to(message, "No links found.")

# Start the bot
if __name__ == '__main__':
    bot.polling()
