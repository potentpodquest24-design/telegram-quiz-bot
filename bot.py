import telebot
import json
import os
from dotenv import load_dotenv
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
import threading
import random

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = telebot.TeleBot(TOKEN)

# load questions
with open("quiz_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

user_sessions = {}
users = set()
timers = {}  # ટાઈમર રાખવા માટે નવી ડિક્શનરી

# START
@bot.message_handler(commands=['start'])
def start(message):
    users.add(message.chat.id)
    kb = InlineKeyboardMarkup()
    for subject in data.keys():
        kb.add(InlineKeyboardButton(subject, callback_data=f"sub|{subject}"))
    bot.send_message(message.chat.id, "📚 Select Subject", reply_markup=kb)

# SUBJECT
@bot.callback_query_handler(func=lambda c: c.data.startswith("sub|"))
def subject(call):
    subject = call.data.split("|")[1]
    kb = InlineKeyboardMarkup()
    for chapter in data[subject].keys():
        kb.add(InlineKeyboardButton(chapter, callback_data=f"chap|{subject}|{chapter}"))
    bot.edit_message_text("📖 Select Chapter", call.message.chat.id, call.message.message_id, reply_markup=kb)

# CHAPTER
@bot.callback_query_handler(func=lambda c: c.data.startswith("chap|"))
def chapter(call):
    subject, chapter = call.data.split("|")[1:]
    kb = InlineKeyboardMarkup()
    for n in [10, 20, 30, 40, 50, 60]:
        kb.add(InlineKeyboardButton(str(n), callback_data=f"count|{subject}|{chapter}|{n}"))
    bot.edit_message_text("🔢 કેટલા પ્રશ્ન?", call.message.chat.id, call.message.message_id, reply_markup=kb)

# QUESTION COUNT
@bot.callback_query_handler(func=lambda c: c.data.startswith("count|"))
def count(call):
    subject, chapter, count = call.data.split("|")[1:]
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Without Time", callback_data=f"time|{subject}|{chapter}|{count}|0"))
    kb.add(
        InlineKeyboardButton("60 sec", callback_data=f"time|{subject}|{chapter}|{count}|60"),
        InlineKeyboardButton("80 sec", callback_data=f"time|{subject}|{chapter}|{count}|80")
    )
    bot.edit_message_text("⏱ Select Time", call.message.chat.id, call.message.message_id, reply_markup=kb)

# TIME SELECT
@bot.callback_query_handler(func=lambda c: c.data.startswith("time|"))
def time_select(call):
    subject, chapter, count, time = call.data.split("|")[1:]
    questions = data[subject][chapter]
    random.shuffle(questions)
    selected = questions[:int(count)]
    user_sessions[call.message.chat.id] = {
        "questions": selected,
        "index": 0,
        "score": 0,
        "time": int(time)
    }
    send_question(call.message.chat.id)

# SEND QUESTION
def send_question(chat_id):
    # જો આ યુઝર માટે જૂનું ટાઈમર ચાલુ હોય તો તેને કેન્સલ કરો
    if chat_id in timers:
        timers[chat_id].cancel()

    session = user_sessions.get(chat_id)
    if not session: return

    if session["index"] >= len(session["questions"]):
        finish(chat_id)
        return

    q = session["questions"][session["index"]]

    msg = bot.send_poll(
        chat_id,
        q["question"],
        q["options"],
        type="quiz",
        correct_option_id=q["answer"],
        is_anonymous=False,
        open_period=session["time"] if session["time"] != 0 else None
    )

    session["poll_id"] = msg.poll.id
    session["index"] += 1

    # જો ટાઈમ લિમિટ હોય, તો ઓટોમેટિક નેક્સ્ટ ક્વેશ્ચન માટે ટાઈમર સેટ કરો
    if session["time"] > 0:
        # ટાઈમ પૂરો થયાના 2 સેકન્ડ પછી નેક્સ્ટ ક્વેશ્ચન મોકલશે (બફર ટાઈમ)
        t = threading.Timer(session["time"] + 2, send_question, args=[chat_id])
        timers[chat_id] = t
        t.start()

# ANSWER
@bot.poll_answer_handler()
def answer(poll):
    for chat_id, session in user_sessions.items():
        if session.get("poll_id") == poll.poll_id:
            # યુઝરે જવાબ આપી દીધો, એટલે જૂનું ટાઈમર કેન્સલ કરો
            if chat_id in timers:
                timers[chat_id].cancel()

            q = session["questions"][session["index"] - 1]
            if poll.option_ids[0] == q["answer"]:
                session["score"] += 1

            send_question(chat_id)
            break

# FINISH
def finish(chat_id):
    if chat_id in timers:
        timers[chat_id].cancel()
        
    s = user_sessions[chat_id]
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔁 Restart", callback_data="restart"))
    bot.send_message(
        chat_id,
        f"🎉 Quiz Completed!\n\n🏆 Score : {s['score']} / {len(s['questions'])}\n\n👏 સરસ પ્રયાસ!\nદરરોજ practice કરો અને વધુ શીખો.\n\n👇 ફરીથી શરૂ કરવા માટે button દબાવો",
        reply_markup=kb
    )

# RESTART
@bot.callback_query_handler(func=lambda c: c.data == "restart")
def restart(call):
    start(call.message)

# ADMIN
@bot.message_handler(commands=['admin'])
def admin(message):
    if message.chat.id != ADMIN_ID:
        return
    bot.send_message(message.chat.id, f"👥 Total Users : {len(users)}")

# KEEP ALIVE
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot Running"

def run():
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run).start()
print("Bot started")
bot.infinity_polling()
