# main.py

import os
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application, MessageHandler, CommandHandler,
    ContextTypes, filters
)
import re
import asyncio

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

app = Flask(__name__)
bot_app = Application.builder().token(TOKEN).build()

def parse_mcqs(text):
    pattern = re.compile(r"Q\d*: (.*?)\nA\) (.*?)\nB\) (.*?)\nC\) (.*?)\nD\) (.*?)\nAnswer: ([ABCD])", re.DOTALL)
    return pattern.findall(text)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send a .txt file containing MCQs.")

async def handle_txt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text("Please upload a .txt file.")
        return

    file = await context.bot.get_file(document.file_id)
    content = await file.download_as_bytearray()
    text = content.decode("utf-8")
    mcqs = parse_mcqs(text)

    if not mcqs:
        await update.message.reply_text("Couldn't parse any MCQs.")
        return

    for idx, (q, a, b, c, d, ans) in enumerate(mcqs):
        options = [a, b, c, d]
        correct_idx = ["A", "B", "C", "D"].index(ans.strip())
        await context.bot.send_poll(
            chat_id=update.effective_chat.id,
            question=f"Q{idx+1}: {q.strip()}",
            options=options,
            type='quiz',
            correct_option_id=correct_idx,
            is_anonymous=False
        )
        await asyncio.sleep(1.2)  # Rate-limit for safety

bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.Document.ALL, handle_txt))

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot_app.bot)
    bot_app.update_queue.put_nowait(update)
    return "OK", 200

@app.route("/", methods=["GET"])
def home():
    return "Bot is running!", 200

async def set_webhook():
    await bot_app.bot.set_webhook(f"{WEBHOOK_URL}/{TOKEN}")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(set_webhook())
    bot_app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        webhook_url=f"{WEBHOOK_URL}/{TOKEN}",
    )
    
