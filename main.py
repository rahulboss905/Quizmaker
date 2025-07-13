import logging
import re
import os
from telegram import Update, Poll
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_mcqs(text):
    pattern = re.compile(
        r"Q\d*[:\.]?\s*(.*?)\n"
        r"A[\)\.]?\s*(.*?)\n"
        r"B[\)\.]?\s*(.*?)\n"
        r"C[\)\.]?\s*(.*?)\n"
        r"D[\)\.]?\s*(.*?)\n"
        r"Answer[:\.]?\s*([A-Da-d])",
        re.MULTILINE
    )
    mcqs = []
    for match in pattern.findall(text):
        q, a, b, c, d, ans = match
        correct_index = ord(ans.lower()) - ord('a')
        mcqs.append({
            "question": q.strip(),
            "options": [a.strip(), b.strip(), c.strip(), d.strip()],
            "correct": correct_index
        })
    return mcqs

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send a .txt file with MCQs to start the quiz.")

async def handle_txt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text("❌ Only .txt files are supported.")
        return

    file = await document.get_file()
    path = await file.download_to_drive()

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    mcqs = parse_mcqs(text)
    if not mcqs:
        await update.message.reply_text("❌ Couldn’t parse any questions. Check the format.")
        return

    for i, mcq in enumerate(mcqs, 1):
        try:
            await context.bot.send_poll(
                chat_id=update.effective_chat.id,
                question=f"Q{i}: {mcq['question']}",
                options=mcq['options'],
                type=Poll.QUIZ,
                correct_option_id=mcq['correct'],
                is_anonymous=False
            )
        except Exception as e:
            await update.message.reply_text(f"⚠️ Failed to send Q{i}: {e}")
            continue

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.FILE_EXTENSION("txt"), handle_txt))

    print("✅ Bot is running on Render")
    app.run_polling()