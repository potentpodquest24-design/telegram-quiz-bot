import os
import json
import random
import asyncio
import time
from datetime import datetime
from flask import Flask
from threading import Thread
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    CallbackQueryHandler, ContextTypes,
    PollAnswerHandler, MessageHandler, filters
)

# ================= LOAD ENV =================
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 5148765826  # તમારો એડમિન આઈડી

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in .env file")

DB_FILE = "quiz_data.json"
LEADERBOARD_FILE = "leaderboard.json"
DAILY_FILE = "daily.json"
USERS_FILE = "users.json"

user_sessions = {}

# ================= KEEP ALIVE =================
app_flask = Flask("")

@app_flask.route("/")
def home():
    return "Bot Running 24/7"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)

def keep_alive():
    Thread(target=run_web, daemon=True).start()

# ================= FILE UTILS =================
def load_json(file):
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_json(file, data):
    temp_file = file + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(temp_file, file)

# ================= CLEANUP TASK =================
async def cleanup_old_sessions(context: ContextTypes.DEFAULT_TYPE):
    current_time = time.time()
    expired_users = []
    
    for user_id, session in user_sessions.items():
        if current_time - session.get("quiz_id", 0) > 3600:
            expired_users.append(user_id)
            
    for user_id in expired_users:
        del user_sessions[user_id]
        
    if expired_users:
        print(f"🗑️ Cleaned up {len(expired_users)} expired sessions.")

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if update.effective_user.id in user_sessions:
        del user_sessions[update.effective_user.id]

    users = load_json(USERS_FILE)
    if user_id not in users:
        users[user_id] = {"name": update.effective_user.first_name}
        save_json(USERS_FILE, users)

    keyboard = [[InlineKeyboardButton("▶ Start Quiz", callback_data="user_subject")]]

    await update.message.reply_text(
        f"🙏 Welcome {update.effective_user.first_name} to Quiz Bot",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= ADMIN PANEL =================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ આ કમાન્ડ ફક્ત Admin માટે છે.")
        return

    keyboard = [
        [InlineKeyboardButton("📊 Bot Stats", callback_data="admin_stats")],
        [InlineKeyboardButton("📣 Broadcast", callback_data="admin_broadcast")]
    ]
    await update.message.reply_text("👑 *Admin Panel*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ Access Denied!", show_alert=True)
        return

    await query.answer()
    data = query.data

    if data == "admin_stats":
        users = load_json(USERS_FILE)
        total_users = len(users)
        active_sessions = len(user_sessions)
        
        text = f"📊 *Bot Statistics*\n\n👥 Total Users: {total_users}\n🔥 Active Quizzes: {active_sessions}"
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin_broadcast":
        context.user_data["broadcasting"] = True
        keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="admin_cancel_broadcast")]]
        await query.edit_message_text("📣 જે મેસેજ બધા યુઝર્સને મોકલવો હોય તે નીચે ટાઈપ કરીને મોકલો:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "admin_back" or data == "admin_cancel_broadcast":
        context.user_data["broadcasting"] = False
        keyboard = [
            [InlineKeyboardButton("📊 Bot Stats", callback_data="admin_stats")],
            [InlineKeyboardButton("📣 Broadcast", callback_data="admin_broadcast")]
        ]
        await query.edit_message_text("👑 *Admin Panel*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

# એડમિન બ્રોડકાસ્ટ માટે મેસેજ હેન્ડલર
async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID and context.user_data.get("broadcasting"):
        context.user_data["broadcasting"] = False
        message_to_send = update.message.text
        users = load_json(USERS_FILE)
        
        success = 0
        failed = 0
        
        msg = await update.message.reply_text("⏳ Broadcast શરુ થઈ ગયું છે. કૃપા કરીને રાહ જુઓ...")
        
        for user_id in users.keys():
            try:
                await context.bot.send_message(chat_id=user_id, text=message_to_send)
                success += 1
                await asyncio.sleep(0.05) # Telegram ની લિમિટમાં રહેવા માટે
            except Exception:
                failed += 1
                
        await msg.edit_text(f"✅ Broadcast પૂરું થયું!\n\n✔️ મોકલેલા મેસેજ: {success}\n❌ નિષ્ફળ: {failed}")

# ================= SUBJECT =================
async def user_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    db = load_json(DB_FILE)
    subjects = list(db.keys())

    buttons = [[InlineKeyboardButton(s, callback_data=f"sub_{i}")] for i, s in enumerate(subjects)]
    await query.edit_message_text("📚 Subject પસંદ કરો", reply_markup=InlineKeyboardMarkup(buttons))

# ================= CHAPTER =================
async def user_chapter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    sub_index = int(query.data.replace("sub_", ""))
    db = load_json(DB_FILE)
    subjects = list(db.keys())

    if sub_index >= len(subjects): return

    subject = subjects[sub_index]
    context.user_data["subject"] = subject
    chapters = list(db.get(subject, {}).keys())

    buttons = [[InlineKeyboardButton(c, callback_data=f"chap_{i}")] for i, c in enumerate(chapters)]
    await query.edit_message_text("📖 Chapter પસંદ કરો", reply_markup=InlineKeyboardMarkup(buttons))

# ================= SELECT CHAPTER =================
async def select_chapter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chap_index = int(query.data.replace("chap_", ""))
    subject = context.user_data.get("subject")

    db = load_json(DB_FILE)
    chapters = list(db.get(subject, {}).keys())

    if chap_index >= len(chapters): return

    context.user_data["chapter"] = chapters[chap_index]

    keyboard = [
        [InlineKeyboardButton("⏱ 60 sec", callback_data="mode_60")],
        [InlineKeyboardButton("⏱ 80 sec", callback_data="mode_80")],
        [InlineKeyboardButton("▶ Without Time", callback_data="mode_notime")]
    ]
    await query.edit_message_text("Mode પસંદ કરો", reply_markup=InlineKeyboardMarkup(keyboard))

# ================= MODE =================
async def select_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["mode"] = query.data

    keyboard = [
        [InlineKeyboardButton("10", callback_data="count_10"), InlineKeyboardButton("20", callback_data="count_20")],
        [InlineKeyboardButton("30", callback_data="count_30")]
    ]
    await query.edit_message_text("કેટલા પ્રશ્ન જોઈએ?", reply_markup=InlineKeyboardMarkup(keyboard))

# ================= START QUIZ =================
async def select_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    total = int(query.data.split("_")[1])
    subject = context.user_data.get("subject")
    chapter = context.user_data.get("chapter")

    db = load_json(DB_FILE)
    questions = db.get(subject, {}).get(chapter, [])

    if not questions:
        await query.edit_message_text("⚠️ પ્રશ્નો મળ્યા નથી.")
        return

    selected = random.sample(questions, min(total, len(questions)))

    user_sessions[query.from_user.id] = {
        "quiz_id": time.time(),
        "questions": selected,
        "qno": 0,
        "score": 0,
        "chat_id": query.message.chat_id,
        "mode": context.user_data.get("mode"),
        "timer_task": None,
        "current_poll_id": None,
        "last_poll_message_id": None
    }

    await query.edit_message_text("🚀 Quiz Started!")
    await send_poll_question(context, query.from_user.id)

# ================= SEND POLL =================
async def send_poll_question(context: ContextTypes.DEFAULT_TYPE, user_id):
    s = user_sessions.get(user_id)
    if not s: return

    if s["qno"] >= len(s["questions"]):
        await finish_quiz(context, user_id)
        return

    q = s["questions"][s["qno"]]

    open_period = None
    if s["mode"] == "mode_60": open_period = 60
    elif s["mode"] == "mode_80": open_period = 80

    poll_msg = await context.bot.send_poll(
        chat_id=s["chat_id"],
        question=f"Q{s['qno']+1}. {q['question']}",
        options=q["options"],
        type="quiz",
        correct_option_id=q["answer"],
        is_anonymous=False,
        open_period=open_period
    )

    s["current_poll_id"] = poll_msg.poll.id
    s["last_poll_message_id"] = poll_msg.message_id

    if open_period:
        s["timer_task"] = asyncio.create_task(
            auto_next(context, user_id, open_period, s["qno"], s["quiz_id"])
        )

# ================= AUTO NEXT =================
async def auto_next(context: ContextTypes.DEFAULT_TYPE, user_id, delay, expected_qno, quiz_id):
    try:
        await asyncio.sleep(delay + 1)
    except asyncio.CancelledError:
        return

    s = user_sessions.get(user_id)
    if not s or s["quiz_id"] != quiz_id: return
    if s["qno"] != expected_qno: return

    try:
        await context.bot.stop_poll(chat_id=s["chat_id"], message_id=s["last_poll_message_id"])
    except Exception: pass

    s["qno"] += 1
    s["timer_task"] = None
    await send_poll_question(context, user_id)

# ================= POLL ANSWER =================
async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.poll_answer
    user_id = answer.user.id
    s = user_sessions.get(user_id)

    if not s: return
    if answer.poll_id != s["current_poll_id"]: return
    if s["qno"] >= len(s["questions"]): return

    if s["timer_task"]:
        s["timer_task"].cancel()
        s["timer_task"] = None

    try:
        await context.bot.stop_poll(chat_id=s["chat_id"], message_id=s["last_poll_message_id"])
    except Exception: pass

    if not answer.option_ids:
        s["qno"] += 1
        await send_poll_question(context, user_id)
        return

    selected = answer.option_ids[0]
    correct = s["questions"][s["qno"]]["answer"]

    if selected == correct:
        s["score"] += 1

    s["qno"] += 1
    await send_poll_question(context, user_id)

# ================= FINISH QUIZ =================
async def finish_quiz(context: ContextTypes.DEFAULT_TYPE, user_id):
    s = user_sessions.get(user_id)
    if not s: return

    score = s["score"]
    total = len(s["questions"])

    await context.bot.send_message(
        chat_id=s["chat_id"],
        text=f"🎉 Quiz Finished!\n\nScore: {score}/{total}"
    )
    del user_sessions[user_id]

# ================= RUN =================
if __name__ == "__main__":
    keep_alive()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.job_queue.run_repeating(cleanup_old_sessions, interval=3600, first=60)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))  # નવો એડમિન કમાન્ડ
    
    app.add_handler(CallbackQueryHandler(admin_actions, pattern="^admin_")) # એડમિન બટન્સ
    app.add_handler(CallbackQueryHandler(user_subject, pattern="^user_subject$"))
    app.add_handler(CallbackQueryHandler(user_chapter, pattern="^sub_"))
    app.add_handler(CallbackQueryHandler(select_chapter, pattern="^chap_"))
    app.add_handler(CallbackQueryHandler(select_mode, pattern="^mode_"))
    app.add_handler(CallbackQueryHandler(select_count, pattern="^count_"))
    
    app.add_handler(PollAnswerHandler(handle_poll_answer))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_text)) # બ્રોડકાસ્ટ ટેક્સ્ટ માટે

    print("Bot Running...")
    app.run_polling(drop_pending_updates=True)
