import os
import re
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from telegram.ext.webhookhandler import WebhookHandler

# Environment variables (set these in Render dashboard or .env if testing locally)
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # e.g., https://your-render-url.onrender.com

# Initialize Flask and Telegram Application
app = Flask(__name__)
application = Application.builder().token(BOT_TOKEN).build()
webhook_handler = WebhookHandler(application)

def parse_mcqs(text):
    pattern = re.compile(r"Q\d*[:：]\s*(.*?)\s*A\)\s*(.*?)\s*B\)\s*(.*?)\s*C\)\s*(.*?)\s*D\)\s*(.*?)\s*Answer[:：]\s*([A-D])", re.DOTALL)
    return pattern.findall(text)

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc.file_name.endswith(".txt"):
        await update.message.reply_text("Send a .txt file only.")
        return

    file = await doc.get_file()
    text = await file.download_as_bytearray()
    mcqs = parse_mcqs(text.decode())

    if not mcqs:
        await update.message.reply_text("Couldn't parse any MCQs.")
        return

    for i, (question, a, b, c, d, answer) in enumerate(mcqs, start=1):
        options = [a.strip(), b.strip(), c.strip(), d.strip()]
        correct_option = ord(answer.upper()) - ord("A")
        await context.bot.send_poll(
            chat_id=update.effective_chat.id,
            question=f"Q{i}: {question.strip()}",
            options=options,
            type='quiz',
            correct_option_id=correct_option,
            is_anonymous=False,
        )

# Telegram handler for document uploads
application.add_handler(MessageHandler(filters.Document.ALL, handle_file))

# Webhook endpoint
@app.post("/hook")
async def webhook():
    await webhook_handler.handle_update(request)
    return "ok"

if __name__ == "__main__":
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        webhook_url=WEBHOOK_URL + "/hook"
    )
    
