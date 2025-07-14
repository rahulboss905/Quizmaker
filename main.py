
#!/usr/bin/env python
# pyright: reportUnusedVariable=false, reportGeneralTypeIssues=false
"""
Telegram Quiz Bot

This bot reads quiz questions from a text file and sends them as polls to users.
Text file format should be:
Question text?
A) Option 1
B) Option 2
C) Option 3
D) Option 4
Correct: A

Hit RUN to execute the program.
"""

import logging
import os
import random
from typing import List, Dict

from telegram import __version__ as TG_VER

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )

from telegram import Update, Poll
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, PollAnswerHandler

my_bot_token = os.environ['YOUR_BOT_TOKEN']

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

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
            
        # Split by double newlines to separate questions
        question_blocks = content.split('\n\n')
        
        for block in question_blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 6:  # Question + 4 options + correct answer
                question_text = lines[0]
                options = []
                correct_answer = None
                
                # Parse options (A, B, C, D)
                for i in range(1, 5):
                    if i < len(lines):
                        option = lines[i].strip()
                        if option.startswith(('A)', 'B)', 'C)', 'D)')):
                            options.append(option[2:].strip())
                
                # Parse correct answer
                if len(lines) > 5:
                    correct_line = lines[5].strip()
                    if correct_line.startswith('Correct:'):
                        correct_letter = correct_line.split(':')[1].strip().upper()
                        correct_mapping = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
                        correct_answer = correct_mapping.get(correct_letter, 0)
                
                if len(options) >= 2:  # At least 2 options required for a poll
                    questions.append({
                        'question': question_text,
                        'options': options,
                        'correct_answer': correct_answer if correct_answer is not None else 0
                    })
    
    except Exception as e:
        logger.error(f"Error loading quiz questions: {e}")
    
    return questions


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! ðŸ§  Welcome to the Quiz Bot!\n\n"
        "Commands:\n"
        "/quiz - Get a random quiz question\n"
        "/help - Show this help message\n"
        "/reload - Reload questions from file"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = """
ðŸ§  Quiz Bot Commands:

/start - Welcome message
/quiz - Get a random quiz question
/reload - Reload questions from quiz.txt file
/help - Show this help message

ðŸ“ Quiz file format (quiz.txt):
```
What is the capital of France?
A) London
B) Berlin
C) Paris
D) Madrid
Correct: C

What is 2 + 2?
A) 3
B) 4
C) 5
D) 6
Correct: B
```

Make sure to separate questions with a blank line!
    """
    await update.message.reply_text(help_text)


async def reload_questions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reload questions from the quiz file."""
    global quiz_questions
    quiz_questions = load_quiz_questions('quiz.txt')
    
    if quiz_questions:
        await update.message.reply_text(f"âœ… Loaded {len(quiz_questions)} questions from quiz.txt")
    else:
        await update.message.reply_text("âŒ No questions found. Make sure quiz.txt exists and is properly formatted.")


async def send_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a quiz poll to the user."""
    if not quiz_questions:
        await update.message.reply_text("âŒ No quiz questions available. Use /reload to load questions from quiz.txt")
        return
    
    # Select a random question
    question_data = random.choice(quiz_questions)
    
    # Send poll
    await update.message.reply_poll(
        question=question_data['question'],
        options=question_data['options'],
        type=Poll.QUIZ,
        correct_option_id=question_data['correct_answer'],
        is_anonymous=False,
        allows_multiple_answers=False
    )


async def poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle poll answers."""
    answer = update.poll_answer
    user = answer.user
    
    if answer.option_ids:
        selected_option = answer.option_ids[0]
        logger.info(f"User {user.username} selected option {selected_option}")


def main() -> None:
    """Start the bot."""
    global quiz_questions
    
    # Load quiz questions on startup
    quiz_questions = load_quiz_questions('quiz.txt')
    logger.info(f"Loaded {len(quiz_questions)} quiz questions")
    
    # Create the Application
    application = Application.builder().token(my_bot_token).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("quiz", send_quiz))
    application.add_handler(CommandHandler("reload", reload_questions))
    
    # Add poll answer handler
    application.add_handler(PollAnswerHandler(poll_answer))

    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
