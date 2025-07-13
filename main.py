import os
import logging
from fastapi import FastAPI, Request
from telegram import Update, Bot, Poll
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from telegram.ext import AIORateLimiter
from telegram.constants import ParseMode
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

app = FastAPI()
bot = Bot(token=BOT_TOKEN)

# ========== MCQ Parser ==========
import re

def parse_mcqs(text):
    pattern = re.compile(r"Q\d*[:\-\.]?\s*(.*?)\s*(?:\n|\r\n)"
                         r"A\)\s*(.*?)\s*(?:\n|\r\n)"
                         r"B\)\s*(.*?)\s*(?:\n|\r\n)"
                         r"C\)\s*(.*?)\s*(?:\n|\r\n)"
                         r"D\)\s*(.*?)\s*(?:\n|\r\n)"
                         r"Answer[:\-\.]?\s*([ABCD])", re.IGNORECASE)
    questions = pattern.findall(text)
    return [{
        "question": q.strip(),
        "options": [a.strip(), b.strip(), c.strip(), d.strip()],
        "correct_option_id": "ABCD".index(ans.upper())
    } for q, a, b, c, d, ans in questions]

# ========== Bot Logic ==========

async def handle_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc.file_name.endswith(".txt"):
        await update.message.reply_text("Please send a valid .txt file.")
        return

    file = await context.bot.get_file(doc.file_id)
    file_path = await file.download_to_drive()

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    mcqs = parse_mcqs(content)
    if not mcqs:
        await update.message.reply_text("No valid MCQs found.")
        return

    for q in mcqs:
        await update.message.chat.send_poll(
            question=q['question'],
            options=q['options'],
            type=Poll.QUIZ,
            correct_option_id=q['correct_option_id'],
            is_anonymous=False
        )

# ========== Telegram Setup ==========

@app.on_event("startup")
async def startup():
    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .rate_limiter(AIORateLimiter())
        .build()
    )
    application.add_handler(MessageHandler(filters.Document.ALL, handle_doc))

    await bot.set_webhook(f"{WEBHOOK_URL}/webhook")
    app.bot_app = application

@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, bot)
    await app.bot_app.process_update(update)
    return {"ok": True}
    
