import json
import os
from flask import Flask
from threading import Thread
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv("my.env")

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

app = Flask(__name__)

@app.route("/")
def home():
    return "Quiz Bot Running"


# ---------------- JSON LOAD ---------------- #

def load_quiz():
    with open("quiz_data.json") as f:
        return json.load(f)

quiz_data = load_quiz()


# ---------------- START ---------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = []

    for subject in quiz_data:
        keyboard.append([
            InlineKeyboardButton(subject, callback_data=f"subject|{subject}")
        ])

    if update.effective_user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin")])

    await update.message.reply_text(
        "📚 Select Subject",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ---------------- BUTTON ---------------- #

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    data = query.data.split("|")

    # SUBJECT
    if data[0] == "subject":

        subject = data[1]

        keyboard = []

        for chapter in quiz_data[subject]:
            keyboard.append([
                InlineKeyboardButton(
                    chapter,
                    callback_data=f"chapter|{subject}|{chapter}"
                )
            ])

        await query.edit_message_text(
            f"📖 {subject} Chapters",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # CHAPTER
    elif data[0] == "chapter":

        subject = data[1]
        chapter = data[2]

        q = quiz_data[subject][chapter]["question"]
        options = quiz_data[subject][chapter]["options"]

        keyboard = []

        for opt in options:
            keyboard.append([
                InlineKeyboardButton(
                    opt,
                    callback_data=f"answer|{subject}|{chapter}|{opt}"
                )
            ])

        await query.edit_message_text(
            q,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ANSWER
    elif data[0] == "answer":

        subject = data[1]
        chapter = data[2]
        user_ans = data[3]

        correct = quiz_data[subject][chapter]["answer"]

        if user_ans == correct:
            text = "✅ Correct Answer"
        else:
            text = f"❌ Wrong\nCorrect: {correct}"

        await query.edit_message_text(text)

    # ADMIN
    elif data[0] == "admin":

        if query.from_user.id != ADMIN_ID:
            return

        keyboard = [
            [InlineKeyboardButton("➕ Add Quiz (Soon)", callback_data="none")]
        ]

        await query.edit_message_text(
            "⚙️ Admin Panel",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# ---------------- BOT START ---------------- #

def run_bot():

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(buttons))

    application.run_polling()


# ---------------- MAIN ---------------- #

if __name__ == "__main__":

    bot_thread = Thread(target=run_bot)
    bot_thread.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
