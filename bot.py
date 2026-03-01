import json
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters, PollAnswerHandler
)

# ================== CONFIG ==================

BOT_TOKEN = "8581217078:AAHxvT124vdAT8NHViiQx_GyJzJzc-GxC38"
ADMIN_ID = 5148765826   

DB_FILE = "quiz_data.json"
USER_FILE = "users.json"

user_sessions = {}
admin_sessions = {}

# ================== DATABASE ==================

def load_json(file):
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ================== START ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_json(USER_FILE)
    users[str(update.effective_user.id)] = True
    save_json(USER_FILE, users)

    keyboard = [[InlineKeyboardButton("▶ Start Quiz", callback_data="user_subject")]]
    await update.message.reply_text("🙏 Welcome to Quiz Bot", reply_markup=InlineKeyboardMarkup(keyboard))

# ================== USER QUIZ ==================

async def user_subject(update: Update, context):
    query = update.callback_query
    await query.answer()

    db = load_json(DB_FILE)
    if not db:
        await query.edit_message_text("❌ No subject available")
        return

    buttons = [[InlineKeyboardButton(s, callback_data=f"sub_{s}")] for s in db]
    await query.edit_message_text("📚 Subject પસંદ કરો", reply_markup=InlineKeyboardMarkup(buttons))

async def user_chapter(update: Update, context):
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
    subject = context.user_data["subject"]

    db = load_json(DB_FILE)
    questions = db[subject][chapter]
    random.shuffle(questions)

    user_sessions[query.from_user.id] = {
        "questions": questions[:10],
        "score": 0,
        "qno": 0
    }

    await send_poll(query, context)

async def send_poll(query, context):
    uid = query.from_user.id
    session = user_sessions.get(uid)

    if not session:
        return

    if session["qno"] >= len(session["questions"]):
        score = session["score"]
        keyboard = [[InlineKeyboardButton("🔁 Restart", callback_data="user_subject")]]
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"🎉 Quiz Finished\n\nScore: {score}/{len(session['questions'])}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    q = session["questions"][session["qno"]]

    await context.bot.send_poll(
        chat_id=query.message.chat_id,
        question=f"Q{session['qno']+1}. {q['question']}",
        options=q["options"],
        type="quiz",
        correct_option_id=q["answer"],
        is_anonymous=False
    )

async def poll_handler(update: Update, context):
    ans = update.poll_answer
    uid = ans.user.id

    if uid not in user_sessions:
        return

    session = user_sessions[uid]
    correct = session["questions"][session["qno"]]["answer"]

    if ans.option_ids[0] == correct:
        session["score"] += 1

    session["qno"] += 1

    fake_query = type("obj", (), {"from_user": ans.user, "message": update.effective_chat})
    await send_poll(fake_query, context)

# ================== ADMIN PANEL ==================

async def admin(update: Update, context):
    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("➕ Add Subject", callback_data="add_subject")],
        [InlineKeyboardButton("➕ Add Chapter", callback_data="add_chapter")],
        [InlineKeyboardButton("➕ Add Question", callback_data="add_question")],
        [InlineKeyboardButton("👥 Total Users", callback_data="total_users")]
    ]

    await update.message.reply_text("🔐 Admin Panel", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_buttons(update, context):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    admin_sessions[query.from_user.id] = query.data

    if query.data == "add_subject":
        await query.edit_message_text("✍ Subject નામ લખો")

    elif query.data == "add_chapter":
        await query.edit_message_text("✍ Format: Subject Chapter\nExample: Maths Algebra")

    elif query.data == "add_question":
        await query.edit_message_text("✍ Format:\nSubject Chapter Question | A | B | C | D | 0-3")

    elif query.data == "total_users":
        users = load_json(USER_FILE)
        await query.edit_message_text(f"👥 Total Users: {len(users)}")

async def admin_text(update: Update, context):
    if update.effective_user.id != ADMIN_ID:
        return

    if update.effective_user.id not in admin_sessions:
        return

    mode = admin_sessions[update.effective_user.id]
    text = update.message.text.strip()
    db = load_json(DB_FILE)

    try:
        if mode == "add_subject":
            db[text] = {}
            save_json(DB_FILE, db)
            await update.message.reply_text("✅ Subject Added")

        elif mode == "add_chapter":
            sub, chap = text.split()
            db.setdefault(sub, {})[chap] = []
            save_json(DB_FILE, db)
            await update.message.reply_text("✅ Chapter Added")

        elif mode == "add_question":
            sub, chap, rest = text.split(" ", 2)
            parts = rest.split("|")

            q = parts[0].strip()
            opts = [p.strip() for p in parts[1:5]]
            ans = int(parts[5])

            db.setdefault(sub, {}).setdefault(chap, []).append({
                "question": q,
                "options": opts,
                "answer": ans
            })

            save_json(DB_FILE, db)
            await update.message.reply_text("✅ Question Added")

    except:
        await update.message.reply_text("❌ Wrong Format! Please try again")

# ================== RUN ==================

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))

app.add_handler(CallbackQueryHandler(user_subject, pattern="user_subject"))
app.add_handler(CallbackQueryHandler(user_chapter, pattern="sub_"))
app.add_handler(CallbackQueryHandler(start_quiz, pattern="quiz_"))

app.add_handler(CallbackQueryHandler(admin_buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text))

app.add_handler(PollAnswerHandler(poll_handler))

if __name__ == "__main__":
    app.run_polling()
