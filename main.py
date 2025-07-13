# main.py
import os
from flask import Flask, request
from telegram import Update, Bot
from telegram.constants import ParseMode
from telegram.ext import Dispatcher, MessageHandler, filters
from telegram.ext import Application, ApplicationBuilder
import re

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dispatcher = Dispatcher(bot=bot, update_queue=None, workers=1)


# Parse MCQ questions from .txt
def parse_mcqs(text):
    pattern = re.compile(
        r"Q\d*[:.]\s*(.*?)\nA\)\s*(.*?)\nB\)\s*(.*?)\nC\)\s*(.*?)\nD\)\s*(.*?)\nAnswer:\s*([A-Da-d])",
        re.DOTALL
    )
    return pattern.findall(text)


# Handle .txt file upload
async def handle_doc(update: Update, context):
    doc = update.message.document
    if not doc.file_name.endswith(".txt"):
        await update.message.reply_text("Only .txt files are accepted.")
        return

    file = await doc.get_file()
    file_path = f"/tmp/{doc.file_unique_id}.txt"
    await file.download_to_drive(file_path)

    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    questions = parse_mcqs(content)
    if not questions:
        await update.message.reply_text("Couldn't parse any MCQs.")
        return

    for q in questions:
        question, a, b, c, d, ans = [x.strip() for x in q]
        options = [a, b, c, d]
        correct_index = ord(ans.lower()) - ord("a")

        await bot.send_poll(
            chat_id=update.effective_chat.id,
            question=question,
            options=options,
            type="quiz",
            correct_option_id=correct_index,
            is_anonymous=False
        )


handler = MessageHandler(filters.Document.ALL, handle_doc)
dispatcher.add_handler(handler)


@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"


@app.route("/")
def index():
    return "Bot is running"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
    
