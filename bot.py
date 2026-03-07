from flask import Flask
from threading import Thread
import json, asyncio, os, time
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
ADMIN_ID = int(os.getenv("ADMIN_ID", "5148765826"))

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN not found! Render Environment Variable માં add કરો.")

# ================= KEEP ALIVE =================
app_flask = Flask("")

@app_flask.route("/")
def home():
    return "Quiz Bot Running 24/7"

def run_web():
    app_flask.run(host="0.0.0.0", port=10000)

def keep_alive():
    Thread(target=run_web).start()

# ================= FILES =================
DB_FILE = "quiz_data.json"
USERS_FILE = "users.json"

user_sessions = {}

# ================= FILE UTILS =================
def load_json(file, default_type=dict):
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default_type()

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def register_user(user_id):
    users = load_json(USERS_FILE, list)
    if user_id not in users:
        users.append(user_id)
        save_json(USERS_FILE, users)

# ================= ADMIN PANEL =================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.chat_id

    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ Only Admin")
        return

    users = load_json(USERS_FILE, list)

    msg = f"""
👨‍💻 ADMIN PANEL

👥 Total Users: {len(users)}

Broadcast:
 /broadcast your_message
"""

    await update.message.reply_text(msg)

# ================= BROADCAST =================
async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message.chat_id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("Example:\n/broadcast Hello Students")
        return

    text = " ".join(context.args)

    users = load_json(USERS_FILE, list)

    success = 0

    for uid in users:
        try:
            await context.bot.send_message(uid, f"📢 {text}")
            success += 1
            await asyncio.sleep(0.05)
        except:
            pass

    await update.message.reply_text(f"Broadcast Sent {success}/{len(users)}")

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.message.chat_id
    register_user(user_id)

    keyboard = [[InlineKeyboardButton("▶ Start Quiz", callback_data="user_subject")]]

    await update.message.reply_text(
        "📚 Quiz Bot માં આપનું સ્વાગત છે",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= SUBJECT =================
async def user_subject(update, context):

    query = update.callback_query
    await query.answer()

    db = load_json(DB_FILE, dict)

    if not db:
        await query.edit_message_text("Database empty")
        return

    buttons = [[InlineKeyboardButton(s, callback_data=f"sub_{s}")] for s in db]

    await query.edit_message_text(
        "Subject Select કરો",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ================= CHAPTER =================
async def user_chapter(update, context):

    query = update.callback_query
    await query.answer()

    subject = query.data.replace("sub_", "")
    context.user_data["subject"] = subject

    db = load_json(DB_FILE, dict)

    chapters = db.get(subject, {})

    buttons = [[InlineKeyboardButton(c, callback_data=f"chap_{i}")] for i, c in enumerate(chapters)]

    await query.edit_message_text(
        "Chapter Select કરો",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ================= SELECT CHAPTER =================
async def select_chapter(update, context):

    query = update.callback_query
    await query.answer()

    index = int(query.data.replace("chap_", ""))

    subject = context.user_data["subject"]

    db = load_json(DB_FILE, dict)

    chapters = list(db[subject].keys())

    chapter = chapters[index]

    context.user_data["chapter"] = chapter

    keyboard = [
        [InlineKeyboardButton("60 sec", callback_data="mode_60")],
        [InlineKeyboardButton("80 sec", callback_data="mode_80")],
        [InlineKeyboardButton("No Timer", callback_data="mode_notime")]
    ]

    await query.edit_message_text(
        "Timer Mode Select કરો",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= MODE =================
async def select_mode(update, context):

    query = update.callback_query
    await query.answer()

    context.user_data["mode"] = query.data

    keyboard = [
        [InlineKeyboardButton("10", callback_data="count_10"),
         InlineKeyboardButton("20", callback_data="count_20")],

        [InlineKeyboardButton("30", callback_data="count_30"),
         InlineKeyboardButton("40", callback_data="count_40")]
    ]

    await query.edit_message_text(
        "Questions Select કરો",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= START QUIZ =================
async def select_count(update, context):

    query = update.callback_query
    await query.answer()

    total = int(query.data.split("_")[1])

    subject = context.user_data["subject"]
    chapter = context.user_data["chapter"]

    db = load_json(DB_FILE, dict)

    questions = db[subject][chapter][:total]

    user_sessions[query.from_user.id] = {
        "questions": questions,
        "qno": 0,
        "score": 0,
        "mode": context.user_data["mode"],
        "chat_id": query.message.chat_id,
        "poll_id": None
    }

    await query.edit_message_text("Quiz Start 🚀")

    await send_question(context, query.from_user.id)

# ================= SEND QUESTION =================
async def send_question(context, user_id):

    s = user_sessions.get(user_id)

    if not s:
        return

    if s["qno"] >= len(s["questions"]):
        await finish_quiz(context, user_id)
        return

    q = s["questions"][s["qno"]]

    if s["mode"] == "mode_60":
        open_period = 60
    elif s["mode"] == "mode_80":
        open_period = 80
    else:
        open_period = None

    poll = await context.bot.send_poll(
        chat_id=s["chat_id"],
        question=q["question"],
        options=q["options"],
        type="quiz",
        correct_option_id=q["answer"],
        is_anonymous=False,
        open_period=open_period
    )

    s["poll_id"] = poll.poll.id

# ================= POLL ANSWER =================
async def handle_poll_answer(update: Update, context):

    answer = update.poll_answer

    user_id = answer.user.id

    s = user_sessions.get(user_id)

    if not s:
        return

    if answer.poll_id != s["poll_id"]:
        return

    selected = answer.option_ids[0]

    correct = s["questions"][s["qno"]]["answer"]

    if selected == correct:
        s["score"] += 1

    s["qno"] += 1

    await asyncio.sleep(1)

    await send_question(context, user_id)

# ================= FINISH =================
async def finish_quiz(context, user_id):

    s = user_sessions[user_id]

    score = s["score"]
    total = len(s["questions"])

    await context.bot.send_message(
        chat_id=s["chat_id"],
        text=f"Quiz Finished 🎉\nScore: {score}/{total}"
    )

    del user_sessions[user_id]

# ================= RUN =================
keep_alive()

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin_panel))
app.add_handler(CommandHandler("broadcast", broadcast_message))

app.add_handler(CallbackQueryHandler(user_subject, pattern="user_subject"))
app.add_handler(CallbackQueryHandler(user_chapter, pattern="sub_"))
app.add_handler(CallbackQueryHandler(select_chapter, pattern="chap_"))
app.add_handler(CallbackQueryHandler(select_mode, pattern="mode_"))
app.add_handler(CallbackQueryHandler(select_count, pattern="count_"))

app.add_handler(PollAnswerHandler(handle_poll_answer))

if __name__ == "__main__":
    print("🚀 BOT STARTED")
    app.run_polling(drop_pending_updates=True)
