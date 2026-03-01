from flask import Flask
from threading import Thread
import json, random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
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
USER_FILE = "users.json"

user_sessions = {}
admin_sessions = {}

# ================= DATABASE =================

def load_json(file):
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("▶ Start Quiz", callback_data="user_subject")]]
    await update.message.reply_text("🙏 Welcome to Quiz Bot", reply_markup=InlineKeyboardMarkup(keyboard))

# ================= USER QUIZ =================

async def user_subject(update, context):
    query = update.callback_query
    await query.answer()

    db = load_json(DB_FILE)
    buttons = [[InlineKeyboardButton(s, callback_data=f"sub_{s}")] for s in db]
    await query.edit_message_text("📚 Subject પસંદ કરો", reply_markup=InlineKeyboardMarkup(buttons))

async def user_chapter(update, context):
    query = update.callback_query
    await query.answer()

    context.user_data["subject"] = query.data.split("_")[1]

    db = load_json(DB_FILE)
    buttons = [[InlineKeyboardButton(c, callback_data=f"quiz_{c}")]
               for c in db[context.user_data["subject"]]]
    await query.edit_message_text("📖 Chapter પસંદ કરો", reply_markup=InlineKeyboardMarkup(buttons))

async def start_quiz(update, context):
    query = update.callback_query
    await query.answer()

    context.user_data["chapter"] = query.data.split("_")[1]

    keyboard = [
        [InlineKeyboardButton("🟢 10 પ્રશ્ન", callback_data="count_10")],
        [InlineKeyboardButton("🔵 20 પ્રશ્ન", callback_data="count_20")]
    ]
    await query.edit_message_text("કેટલા પ્રશ્ન આપવા?", reply_markup=InlineKeyboardMarkup(keyboard))

async def select_count(update, context):
    query = update.callback_query
    await query.answer()

    total = int(query.data.split("_")[1])
    sub = context.user_data["subject"]
    chap = context.user_data["chapter"]

    db = load_json(DB_FILE)
    questions = db[sub][chap]
    random.shuffle(questions)

    user_sessions[query.from_user.id] = {
        "questions": questions[:total],
        "qno": 0,
        "score": 0
    }

    await send_question(query, context)

async def send_question(query, context):
    uid = query.from_user.id
    s = user_sessions.get(uid)

    if not s:
        return

    if s["qno"] >= len(s["questions"]):
        keyboard = [[InlineKeyboardButton("🔁 Restart Quiz", callback_data="user_subject")]]
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"🎉 Quiz Finished!\n\nScore: {s['score']}/{len(s['questions'])}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    q = s["questions"][s["qno"]]

    buttons = [
        [InlineKeyboardButton(opt, callback_data=f"ans_{i}")]
        for i, opt in enumerate(q["options"])
    ]

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=f"Q{s['qno']+1}. {q['question']}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def answer_handler(update, context):
    query = update.callback_query
    await query.answer()

    uid = query.from_user.id
    s = user_sessions.get(uid)
    if not s:
        return

    selected = int(query.data.split("_")[1])
    correct = s["questions"][s["qno"]]["answer"]

    if selected == correct:
        s["score"] += 1

    s["qno"] += 1

    await send_question(query, context)

# ================= ADMIN =================

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("➕ Add Subject", callback_data="add_subject")],
        [InlineKeyboardButton("➕ Add Chapter", callback_data="add_chapter")],
        [InlineKeyboardButton("➕ Add Question", callback_data="add_question")],
        [InlineKeyboardButton("👥 Total Users", callback_data="total_users")]
    ]
    await update.message.reply_text("🔐 Admin Panel", reply_markup=InlineKeyboardMarkup(keyboard))

# ================= RUN =================

keep_alive()

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))

app.add_handler(CallbackQueryHandler(user_subject, pattern="user_subject"))
app.add_handler(CallbackQueryHandler(user_chapter, pattern="sub_"))
app.add_handler(CallbackQueryHandler(start_quiz, pattern="quiz_"))
app.add_handler(CallbackQueryHandler(select_count, pattern="count_"))
app.add_handler(CallbackQueryHandler(answer_handler, pattern="ans_"))

if __name__ == "__main__":
    app.run_polling()
