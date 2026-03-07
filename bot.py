import os
import json
import asyncio
from flask import Flask
from threading import Thread
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    PollAnswerHandler
)

# ================= ENV =================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing!")

# ================= KEEP ALIVE =================
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "Bot Running"

def run_web():
    app_flask.run(host="0.0.0.0", port=10000)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# ================= DATABASE =================
DB_FILE = "quiz_data.json"

user_sessions = {}

def load_db():
    try:
        with open(DB_FILE, "r", encoding="utf8") as f:
            return json.load(f)
    except:
        return {}

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        [InlineKeyboardButton("Start Quiz", callback_data="start_quiz")]
    ]

    await update.message.reply_text(
        "📚 Quiz Bot Ready",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= START QUIZ =================
async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    db = load_db()

    if not db:
        await query.edit_message_text("No questions found")
        return

    questions = list(db.values())

    user_sessions[query.from_user.id] = {
        "questions": questions,
        "index": 0,
        "score": 0,
        "chat_id": query.message.chat_id,
        "poll_id": None
    }

    await query.edit_message_text("Quiz Started 🚀")

    await send_question(context, query.from_user.id)

# ================= SEND QUESTION =================
async def send_question(context, user_id):

    session = user_sessions.get(user_id)

    if not session:
        return

    if session["index"] >= len(session["questions"]):

        await context.bot.send_message(
            chat_id=session["chat_id"],
            text=f"🏁 Quiz Finished\nScore: {session['score']}"
        )

        del user_sessions[user_id]
        return

    q = session["questions"][session["index"]]

    poll = await context.bot.send_poll(
        chat_id=session["chat_id"],
        question=q["question"],
        options=q["options"],
        type="quiz",
        correct_option_id=q["answer"],
        is_anonymous=False,
        open_period=60
    )

    session["poll_id"] = poll.poll.id

# ================= POLL ANSWER =================
async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):

    answer = update.poll_answer
    user_id = answer.user.id

    session = user_sessions.get(user_id)

    if not session:
        return

    if answer.poll_id != session["poll_id"]:
        return

    if not answer.option_ids:
        return

    selected = answer.option_ids[0]

    q = session["questions"][session["index"]]

    if selected == q["answer"]:
        session["score"] += 1

    session["index"] += 1

    await asyncio.sleep(1)

    await send_question(context, user_id)

# ================= ERROR HANDLER =================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):

    print(f"Error: {context.error}")

# ================= RUN =================
keep_alive()

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(start_quiz, pattern="start_quiz"))
app.add_handler(PollAnswerHandler(handle_poll_answer))

app.add_error_handler(error_handler)

print("🚀 BOT STARTED")

app.run_polling(
    drop_pending_updates=True,
    allowed_updates=Update.ALL_TYPES
)
