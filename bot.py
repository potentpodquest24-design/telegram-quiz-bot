import os
import json
import asyncio
from flask import Flask
from threading import Thread
from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    PollAnswerHandler
)

# ========= ENV =========
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5148765826"))

# ========= KEEP ALIVE =========
app_flask = Flask("")

@app_flask.route("/")
def home():
    return "Bot Running"

def run_web():
    app_flask.run(host="0.0.0.0", port=10000)

def keep_alive():
    Thread(target=run_web).start()

# ========= FILES =========
DB_FILE = "quiz_data.json"
USERS_FILE = "users.json"

user_sessions = {}

# ========= FILE UTILS =========
def load_json(file, default):
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f)

def register_user(uid):
    users = load_json(USERS_FILE, [])
    if uid not in users:
        users.append(uid)
        save_json(USERS_FILE, users)

# ========= START =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    uid = update.message.chat_id
    register_user(uid)

    keyboard = [[InlineKeyboardButton("▶ Start Quiz", callback_data="subject")]]

    await update.message.reply_text(
        "📚 Quiz Bot માં આપનું સ્વાગત છે",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========= SUBJECT =========
async def subject_menu(update, context):

    query = update.callback_query
    await query.answer()

    db = load_json(DB_FILE, {})

    buttons = [[InlineKeyboardButton(s, callback_data=f"sub_{s}")] for s in db]

    await query.edit_message_text(
        "📘 Subject પસંદ કરો",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ========= CHAPTER =========
async def chapter_menu(update, context):

    query = update.callback_query
    await query.answer()

    subject = query.data.replace("sub_", "")
    context.user_data["subject"] = subject

    db = load_json(DB_FILE, {})

    chapters = db[subject]

    buttons = [[InlineKeyboardButton(c, callback_data=f"chap_{c}")] for c in chapters]

    await query.edit_message_text(
        "📖 Chapter પસંદ કરો",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ========= TIMER =========
async def timer_menu(update, context):

    query = update.callback_query
    await query.answer()

    chapter = query.data.replace("chap_", "")
    context.user_data["chapter"] = chapter

    keyboard = [
        [InlineKeyboardButton("60 sec", callback_data="timer_60")],
        [InlineKeyboardButton("80 sec", callback_data="timer_80")],
        [InlineKeyboardButton("No Timer", callback_data="timer_0")]
    ]

    await query.edit_message_text(
        "⏱ Timer પસંદ કરો",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========= QUESTION COUNT =========
async def count_menu(update, context):

    query = update.callback_query
    await query.answer()

    timer = int(query.data.split("_")[1])
    context.user_data["timer"] = timer

    keyboard = [
        [
            InlineKeyboardButton("10", callback_data="count_10"),
            InlineKeyboardButton("20", callback_data="count_20")
        ],
        [
            InlineKeyboardButton("30", callback_data="count_30"),
            InlineKeyboardButton("40", callback_data="count_40")
        ]
    ]

    await query.edit_message_text(
        "❓ કેટલા પ્રશ્ન?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========= START QUIZ =========
async def start_quiz(update, context):

    query = update.callback_query
    await query.answer()

    count = int(query.data.split("_")[1])

    subject = context.user_data["subject"]
    chapter = context.user_data["chapter"]
    timer = context.user_data["timer"]

    db = load_json(DB_FILE, {})

    questions = db[subject][chapter][:count]

    user_sessions[query.from_user.id] = {
        "questions": questions,
        "index": 0,
        "score": 0,
        "chat_id": query.message.chat_id,
        "timer": timer,
        "poll_id": None
    }

    await query.edit_message_text("🚀 Quiz શરૂ!")

    await send_question(context, query.from_user.id)

# ========= SEND QUESTION =========
async def send_question(context, user_id):

    s = user_sessions[user_id]

    if s["index"] >= len(s["questions"]):

        await context.bot.send_message(
            chat_id=s["chat_id"],
            text=f"🏁 Quiz Finished\nScore: {s['score']}/{len(s['questions'])}"
        )

        del user_sessions[user_id]
        return

    q = s["questions"][s["index"]]

    poll = await context.bot.send_poll(
        chat_id=s["chat_id"],
        question=q["question"],
        options=q["options"],
        type="quiz",
        correct_option_id=q["answer"],
        is_anonymous=False,
        open_period=s["timer"] if s["timer"] else None
    )

    s["poll_id"] = poll.poll.id

# ========= POLL ANSWER =========
async def poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):

    answer = update.poll_answer
    uid = answer.user.id

    s = user_sessions.get(uid)

    if not s:
        return

    if answer.poll_id != s["poll_id"]:
        return

    selected = answer.option_ids[0]

    correct = s["questions"][s["index"]]["answer"]

    if selected == correct:
        s["score"] += 1

    s["index"] += 1

    await asyncio.sleep(1)

    await send_question(context, uid)

# ========= ADMIN =========
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.chat_id != ADMIN_ID:
        return

    users = load_json(USERS_FILE, [])

    await update.message.reply_text(
        f"👨‍💻 ADMIN PANEL\n\n👥 Users: {len(users)}\n\n/broadcast message"
    )

# ========= BROADCAST =========
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.chat_id != ADMIN_ID:
        return

    text = " ".join(context.args)

    users = load_json(USERS_FILE, [])

    for uid in users:
        try:
            await context.bot.send_message(uid, text)
            await asyncio.sleep(0.05)
        except:
            pass

    await update.message.reply_text("Broadcast Sent")

# ========= RUN =========
keep_alive()

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(CommandHandler("broadcast", broadcast))

app.add_handler(CallbackQueryHandler(subject_menu, pattern="subject"))
app.add_handler(CallbackQueryHandler(chapter_menu, pattern="sub_"))
app.add_handler(CallbackQueryHandler(timer_menu, pattern="chap_"))
app.add_handler(CallbackQueryHandler(count_menu, pattern="timer_"))
app.add_handler(CallbackQueryHandler(start_quiz, pattern="count_"))

app.add_handler(PollAnswerHandler(poll_answer))

print("🚀 BOT STARTED")

app.run_polling(drop_pending_updates=True)
