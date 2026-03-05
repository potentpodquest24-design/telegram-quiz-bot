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

# ================= KEEP ALIVE =================
app_flask = Flask("")

@app_flask.route("/")
def home():
    return "Bot is running 24/7 with Admin Panel & Timer Fix!"

def run_web():
    app_flask.run(host="0.0.0.0", port=10000)

def keep_alive():
    Thread(target=run_web).start()

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN") 
ADMIN_ID = int(os.getenv("ADMIN_ID", 5148765826))

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

# ================= ADMIN COMMANDS =================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ આ કમાન્ડ માત્ર એડમિન માટે છે.")
        return
        
    users = load_json(USERS_FILE, list)
    msg = (
        "👨‍💻 **એડમિન પેનલ (Admin Panel)**\n\n"
        f"👥 કુલ યુઝર્સ: **{len(users)}**\n\n"
        "📢 **બ્રોડકાસ્ટ કરવા માટેની રીત:**\n"
        "`/broadcast તમારો મેસેજ અહીં લખો`"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    if user_id != ADMIN_ID:
        return
        
    if not context.args:
        await update.message.reply_text("⚠️ ઉદાહરણ: `/broadcast હેલો વિદ્યાર્થીઓ!`", parse_mode="Markdown")
        return
        
    text = " ".join(context.args)
    users = load_json(USERS_FILE, list)
    
    await update.message.reply_text("⏳ બ્રોડકાસ્ટ શરૂ થઈ ગયું છે...")
    success = 0
    for uid in users:
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 **અગત્યની સૂચના**\n\n{text}")
            success += 1
            await asyncio.sleep(0.05) 
        except:
            pass
            
    await update.message.reply_text(f"✅ બ્રોડકાસ્ટ પૂર્ણ! મેસેજ {success}/{len(users)} યુઝર્સને મોકલી દેવાયો છે.")

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    register_user(user_id)

    keyboard = [[InlineKeyboardButton("▶ Start Quiz", callback_data="user_subject")]]
    await update.message.reply_text("🙏 Welcome to Quiz Bot\n\nતમારી મનપસંદ પરીક્ષાની તૈયારી માટે ક્વિઝ શરૂ કરો.", reply_markup=InlineKeyboardMarkup(keyboard))

# ================= SUBJECT =================
async def user_subject(update, context):
    query = update.callback_query
    await query.answer()

    db = load_json(DB_FILE, dict)
    if not db:
        await query.edit_message_text("⚠️ એરર: ડેટાબેઝ ખાલી છે અથવા quiz_data.json માં ભૂલ છે.")
        return

    buttons = [[InlineKeyboardButton(s, callback_data=f"sub_{s}")] for s in db]
    await query.edit_message_text("📚 વિષય (Subject) પસંદ કરો", reply_markup=InlineKeyboardMarkup(buttons))

# ================= CHAPTER =================
async def user_chapter(update, context):
    query = update.callback_query
    await query.answer()

    subject = query.data.replace("sub_", "")
    context.user_data["subject"] = subject

    db = load_json(DB_FILE, dict)
    chapters = db.get(subject, {})

    # 64-byte લિમિટ એરર સોલ્વ કરવા ઇન્ડેક્સનો ઉપયોગ
    buttons = [[InlineKeyboardButton(c, callback_data=f"chap_{i}")] for i, c in enumerate(chapters)]
    buttons.append([InlineKeyboardButton("🔙 પાછા જાઓ", callback_data="user_subject")])
    
    await query.edit_message_text("📖 પ્રકરણ (Chapter) પસંદ કરો", reply_markup=InlineKeyboardMarkup(buttons))

# ================= SELECT CHAPTER =================
async def select_chapter(update, context):
    query = update.callback_query
    await query.answer()

    chapter_index = int(query.data.replace("chap_", ""))
    subject = context.user_data.get("subject")
    
    db = load_json(DB_FILE, dict)
    chapters_list = list(db.get(subject, {}).keys())
    
    if chapter_index < len(chapters_list):
        chapter_name = chapters_list[chapter_index]
        context.user_data["chapter"] = chapter_name
    else:
        await query.edit_message_text("⚠️ કોઈ એરર આવી છે, ફરીથી /start કરો.")
        return

    if subject == "Maths":
        keyboard = [
            [InlineKeyboardButton("⏱ 60 sec", callback_data="mode_60")],
            [InlineKeyboardButton("⏱ 80 sec", callback_data="mode_80")],
            [InlineKeyboardButton("▶ Without Time", callback_data="mode_notime")]
        ]
        await query.edit_message_text("⏳ ટાઈમર મોડ પસંદ કરો", reply_markup=InlineKeyboardMarkup(keyboard))
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
    await query.edit_message_text("🎯 તમારે કેટલા પ્રશ્નો રમવા છે?", reply_markup=InlineKeyboardMarkup(keyboard))

# ================= START QUIZ =================
async def select_count(update, context):
    query = update.callback_query
    await query.answer()

    total = int(query.data.split("_")[1])
    subject = context.user_data.get("subject")
    chapter = context.user_data.get("chapter")

    db = load_json(DB_FILE, dict)
    if subject not in db or chapter not in db[subject]:
        await query.edit_message_text("⚠️ આ ચેપ્ટરમાં કોઈ પ્રશ્નો મળ્યા નથી.")
        return

    questions = db[subject][chapter]

    # પ્રશ્નો લાઈનસર જ આવે તે માટેનો કોડ
    if total >= len(questions):
        selected = questions.copy()
    else:
        selected = questions[:total]

    user_sessions[query.from_user.id] = {
        "quiz_id": time.time(),
        "questions": selected,
        "qno": 0,
        "score": 0,
        "subject": subject,
        "mode": context.user_data.get("mode"),
        "chat_id": query.message.chat_id,
        "current_poll_id": None
    }

    await query.edit_message_text("🚀 તમારી ક્વિઝ શરૂ થઈ રહી છે...\nશુભકામનાઓ!")
    await send_poll_question(context, query.from_user.id)

# ================= SEND POLL =================
async def send_poll_question(context, user_id):
    s = user_sessions.get(user_id)
    if not s: return

    if s["qno"] >= len(s["questions"]):
        await finish_quiz(context, user_id)
        return

    q = s["questions"][s["qno"]]

    if s["mode"] == "mode_60": open_period = 60
    elif s["mode"] == "mode_80": open_period = 80
    else: open_period = None

    try:
        poll_msg = await context.bot.send_poll(
            chat_id=s["chat_id"],
            question=f"પ્રશ્ન {s['qno']+1}. {q['question']}",
            options=q["options"],
            type="quiz",
            correct_option_id=q["answer"],
            is_anonymous=False,
            open_period=open_period
        )

        s["current_poll_id"] = poll_msg.poll.id

        if open_period:
            asyncio.create_task(auto_next(context, user_id, open_period, s["qno"], s["quiz_id"]))
            
    except Exception as e:
        print(f"Error sending poll: {e}")
        await finish_quiz(context, user_id)

async def auto_next(context, user_id, delay, expected_qno, quiz_id):
    await asyncio.sleep(delay + 1)
    s = user_sessions.get(user_id)
    
    if not s or s.get("quiz_id") != quiz_id: 
        return
        
    if s["qno"] == expected_qno:
        s["qno"] += 1
        await send_poll_question(context, user_id)

# ================= POLL ANSWER =================
async def handle_poll_answer(update: Update, context):
    answer = update.poll_answer
    user_id = answer.user.id
    s = user_sessions.get(user_id)
    if not s: return

    if answer.poll_id != s.get("current_poll_id"):
        return

    selected = answer.option_ids[0]
    if s["qno"] < len(s["questions"]):
        correct = s["questions"][s["qno"]]["answer"]
        if selected == correct:
            s["score"] += 1

    s["qno"] += 1
    await asyncio.sleep(1) 
    await send_poll_question(context, user_id)

# ================= FINISH =================
async def finish_quiz(context, user_id):
    s = user_sessions.get(user_id)
    if not s: return
    
    score = s["score"]
    total = len(s["questions"])

    keyboard = [[InlineKeyboardButton("🔁 ફરીથી રમો (Restart)", callback_data="user_subject")]]

    await context.bot.send_message(
        chat_id=s["chat_id"],
        text=f"🎉 **ક્વિઝ પૂર્ણ થઈ ગઈ છે!**\n\n🎯 તમારો સ્કોર: **{score} / {total}**\n\nખૂબ ખૂબ અભિનંદન!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    del user_sessions[user_id]

# ================= RUN =================
keep_alive()

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin_panel))
app.add_handler(CommandHandler("broadcast", broadcast_message))

app.add_handler(CallbackQueryHandler(user_subject, pattern="^user_subject$"))
app.add_handler(CallbackQueryHandler(user_chapter, pattern="^sub_"))
app.add_handler(CallbackQueryHandler(select_chapter, pattern="^chap_"))
app.add_handler(CallbackQueryHandler(select_mode, pattern="^mode_"))
app.add_handler(CallbackQueryHandler(select_count, pattern="^count_"))
app.add_handler(PollAnswerHandler(handle_poll_answer))

if __name__ == "__main__":
    print("Bot is starting securely with all features...")
    app.run_polling(drop_pending_updates=True)
