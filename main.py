#!/usr/bin/env python
# pyright: reportUnusedVariable=false, reportGeneralTypeIssues=false
"""

Hit RUN to execute the program.

You can also deploy a stable, public version of your project, unaffected by the changes you make in the workspace.

This proof-of-concept Telegram bot takes a user's text messages and turns them into stylish images. Utilizing Python, the `python-telegram-bot` library, and PIL for image manipulation, it offers a quick and interactive way to generate content.

Read the README.md file for more information on how to get and deploy Telegram bots.
"""

import logging

from telegram import __version__ as TG_VER

try:
  from telegram import __version_info__
except ImportError:
  __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
  raise RuntimeError(
      f"This example is not compatible with your current PTB version {TG_VER}. To view the "
      f"{TG_VER} version of this example, "
      f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html")

from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from PIL import Image, ImageDraw, ImageFont
import os

my_bot_token = os.environ['BOT_TOKEN']

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# Define a few command handlers. These usually take the two arguments update and
# context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  """Send a message when the command /start is issued."""
  user = update.effective_user
  await update.message.reply_html(
      rf"Hi {user.mention_html()}!",
      reply_markup=ForceReply(selective=True),
  )


async def help_command(update: Update,
                       context: ContextTypes.DEFAULT_TYPE) -> None:
  """Send a message when the command /help is issued."""
  help_text = """
ðŸ¤– Quiz Bot Commands:

ðŸ“¤ Upload a .txt file with MCQ questions to create automatic quiz polls!

ðŸ“ Text File Format:
Q: Your question here?
A) Option 1
B) Option 2  
C) Option 3
D) Option 4
Answer: A
Explanation: Optional explanation

You can also send text messages to create stylized images.
  """
  await update.message.reply_text(help_text)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  """Handle text file uploads and create quiz polls"""
  document = update.message.document
  
  if document.mime_type != 'text/plain':
    await update.message.reply_text("Please send a text file (.txt) containing MCQ questions.")
    return
  
  # Download the file
  file = await context.bot.get_file(document.file_id)
  await file.download_to_drive('quiz_questions.txt')
  
  # Read and parse questions
  try:
    with open('quiz_questions.txt', 'r', encoding='utf-8') as f:
      content = f.read()
    
    questions = parse_mcq_questions(content)
    
    if not questions:
      await update.message.reply_text("No valid MCQ questions found in the file. Please check the format.")
      return
    
    await update.message.reply_text(f"Found {len(questions)} questions. Creating polls...")
    
    # Create polls for each question
    for i, question in enumerate(questions):
      poll_message = await context.bot.send_poll(
        chat_id=update.effective_chat.id,
        question=question['question'],
        options=question['options'],
        type='quiz',
        correct_option_id=question['correct_answer'],
        is_anonymous=False,
        explanation=question.get('explanation', '')
      )
      
  except Exception as e:
    await update.message.reply_text(f"Error processing file: {str(e)}")

def parse_mcq_questions(content):
  """Parse MCQ questions from text content"""
  questions = []
  lines = content.strip().split('\n')
  current_question = None
  options = []
  correct_answer = None
  explanation = ""
  
  for line in lines:
    line = line.strip()
    if not line:
      continue
      
    # Question line (starts with Q: or Question:)
    if line.startswith('Q:') or line.startswith('Question:'):
      # Save previous question if exists
      if current_question and options:
        questions.append({
          'question': current_question,
          'options': options,
          'correct_answer': correct_answer or 0,
          'explanation': explanation
        })
      
      # Start new question
      current_question = line.split(':', 1)[1].strip()
      options = []
      correct_answer = None
      explanation = ""
      
    # Option lines (A, B, C, D)
    elif line.startswith(('A)', 'B)', 'C)', 'D)', 'a)', 'b)', 'c)', 'd)')):
      option_text = line[2:].strip()
      options.append(option_text)
      
    # Correct answer line
    elif line.startswith('Answer:') or line.startswith('Correct:'):
      answer_text = line.split(':', 1)[1].strip().upper()
      if answer_text in ['A', 'B', 'C', 'D']:
        correct_answer = ord(answer_text) - ord('A')
      elif answer_text.isdigit():
        correct_answer = int(answer_text) - 1
        
    # Explanation line
    elif line.startswith('Explanation:'):
      explanation = line.split(':', 1)[1].strip()
  
  # Add the last question
  if current_question and options:
    questions.append({
      'question': current_question,
      'options': options,
      'correct_answer': correct_answer or 0,
      'explanation': explanation
    })
  
  return questions

async def stylize(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
  user_message = update.message.text
  if user_message is None:
    await update.message.reply_text("Please send text to stylize or upload a .txt file with MCQ questions for quiz!")
    return

  img = Image.new('RGB', (500, 200), color=(73, 109, 137))
  d = ImageDraw.Draw(img)
  fnt = ImageFont.load_default()
  d.text((50, 90), user_message, font=fnt, fill=(255, 255, 0))

  img.save('styled_text.png')
  with open('styled_text.png', 'rb') as photo:
    await update.message.reply_photo(photo=photo)


def main() -> None:
  """Start the bot."""
  # Create the Application and pass it your bot's token.
  application = Application.builder().token(my_bot_token).build()

  # on different commands - answer in Telegram
  application.add_handler(CommandHandler("start", start))
  application.add_handler(CommandHandler("help", help_command))

  # on document upload - handle quiz creation
  application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

  # on non command i.e message - echo the message on Telegram
  application.add_handler(
      MessageHandler(filters.TEXT & ~filters.COMMAND, stylize))

  # Run the bot until the user presses Ctrl-C
  application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
  main()
