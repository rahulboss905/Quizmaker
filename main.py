import os
import logging
import re
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from telegram import Update, Bot, Poll
from telegram.ext import Application, ApplicationBuilder, ContextTypes, MessageHandler, filters, AIORateLimiter
from dotenv import load_dotenv
from telegram.constants import ParseMode

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # e.g., https://your-app.onrender.com

bot = Bot(token=BOT_TOKEN)

# Initialize FastAPI
app = FastAPI()

# ========== MCQ PARSER ==========
def parse_mcqs(text):
    pattern = re.compile(
        r"Q\d*[:\-\.]?\s*(.*?)\s*(?:\n|\r\n)"
        r"A\)\s*(.*?)\s*(?:\n|\r\n)"
        r"B\)\s*(.*?)\s*(?:\n|\r\n)"
        r"C\)\s*(.*?)\s*(?:\n|\r\n)"
        r"D\)\s*(.*?)\s*(?:\n|\r\n)"
        r"Answer[:\-\.]?\s*([ABCD])",
        re.IGNORECASE
    )
    questions = pattern.findall(text)
    return [{
        "question": q.strip(),
        "options": [a.strip(), b.strip(), c.strip(), d.strip()],
        "correct_option_id": "ABCD".index(ans.upper())
    } for q, a, b, c, d, ans in questions]

# ========== TELEGRAM HANDLER ==========
async def handle_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc.file_name.endswith(".txt"):
        await update.message.reply_text("❌ Please upload a `.txt` file.")
        return

    file = await context.bot.get_file(doc.file_id)
    file_path = await file.download_to_drive()

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    mcqs = parse_mcqs(content)
    if not mcqs:
        await update.message.reply_text("⚠️ Couldn't parse any MCQs.")
        return

    for q in mcqs:
        await update.message.chat.send_poll(
            question=q['question'],
            options=q['options'],
            type=Poll.QUIZ,
            correct_option_id=q['correct_option_id'],
            is_anonymous=False
        )

# ========== SETUP TELEGRAM APP ==========
@app.on_event("startup")
async def start_bot():
    app.bot_app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .rate_limiter(AIORateLimiter())
        .build()
    )

    app.bot_app.add_handler(MessageHandler(filters.Document.ALL, handle_doc))
    await bot.set_webhook(f"{WEBHOOK_URL}/webhook")
    await app.bot_app.initialize()
    await app.bot_app.start()
    print("✅ Bot started and webhook set.")

@app.on_event("shutdown")
async def shutdown_bot():
    await app.bot_app.stop()
    await app.bot_app.shutdown()
    print("🛑 Bot stopped.")

# ========== WEBHOOK ENDPOINT ==========
@app.post("/webhook")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = Update.de_json(data, bot)
    await app.bot_app.process_update(update)
    return JSONResponse(content={"ok": True})

# ========== BASIC HEALTH CHECK ==========
@app.get("/")
def root():
    return {"status": "Bot is running"}
    
