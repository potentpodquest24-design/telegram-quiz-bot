from flask import Flask
from threading import Thread
import json, random, asyncio
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    CallbackQueryHandler, ContextTypes,
    PollAnswerHandler
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
LEADERBOARD_FILE = "leaderboard.json"
RESULT_FILE = "results.json"

user_sessions = {}

# ================= FILE UTILS =================

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

    subject = query.data.replace("sub_", "")
    context.user_data["subject"] = subject

    if subject == "Maths":
        keyboard = [
            [InlineKeyboardButton("🟢 With Time (1 Min)", callback_data="mode_time")],
            [InlineKeyboardButton("🔵 Without Time", callback_data="mode_notime")]
        ]
        await query.edit_message_text("Mode પસંદ કરો", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    db = load_json(DB_FILE)
    chapter = list(db[subject].keys())[0]
    context.user_data["chapter"] = chapter

    await show_count_buttons(query)

# ================= MODE =================

async def select_mode(update, context):
    query = update.callback_query
    await query.answer()

    context.user_data["mode"] = query.data

    db = load_json(DB_FILE)
    chapter = list(db["Maths"].keys())[0]
    context.user_data["chapter"] = chapter

    await show_count_buttons(query)

# ================= QUESTION COUNT =================

async def show_count_buttons(query):
    keyboard = [
        [InlineKeyboardButton("10", callback_data="count_10"),
         InlineKeyboardButton("20", callback_data="count_20")],
        [InlineKeyboardButton("30", callback_data="count_30"),
         InlineKeyboardButton("40", callback_data="count_40")],
        [InlineKeyboardButton("50", callback_data="count_50")]
    ]

    await query.edit_message_text("કેટલા પ્રશ્ન જોઈએ?", reply_markup=InlineKeyboardMarkup(keyboard))

# ================= START QUIZ =================

async def select_count(update, context):
    query = update.callback_query
    await query.answer()

    total = int(query.data.split("_")[1])
    subject = context.user_data["subject"]
    chapter = context.user_data["chapter"]

    db = load_json(DB_FILE)
    questions = db[subject][chapter]
    random.shuffle(questions)

    user_sessions[query.from_user.id] = {
        "questions": questions[:total],
        "qno": 0,
        "score": 0,
        "subject": subject
    }

    await send_poll_question(context, query.message.chat_id, query.from_user.id)

# ================= POLL QUESTION =================

async def send_poll_question(context, chat_id, user_id):
    s = user_sessions.get(user_id)
    if not s:
        return

    if s["qno"] >= len(s["questions"]):
        await finish_quiz(context, chat_id, user_id)
        return

    q = s["questions"][s["qno"]]

    await context.bot.send_poll(
        chat_id=chat_id,
        question=f"Q{s['qno']+1}. {q['question']}",
        options=q["options"],
        type="quiz",
        correct_option_id=q["answer"],
        is_anonymous=False,
        open_period=60 if context.user_data.get("mode") == "mode_time" else None
    )

# ================= POLL ANSWER =================

async def handle_poll_answer(update: Update, context):
    answer = update.poll_answer
    user_id = answer.user.id

    s = user_sessions.get(user_id)
    if not s:
        return

    selected = answer.option_ids[0]
    correct = s["questions"][s["qno"]]["answer"]

    if selected == correct:
        s["score"] += 1

    s["qno"] += 1

    await asyncio.sleep(1)

    await send_poll_question(context, user_id, user_id)

# ================= FINISH =================

async def finish_quiz(context, chat_id, user_id):
    s = user_sessions[user_id]
    score = s["score"]
    total = len(s["questions"])

    # Save Leaderboard
    leaderboard = load_json(LEADERBOARD_FILE)
    leaderboard[str(user_id)] = leaderboard.get(str(user_id), 0) + score
    save_json(LEADERBOARD_FILE, leaderboard)

    # Save Result History
    results = load_json(RESULT_FILE)
    results.setdefault(str(user_id), []).append({
        "subject": s["subject"],
        "score": score,
        "total": total
    })
    save_json(RESULT_FILE, results)

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🎉 Quiz Finished!\n\nScore: {score}/{total}"
    )

# ================= LEADERBOARD =================

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_json(LEADERBOARD_FILE)
    if not data:
        await update.message.reply_text("No leaderboard data yet.")
        return

    sorted_users = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]

    text = "🏆 Top 10 Leaderboard\n\n"
    for i, (uid, score) in enumerate(sorted_users, 1):
        text += f"{i}. {uid} — {score} points\n"

    await update.message.reply_text(text)

# ================= PERFORMANCE =================

async def performance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    results = load_json(RESULT_FILE)

    if user_id not in results:
        await update.message.reply_text("No performance data.")
        return

    text = "📊 Your Performance:\n\n"
    for r in results[user_id]:
        text += f"{r['subject']} → {r['score']}/{r['total']}\n"

    await update.message.reply_text(text)

# ================= RUN =================

keep_alive()

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("leaderboard", leaderboard))
app.add_handler(CommandHandler("performance", performance))

app.add_handler(CallbackQueryHandler(user_subject, pattern="user_subject"))
app.add_handler(CallbackQueryHandler(user_chapter, pattern="sub_"))
app.add_handler(CallbackQueryHandler(select_mode, pattern="mode_"))
app.add_handler(CallbackQueryHandler(select_count, pattern="count_"))

app.add_handler(PollAnswerHandler(handle_poll_answer))

if __name__ == "__main__":
    app.run_polling()
