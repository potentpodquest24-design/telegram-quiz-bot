import os
import logging
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Flask app for Render
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

# Quiz Data
quiz_data = {
    "Math": {
        "Chapter 1": {
            "q": "2 + 2 = ?",
            "options": ["3", "4", "5"],
            "answer": "4",
        }
    },
    "Science": {
        "Chapter 1": {
            "q": "Water formula?",
            "options": ["H2O", "CO2", "O2"],
            "answer": "H2O",
        }
    },
}


# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []

    for subject in quiz_data:
        keyboard.append([InlineKeyboardButton(subject, callback_data=f"subject_{subject}")])

    if update.effective_user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("📚 Select Subject", reply_markup=reply_markup)


# Button handler
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    # Subject click
    if data.startswith("subject_"):
        subject = data.split("_")[1]

        keyboard = []

        for chapter in quiz_data[subject]:
            keyboard.append([
                InlineKeyboardButton(
                    chapter, callback_data=f"chapter_{subject}_{chapter}"
                )
            ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"📖 {subject} - Select Chapter", reply_markup=reply_markup
        )

    # Chapter click
    elif data.startswith("chapter_"):
        _, subject, chapter = data.split("_")

        question = quiz_data[subject][chapter]["q"]
        options = quiz_data[subject][chapter]["options"]

        keyboard = []

        for opt in options:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        opt, callback_data=f"answer_{subject}_{chapter}_{opt}"
                    )
                ]
            )

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(question, reply_markup=reply_markup)

    # Answer click
    elif data.startswith("answer_"):
        _, subject, chapter, user_answer = data.split("_")

        correct = quiz_data[subject][chapter]["answer"]

        if user_answer == correct:
            text = "✅ Correct!"
        else:
            text = f"❌ Wrong! Correct answer: {correct}"

        await query.edit_message_text(text)

    # Admin Panel
    elif data == "admin":
        if query.from_user.id != ADMIN_ID:
            return

        keyboard = [
            [InlineKeyboardButton("➕ Add Quiz (Coming Soon)", callback_data="none")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text("⚙️ Admin Panel", reply_markup=reply_markup)


# Run telegram bot
def run_bot():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))

    application.run_polling()


if __name__ == "__main__":
    t = Thread(target=run_bot)
    t.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
