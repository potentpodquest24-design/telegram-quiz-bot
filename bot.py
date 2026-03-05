import os
import json
import random
import asyncio
import time
import aiofiles
from flask import Flask
from threading import Thread
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    CallbackQueryHandler, ContextTypes,
    PollAnswerHandler
)

# ================= LOAD ENV =================
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 5148765826

DB_FILE = "quiz_data.json"
LEADERBOARD_FILE = "leaderboard.json"
USERS_FILE = "users.json"

user_sessions = {}

# ================= KEEP ALIVE =================
app_flask = Flask("")

@app_flask.route("/")
def home():
    return "Bot Running"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)

def keep_alive():
    Thread(target=run_web, daemon=True).start()

# ================= FILE UTILS =================
async def load_json(file):
    try:
        async with aiofiles.open(file, "r", encoding="utf-8") as f:
            return json.loads(await f.read())
    except:
        return {}

async def save_json(file, data):
    async with aiofiles.open(file, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, ensure_ascii=False, indent=2))

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    users = await load_json(USERS_FILE)
    if user_id not in users:
        users[user_id] = {"name": update.effective_user.first_name}
        await save_json(USERS_FILE, users)

    keyboard = [[InlineKeyboardButton("▶ Start Quiz", callback_data="start_quiz")]]

    await update.message.reply_text(
        "🙏 Welcome to Quiz Bot",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= LEADERBOARD =================
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lb = await load_json(LEADERBOARD_FILE)
    users = await load_json(USERS_FILE)

    sorted_lb = sorted(lb.items(), key=lambda x: x[1], reverse=True)[:10]

    text = "🏆 Top 10 Leaderboard\n\n"
    for i, (uid, score) in enumerate(sorted_lb, 1):
        name = users.get(uid, {}).get("name", "User")
        text += f"{i}. {name} - {score}\n"

    await update.message.reply_text(text)

# ================= QUIZ FLOW =================
async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    db = await load_json(DB_FILE)
    subjects = list(db.keys())

    buttons = [[InlineKeyboardButton(s, callback_data=f"sub_{i}")]
               for i, s in enumerate(subjects)]

    await query.edit_message_text("📚 Subject પસંદ કરો",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def select_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    sub_index = int(query.data.split("_")[1])
    db = await load_json(DB_FILE)
    subjects = list(db.keys())
    subject = subjects[sub_index]

    context.user_data["subject"] = subject

    chapters = list(db[subject].keys())

    buttons = [[InlineKeyboardButton(c, callback_data=f"chap_{i}")]
               for i, c in enumerate(chapters)]

    await query.edit_message_text("📖 Chapter પસંદ કરો",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def select_chapter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chap_index = int(query.data.split("_")[1])
    subject = context.user_data["subject"]

    db = await load_json(DB_FILE)
    chapter = list(db[subject].keys())[chap_index]

    context.user_data["chapter"] = chapter

    keyboard = [
        [InlineKeyboardButton("⏱ 60 sec", callback_data="mode_60")],
        [InlineKeyboardButton("⏱ 80 sec", callback_data="mode_80")],
        [InlineKeyboardButton("▶ Without Time", callback_data="mode_notime")]
    ]

    await query.edit_message_text("Mode પસંદ કરો",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def select_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["mode"] = query.data

    await query.edit_message_text("🚀 Quiz Started!")

    await start_quiz_session(query.from_user.id, context)

# ================= QUIZ SESSION =================
async def start_quiz_session(user_id, context):
    db = await load_json(DB_FILE)

    subject = context.user_data["subject"]
    chapter = context.user_data["chapter"]

    questions = db[subject][chapter]
    selected = random.sample(questions, min(10, len(questions)))

    user_sessions[user_id] = {
        "questions": selected,
        "qno": 0,
        "score": 0,
        "chat_id": user_id,
        "mode": context.user_data["mode"],
        "start_time": time.time(),
        "current_poll": None
    }

    await send_question(context, user_id)

# ================= SEND QUESTION =================
async def send_question(context, user_id):
    s = user_sessions.get(user_id)
    if not s:
        return

    if s["qno"] >= len(s["questions"]):
        await finish_quiz(context, user_id)
        return

    q = s["questions"][s["qno"]]

    open_period = None
    if s["mode"] == "mode_60":
        open_period = 60
    elif s["mode"] == "mode_80":
        open_period = 80

    poll = await context.bot.send_poll(
        chat_id=s["chat_id"],
        question=f"Q{s['qno']+1}. {q['question']}",
        options=q["options"],
        type="quiz",
        correct_option_id=q["answer"],
        is_anonymous=False,
        open_period=open_period
    )

    s["current_poll"] = poll.poll.id

    if open_period:
        asyncio.create_task(auto_next(context, user_id, open_period))

# ================= AUTO NEXT =================
async def auto_next(context, user_id, delay):
    await asyncio.sleep(delay + 1)

    s = user_sessions.get(user_id)
    if not s:
        return

    s["qno"] += 1
    await send_question(context, user_id)

# ================= POLL ANSWER =================
async def handle_poll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.poll_answer
    user_id = answer.user.id

    s = user_sessions.get(user_id)
    if not s:
        return

    if answer.option_ids:
        selected = answer.option_ids[0]
        correct = s["questions"][s["qno"]]["answer"]
        if selected == correct:
            s["score"] += 1

    s["qno"] += 1
    await send_question(context, user_id)

# ================= FINISH =================
async def finish_quiz(context, user_id):
    s = user_sessions.get(user_id)
    if not s:
        return

    score = s["score"]

    lb = await load_json(LEADERBOARD_FILE)
    lb[str(user_id)] = lb.get(str(user_id), 0) + score
    await save_json(LEADERBOARD_FILE, lb)

    keyboard = [
        [InlineKeyboardButton("🔁 Retry", callback_data="retry")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="menu")]
    ]

    await context.bot.send_message(
        chat_id=s["chat_id"],
        text=f"🎉 Quiz Finished!\nScore: {score}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    del user_sessions[user_id]

# ================= RUN =================
if __name__ == "__main__":
    keep_alive()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("leaderboard", leaderboard))

    app.add_handler(CallbackQueryHandler(start_quiz, pattern="start_quiz"))
    app.add_handler(CallbackQueryHandler(select_subject, pattern="^sub_"))
    app.add_handler(CallbackQueryHandler(select_chapter, pattern="^chap_"))
    app.add_handler(CallbackQueryHandler(select_mode, pattern="^mode_"))
    app.add_handler(PollAnswerHandler(handle_poll))

    print("Bot Running...")
    app.run_polling(drop_pending_updates=True)
