# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container
COPY . .

# Environment variables
ENV TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
ENV LOGIN_URL=https://example.com/login
ENV COURSE_URL=https://example.com/course
ENV WEBSITE_USERNAME=your_username
ENV WEBSITE_PASSWORD=your_password

# Run the bot script
CMD ["python", "main.py"]
