import logging
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes
)
from flask import Flask
import threading

# ---------------- CONFIG ----------------

BOT_TOKEN = "8581217078:AAHxvT124vdAT8NHViiQx_GyJzJzc-GxC38"
ADMIN_ID = 5148765826

DATA_FILE = "data.json"

# ----------------------------------------

logging.basicConfig(level=logging.INFO)

# Flask server for Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run_flask).start()

# ----------------------------------------

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

db = load_data()

# ----------------------------------------

def is_admin(user_id):
    return user_id == ADMIN_ID

# ----------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📝 Start Quiz", callback_data="start_quiz")]
    ]
    await update.message.reply_text(
        "👋 Welcome to Quiz Bot\n\nStart Quiz કરવા માટે નીચે બટન દબાવો 👇",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ----------------------------------------

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Access Denied")
        return

    keyboard = [
        [InlineKeyboardButton("➕ Add Subject", callback_data="add_subject")],
        [InlineKeyboardButton("➕ Add Question", callback_data="add_question")],
        [InlineKeyboardButton("📋 View Data", callback_data="view_data")]
    ]

    await update.message.reply_text(
        "⚙ ADMIN PANEL",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ----------------------------------------

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "start_quiz":
        await show_subjects(query, context)

    elif data == "add_subject":
        context.user_data["state"] = "add_subject"
        await query.message.reply_text("✏ Subject નામ લખો:")

    elif data == "add_question":
        if not db:
            await query.message.reply_text("❌ પહેલું Subject add કરો")
            return
        await show_subjects_admin(query, context)

    elif data.startswith("subject_admin_"):
        subject = data.replace("subject_admin_", "")
        context.user_data["add_q_subject"] = subject
        context.user_data["state"] = "add_question"
        await query.message.reply_text(
            "✏ Question format:\n\nQuestion | Option1 | Option2 | Option3 | Option4 | correct(1-4)"
        )

    elif data.startswith("subject_"):
        subject = data.replace("subject_", "")
        context.user_data["quiz_subject"] = subject
        context.user_data["q_index"] = 0
        await send_question(query, context)

    elif data.startswith("ans_"):
        await check_answer(query, context)

# ----------------------------------------

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    state = context.user_data.get("state")

    if state == "add_subject":
        subject = update.message.text.strip()
        db.setdefault(subject, [])
        save_data(db)
        context.user_data.clear()
        await update.message.reply_text(f"✅ Subject added: {subject}")

    elif state == "add_question":
        subject = context.user_data.get("add_q_subject")
        parts = update.message.text.split("|")

        if len(parts) != 6:
            await update.message.reply_text("❌ Format ખોટું છે, ફરી લખો")
            return

        q = {
            "q": parts[0].strip(),
            "options": [p.strip() for p in parts[1:5]],
            "ans": int(parts[5].strip()) - 1
        }

        db.setdefault(subject, []).append(q)
        save_data(db)
        context.user_data.clear()

        await update.message.reply_text("✅ Question Added Successfully")

# ----------------------------------------

async def show_subjects(query, context):
    keyboard = [
        [InlineKeyboardButton(sub, callback_data=f"subject_{sub}")]
        for sub in db.keys()
    ]
    await query.message.reply_text(
        "📚 Subject પસંદ કરો:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_subjects_admin(query, context):
    keyboard = [
        [InlineKeyboardButton(sub, callback_data=f"subject_admin_{sub}")]
        for sub in db.keys()
    ]
    await query.message.reply_text(
        "📚 Subject પસંદ કરો:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ----------------------------------------

async def send_question(query, context):
    subject = context.user_data["quiz_subject"]
    idx = context.user_data["q_index"]

    questions = db.get(subject, [])

    if idx >= len(questions):
        await query.message.reply_text("🎉 Quiz Completed!")
        context.user_data.clear()
        return

    q = questions[idx]

    keyboard = [
        [InlineKeyboardButton(opt, callback_data=f"ans_{i}")]
        for i, opt in enumerate(q["options"])
    ]

    await query.message.reply_text(
        f"Q{idx+1}. {q['q']}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ----------------------------------------

async def check_answer(query, context):
    subject = context.user_data["quiz_subject"]
    idx = context.user_data["q_index"]
    questions = db.get(subject, [])

    user_ans = int(query.data.replace("ans_", ""))
    correct = questions[idx]["ans"]

    if user_ans == correct:
        await query.message.reply_text("✅ Correct!")
    else:
        await query.message.reply_text(
            f"❌ Wrong!\nCorrect Answer: {questions[idx]['options'][correct]}"
        )

    context.user_data["q_index"] += 1
    await send_question(query, context)

# ----------------------------------------

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("help", start))

    app.add_handler(CommandHandler("text", text_handler))

    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
