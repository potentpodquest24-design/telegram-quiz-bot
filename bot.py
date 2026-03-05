from flask import Flask
from threading import Thread
import json, random, asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters, PollAnswerHandler
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
    users = load_json(USER_FILE)
    users[str(update.effective_user.id)] = True
    save_json(USER_FILE, users)

    keyboard = [[InlineKeyboardButton("▶ Start Quiz", callback_data="user_subject")]]
    await update.message.reply_text("🙏 Welcome to Quiz Bot", reply_markup=InlineKeyboardMarkup(keyboard))

# ================= SUBJECT =================

async def user_subject(update, context):
    query = update.callback_query
    await query.answer()

    db = load_json(DB_FILE)
    buttons = [[InlineKeyboardButton(s, callback_data=f"sub_{s}")] for s in db]

    await query.edit_message_text("📚 Subject પસંદ કરો", reply_markup=InlineKeyboardMarkup(buttons))

# ================= CHAPTER =================

async def user_chapter(update, context):
    query = update.callback_query
    await query.answer()

    subject = query.data.split("_",1)[1]
    context.user_data["subject"] = subject

    db = load_json(DB_FILE)
    chapters = db[subject].keys()

    buttons = [[InlineKeyboardButton(c, callback_data=f"chap_{c}")] for c in chapters]
    await query.edit_message_text("📖 Chapter પસંદ કરો", reply_markup=InlineKeyboardMarkup(buttons))

# ================= SELECT CHAPTER =================

async def select_chapter(update, context):
    query = update.callback_query
    await query.answer()

    chapter = query.data.split("_",1)[1]
    context.user_data["chapter"] = chapter

    if context.user_data["subject"] == "Maths":
        keyboard = [
            [InlineKeyboardButton("⏱ With Time (50 sec)", callback_data="mode_time")],
            [InlineKeyboardButton("▶ Without Time", callback_data="mode_notime")]
        ]
        await query.edit_message_text("Mode પસંદ કરો", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    await show_count_buttons(query)

# ================= MODE =================

async def select_mode(update, context):
    query = update.callback_query
    await query.answer()

    context.user_data["mode"] = query.data
    await show_count_buttons(query)

# ================= COUNT BUTTONS =================

async def show_count_buttons(query):
    keyboard = [
        [InlineKeyboardButton("10", callback_data="count_10"),
         InlineKeyboardButton("20", callback_data="count_20")],
        [InlineKeyboardButton("30", callback_data="count_30"),
         InlineKeyboardButton("40", callback_data="count_40")],
        [InlineKeyboardButton("50", callback_data="count_50")]
    ]
    await query.edit_message_text("કેટલા પ્રશ્ન આપવા?", reply_markup=InlineKeyboardMarkup(keyboard))

# ================= START QUIZ =================

async def select_count(update, context):
    query = update.callback_query
    await query.answer()

    total = int(query.data.split("_")[1])
    sub = context.user_data["subject"]
    chap = context.user_data["chapter"]

    db = load_json(DB_FILE)
    questions = db[sub][chap]

    if total > len(questions):
        total = len(questions)

    selected_questions = random.sample(questions, total)

    user_sessions[query.from_user.id] = {
        "questions": selected_questions,
        "qno": 0,
        "score": 0,
        "mode": context.user_data.get("mode", "mode_notime")
    }

    await send_poll(query.message.chat_id, query.from_user.id, context)

# ================= SEND POLL =================

async def send_poll(chat_id, uid, context):
    s = user_sessions.get(uid)
    if not s:
        return

    if s["qno"] >= len(s["questions"]):
        keyboard = [[InlineKeyboardButton("🔁 Restart Quiz", callback_data="user_subject")]]
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🎉 Quiz Finished!\n\nScore: {s['score']}/{len(s['questions'])}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    q = s["questions"][s["qno"]]

    await context.bot.send_poll(
        chat_id=chat_id,
        question=f"Q{s['qno']+1}. {q['question']}",
        options=q["options"],
        type="quiz",
        correct_option_id=q["answer"],
        is_anonymous=False,
        open_period=50 if s["mode"] == "mode_time" else None
    )

# ================= POLL ANSWER =================

async def handle_poll_answer(update: Update, context):
    answer = update.poll_answer
    uid = answer.user.id

    s = user_sessions.get(uid)
    if not s:
        return

    selected = answer.option_ids[0]
    correct = s["questions"][s["qno"]]["answer"]

    if selected == correct:
        s["score"] += 1

    s["qno"] += 1

    await asyncio.sleep(1)
    await send_poll(uid, uid, context)

# ================= ADMIN PANEL (UNCHANGED) =================
# >>> તમારો admin system same રાખ્યો છે <<<

# ================= RUN =================

keep_alive()

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))

app.add_handler(CallbackQueryHandler(user_subject, pattern="user_subject"))
app.add_handler(CallbackQueryHandler(user_chapter, pattern="sub_"))
app.add_handler(CallbackQueryHandler(select_chapter, pattern="chap_"))
app.add_handler(CallbackQueryHandler(select_mode, pattern="mode_"))
app.add_handler(CallbackQueryHandler(select_count, pattern="count_"))

app.add_handler(PollAnswerHandler(handle_poll_answer))

app.add_handler(CallbackQueryHandler(admin_buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text))

if __name__ == "__main__":
    app.run_polling(drop_pending_updates=True)
