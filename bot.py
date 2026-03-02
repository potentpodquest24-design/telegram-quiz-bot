from flask import Flask
from threading import Thread
import json, random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, filters
)

# ================= KEEP ALIVE =================

app_flask = Flask("")

@app_flask.route("/")
def home():
    return "Bot is running!"

def run_web():
    app_flask.run(host="0.0.0.0", port=10000)

def keep_alive():
    Thread(target=run_web).start()

# ================= CONFIG =================

BOT_TOKEN = "8581217078:AAHxvT124vdAT8NHViiQx_GyJzJzc-GxC38"
ADMIN_ID = 5148765826

DB_FILE = "quiz_data.json"

user_sessions = {}

# ================= DATABASE =================

def load_json(file):
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("▶ Start Quiz", callback_data="user_subject")]]
    await update.message.reply_text("🙏 Welcome to Quiz Bot", reply_markup=InlineKeyboardMarkup(keyboard))

# ================= USER QUIZ =================

async def user_subject(update, context):
    query = update.callback_query
    await query.answer()

    db = load_json(DB_FILE)
    if not db:
        await query.edit_message_text("❌ No subjects available")
        return

    buttons = [[InlineKeyboardButton(s, callback_data=f"sub_{s}")] for s in db]
    await query.edit_message_text("📚 Subject પસંદ કરો", reply_markup=InlineKeyboardMarkup(buttons))

async def user_chapter(update, context):
    query = update.callback_query
    await query.answer()

    subject = query.data.split("_",1)[1]
    context.user_data["subject"] = subject

    db = load_json(DB_FILE)
    buttons = [[InlineKeyboardButton(c, callback_data=f"quiz_{c}")] for c in db[subject]]
    await query.edit_message_text("📖 Chapter પસંદ કરો", reply_markup=InlineKeyboardMarkup(buttons))

async def start_quiz(update, context):
    query = update.callback_query
    await query.answer()

    chapter = query.data.split("_",1)[1]
    context.user_data["chapter"] = chapter

    keyboard = [
        [InlineKeyboardButton("🟢 10 પ્રશ્ન", callback_data="count_10")],
        [InlineKeyboardButton("🔵 20 પ્રશ્ન", callback_data="count_20")]
    ]
    await query.edit_message_text("કેટલા પ્રશ્ન આપવા?", reply_markup=InlineKeyboardMarkup(keyboard))

async def select_count(update, context):
    query = update.callback_query
    await query.answer()

    total = int(query.data.split("_")[1])
    subject = context.user_data["subject"]
    chapter = context.user_data["chapter"]

    db = load_json(DB_FILE)
    questions = db[subject][chapter].copy()
    random.shuffle(questions)

    user_sessions[query.from_user.id] = {
        "questions": questions[:total],
        "qno": 0,
        "score": 0
    }

    await send_question(query.message.chat_id, context, query.from_user.id)

async def send_question(chat_id, context, uid):
    session = user_sessions.get(uid)

    if not session:
        return

    if session["qno"] >= len(session["questions"]):
        keyboard = [[InlineKeyboardButton("🔁 Restart Quiz", callback_data="user_subject")]]
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🎉 Quiz Finished!\n\nScore: {session['score']}/{len(session['questions'])}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    q = session["questions"][session["qno"]]

    buttons = [
        [InlineKeyboardButton(opt, callback_data=f"ans_{i}")]
        for i, opt in enumerate(q["options"])
    ]

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"Q{session['qno']+1}. {q['question']}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def answer_handler(update, context):
    query = update.callback_query
    await query.answer()

    uid = query.from_user.id
    session = user_sessions.get(uid)

    if not session:
        return

    selected = int(query.data.split("_")[1])
    correct = session["questions"][session["qno"]]["answer"]

    if selected == correct:
        session["score"] += 1

    session["qno"] += 1

    await send_question(query.message.chat_id, context, uid)

# ================= RUN =================

keep_alive()

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(user_subject, pattern="user_subject"))
app.add_handler(CallbackQueryHandler(user_chapter, pattern="sub_"))
app.add_handler(CallbackQueryHandler(start_quiz, pattern="quiz_"))
app.add_handler(CallbackQueryHandler(select_count, pattern="count_"))
app.add_handler(CallbackQueryHandler(answer_handler, pattern="ans_"))

if __name__ == "__main__":
    app.run_polling()
