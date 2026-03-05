from flask import Flask
from threading import Thread
import json, random, asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    CallbackQueryHandler, ContextTypes,
    PollAnswerHandler
)

# ================= KEEP ALIVE =================

app_flask = Flask("")

@app_flask.route("/")
def home():
    return "Bot is running 24/7!"

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

    # જો નવો મેસેજ હોય અથવા જૂનો એડિટ કરવાનો હોય
    if query.message:
        await query.edit_message_text("📚 Subject પસંદ કરો", reply_markup=InlineKeyboardMarkup(buttons))

# ================= CHAPTER =================

async def user_chapter(update, context):
    query = update.callback_query
    await query.answer()

    subject = query.data.replace("sub_", "")
    context.user_data["subject"] = subject

    db = load_json(DB_FILE)
    chapters = db.get(subject, {})

    buttons = [[InlineKeyboardButton(c, callback_data=f"chap_{c}")] for c in chapters]

    await query.edit_message_text("📖 Chapter પસંદ કરો", reply_markup=InlineKeyboardMarkup(buttons))

# ================= SELECT CHAPTER =================

async def select_chapter(update, context):
    query = update.callback_query
    await query.answer()

    chapter = query.data.replace("chap_", "")
    context.user_data["chapter"] = chapter

    # .get() નો ઉપયોગ જેથી બોટ રિસ્ટાર્ટ વખતે એરર ન આવે
    if context.user_data.get("subject") == "Maths":
        keyboard = [
            [InlineKeyboardButton("⏱ 60 sec", callback_data="mode_60")],
            [InlineKeyboardButton("⏱ 80 sec", callback_data="mode_80")],
            [InlineKeyboardButton("▶ Without Time", callback_data="mode_notime")]
        ]
        await query.edit_message_text("Mode પસંદ કરો", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    context.user_data["mode"] = "mode_notime"
    await show_count_buttons(query)

# ================= MODE =================

async def select_mode(update, context):
    query = update.callback_query
    await query.answer()

    context.user_data["mode"] = query.data
    await show_count_buttons(query)

# ================= COUNT =================

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
    subject = context.user_data.get("subject")
    chapter = context.user_data.get("chapter")

    db = load_json(DB_FILE)
    
    # સુરક્ષા માટે ચેક કરો કે ડેટા છે કે નહીં
    if subject not in db or chapter not in db[subject]:
        await query.edit_message_text("⚠️ આ ચેપ્ટરમાં કોઈ પ્રશ્નો મળ્યા નથી.")
        return

    questions = db[subject][chapter]

    if total >= len(questions):
        selected = questions.copy()
        random.shuffle(selected)
    else:
        selected = random.sample(questions, total)

    user_sessions[query.from_user.id] = {
        "questions": selected,
        "qno": 0,
        "score": 0,
        "subject": subject,
        "mode": context.user_data.get("mode"),
        "chat_id": query.message.chat_id
    }

    await query.edit_message_text("🚀 ક્વિઝ શરૂ થઈ રહી છે...")
    await send_poll_question(context, query.from_user.id)

# ================= SEND POLL =================

async def send_poll_question(context, user_id):
    s = user_sessions.get(user_id)
    if not s:
        return

    # જો બધા પ્રશ્નો પૂરા થઈ ગયા હોય
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

    try:
        poll = await context.bot.send_poll(
            chat_id=s["chat_id"],
            question=f"Q{s['qno']+1}. {q['question']}",
            options=q["options"],
            type="quiz",
            correct_option_id=q["answer"],
            is_anonymous=False,
            open_period=open_period
        )

        # AUTO NEXT IF NO ANSWER (Race Condition ફિક્સ કરેલ છે)
        if open_period:
            asyncio.create_task(auto_next(context, user_id, open_period, s["qno"]))
            
    except Exception as e:
        print(f"Error sending poll: {e}")
        await finish_quiz(context, user_id)

async def auto_next(context, user_id, delay, expected_qno):
    await asyncio.sleep(delay + 1)

    s = user_sessions.get(user_id)
    if not s:
        return

    # જો યુઝર હજુ એ જ પ્રશ્ન પર હોય (એટલે કે જવાબ નથી આપ્યો), તો જ આગળ વધો
    if s["qno"] == expected_qno:
        s["qno"] += 1
        await send_poll_question(context, user_id)

# ================= POLL ANSWER =================

async def handle_poll_answer(update: Update, context):
    answer = update.poll_answer
    user_id = answer.user.id

    s = user_sessions.get(user_id)
    if not s:
        return

    selected = answer.option_ids[0]
    
    # સુરક્ષા માટે ચેક કરો
    if s["qno"] < len(s["questions"]):
        correct = s["questions"][s["qno"]]["answer"]

        if selected == correct:
            s["score"] += 1

    # જવાબ આપ્યા પછી તરત જ પ્રશ્ન નંબર વધારી દો
    s["qno"] += 1

    await asyncio.sleep(1) # થોડું ડીલે જેથી યુઝર સાચો જવાબ જોઈ શકે
    await send_poll_question(context, user_id)

# ================= FINISH =================

async def finish_quiz(context, user_id):
    s = user_sessions.get(user_id)
    if not s: return
    
    score = s["score"]
    total = len(s["questions"])

    keyboard = [[InlineKeyboardButton("🔁 Restart Quiz", callback_data="user_subject")]]

    await context.bot.send_message(
        chat_id=s["chat_id"],
        text=f"🎉 Quiz Finished!\n\nતમારો સ્કોર: {score}/{total}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    # સેશન પૂરો થાય એટલે ડેટા ક્લિયર કરો
    del user_sessions[user_id]

# ================= RUN =================

keep_alive()

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(user_subject, pattern="^user_subject$"))
app.add_handler(CallbackQueryHandler(user_chapter, pattern="^sub_"))
app.add_handler(CallbackQueryHandler(select_chapter, pattern="^chap_"))
app.add_handler(CallbackQueryHandler(select_mode, pattern="^mode_"))
app.add_handler(CallbackQueryHandler(select_count, pattern="^count_"))
app.add_handler(PollAnswerHandler(handle_poll_answer))

if __name__ == "__main__":
    print("Bot is starting...")
    app.run_polling(drop_pending_updates=True)
