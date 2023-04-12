# Badger - A LinkedIn Skill Assessment Quiz Bot

LinkedIn Skill Assessment Quiz Bot is a Python script that automates the process of taking LinkedIn Skill Assessment quizzes. The bot uses Selenium for logging into LinkedIn and collecting data for quiz questions, along with PyAutoGUI and OpenCV for interacting with ChatGPT via the free version of chat.openai.com.



https://user-images.githubusercontent.com/77811876/231528188-ab2de73f-c18e-4080-bd97-501f04fa1253.mp4



## Features
- Automates the process of taking LinkedIn Skill Assessment quizzes
- Built-in support for answering quiz questions using ChatGPT
- Works with the free version of chat.openai.com
- Supports both normal and practice mode quizzes

## Requirements
- Python 3
- OpenAI account
- LinkedIn account
- Firefox

## Setup
- Fill out the `config.py` file.
- Ensure you have an OpenAI account and are logged in. Opening your browser and navigating to "chat.openai.com" should yield the chat interface page, and not prompt you for a login or redirect you.
- Once the script is run, it may require one more piece of additional input from the user to complete the captcha while logging into LinkedIn. You do not have to click the "VERIFY" button; you DO have to click the correct image when asked.

## Usage
1. Run the script using the following command: python main.py
