#!/usr/bin/env python
# pyright: reportUnusedVariable=false, reportGeneralTypeIssues=false

import logging
import os
import random
from typing import List, Dict

from telegram import Update, Poll, __version__ as TG_VER

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )

from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, PollAnswerHandler

my_bot_token = os.environ['BOT_TOKEN']

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Store quiz questions
quiz_questions = []

def load_quiz_questions(file_path: str) -> List[Dict]:
    """Load quiz questions from a text file."""
    questions = []
    if not os.path.exists(file_path):
        logger.warning(f"Quiz file {file_path} not found")
        return questions

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read().strip()
        question_blocks = content.split('\n\n')

        for block in question_blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 6:
                question_text = lines[0]
                options = []
                correct_answer = None

                for i in range(1, 5):
                    if i < len(lines):
                        option = lines[i].strip()
                        if option.startswith(('A)', 'B)', 'C)', 'D)')):
                            options.append(option[2:].strip())

                if len(lines) > 5:
                    correct_line = lines[5].strip()
                    if correct_line.startswith('Correct:'):
                        correct_letter = correct_line.split(':')[1].strip().upper()
                        correct_mapping = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
                        correct_answer = correct_mapping.get(correct_letter, 0)

                if len(options) >= 2:
                    questions.append({
                        'question': question_text,
                        'options': options,
                        'correct_answer': correct_answer if correct_answer is not None else 0
                    })

    except Exception as e:
        logger.error(f"Error loading quiz questions: {e}")

    return questions

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! 🧠 Welcome to the Quiz Bot!

"
        "Commands:
"
        "/quiz - Get a random quiz question
"
        "/help - Show this help message
"
        "/reload - Reload questions from file

"
        "📎 You can also send me a .txt file with your own quiz!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = """
🧠 Quiz Bot Commands:

/start - Welcome message
/quiz - Get a random quiz question
/reload - Reload questions from quiz.txt file
/help - Show this help message

📎 Or upload a .txt file with this format:

What is the capital of France?
A) London
B) Berlin
C) Paris
D) Madrid
Correct: C

Separate each question block with a blank line.
    """
    await update.message.reply_text(help_text)

async def reload_questions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global quiz_questions
    quiz_questions = load_quiz_questions('quiz.txt')
    if quiz_questions:
        await update.message.reply_text(f"✅ Loaded {len(quiz_questions)} questions from quiz.txt")
    else:
        await update.message.reply_text("❌ No questions found or file missing.")

async def send_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not quiz_questions:
        await update.message.reply_text("❌ No quiz questions loaded. Use /reload or upload a .txt file.")
        return
    question_data = random.choice(quiz_questions)
    await update.message.reply_poll(
        question=question_data['question'],
        options=question_data['options'],
        type=Poll.QUIZ,
        correct_option_id=question_data['correct_answer'],
        is_anonymous=False,
        allows_multiple_answers=False
    )

async def poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    answer = update.poll_answer
    user = answer.user
    if answer.option_ids:
        selected_option = answer.option_ids[0]
        logger.info(f"User {user.username} selected option {selected_option}")

async def handle_quiz_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global quiz_questions
    document = update.message.document
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text("❌ Please upload a .txt file only.")
        return
    try:
        file = await document.get_file()
        file_path = f"/tmp/{document.file_name}"
        await file.download_to_drive(file_path)
        quiz_questions = load_quiz_questions(file_path)
        if quiz_questions:
            await update.message.reply_text(f"✅ Loaded {len(quiz_questions)} questions from {document.file_name}. Use /quiz to begin.")
        else:
            await update.message.reply_text("⚠️ File loaded but no valid quiz questions found.")
    except Exception as e:
        logger.error(f"Error processing uploaded file: {e}")
        await update.message.reply_text("❌ Failed to process the file.")

def main() -> None:
    global quiz_questions
    quiz_questions = load_quiz_questions('quiz.txt')
    application = Application.builder().token(my_bot_token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("quiz", send_quiz))
    application.add_handler(CommandHandler("reload", reload_questions))
    application.add_handler(PollAnswerHandler(poll_answer))
    application.add_handler(MessageHandler(filters.Document.MIME_TYPE("text/plain"), handle_quiz_file_upload))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
        
