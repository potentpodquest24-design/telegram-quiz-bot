import telebot
import os
import random
from dotenv import load_dotenv
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
import threading

# ENV LOAD
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = telebot.TeleBot(TOKEN)

users=set()
user_data={}

# SAMPLE QUESTIONS
questions=[
("2 + 2 = ?",["3","4","5"],"4"),
("5 + 3 = ?",["7","8","9"],"8"),
("10 - 4 = ?",["6","5","4"],"6"),
("3 × 3 = ?",["6","9","12"],"9"),
("12 / 3 = ?",["2","4","6"],"4"),
]

# START
@bot.message_handler(commands=['start'])
def start(message):

    users.add(message.chat.id)

    keyboard=InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("🎯 Start Quiz",callback_data="start_quiz")
    )

    keyboard.add(
        InlineKeyboardButton("ℹ️ Help",callback_data="help")
    )

    bot.send_message(
        message.chat.id,
        "👋 Welcome to Quiz Bot\n\nTest your knowledge and improve your skills!",
        reply_markup=keyboard
    )

# HELP
@bot.callback_query_handler(func=lambda call: call.data=="help")
def help_msg(call):

    bot.send_message(
        call.message.chat.id,
        "📚 Quiz Bot Help\n\nSelect quiz and answer questions."
    )

# START QUIZ
@bot.callback_query_handler(func=lambda call: call.data=="start_quiz")
def quiz_menu(call):

    keyboard=InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("10 Questions",callback_data="q10")
    )
    keyboard.add(
        InlineKeyboardButton("20 Questions",callback_data="q20")
    )
    keyboard.add(
        InlineKeyboardButton("30 Questions",callback_data="q30")
    )

    bot.edit_message_text(
        "Select number of questions:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )

# SELECT QUESTION COUNT
@bot.callback_query_handler(func=lambda call: call.data.startswith("q"))
def start_questions(call):

    total=int(call.data.replace("q",""))

    user_data[call.message.chat.id]={
        "score":0,
        "current":0,
        "total":total
    }

    send_question(call.message.chat.id)

# SEND QUESTION
def send_question(chat_id):

    data=user_data[chat_id]

    if data["current"]>=data["total"]:
        finish_quiz(chat_id)
        return

    q=random.choice(questions)

    data["answer"]=q[2]

    keyboard=InlineKeyboardMarkup()

    for opt in q[1]:
        keyboard.add(
            InlineKeyboardButton(opt,callback_data=f"ans_{opt}")
        )

    bot.send_message(
        chat_id,
        f"❓ Question {data['current']+1}\n\n{q[0]}",
        reply_markup=keyboard
    )

    data["current"]+=1

# ANSWER
@bot.callback_query_handler(func=lambda call: call.data.startswith("ans"))
def answer(call):

    ans=call.data.replace("ans_","")

    data=user_data[call.message.chat.id]

    if ans==data["answer"]:
        data["score"]+=1

    send_question(call.message.chat.id)

# FINISH QUIZ
def finish_quiz(chat_id):

    data=user_data[chat_id]

    score=data["score"]
    total=data["total"]

    keyboard=InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("🔁 Restart Quiz",callback_data="start_quiz")
    )

    bot.send_message(
        chat_id,
        f"""
🎉 Quiz Completed!

🏆 Your Score: {score} / {total}

👏 Great job!
Keep learning and try again to improve your score.
""",
        reply_markup=keyboard
    )

# ADMIN PANEL
@bot.message_handler(commands=['admin'])
def admin_panel(message):

    if message.chat.id!=ADMIN_ID:
        return

    keyboard=InlineKeyboardMarkup()

    keyboard.add(
        InlineKeyboardButton("📊 Total Users",callback_data="users")
    )

    bot.send_message(
        message.chat.id,
        "Admin Panel",
        reply_markup=keyboard
    )

# TOTAL USERS
@bot.callback_query_handler(func=lambda call: call.data=="users")
def total_users(call):

    if call.message.chat.id!=ADMIN_ID:
        return

    bot.send_message(
        call.message.chat.id,
        f"👥 Total Users: {len(users)}"
    )

# FLASK KEEP ALIVE (Render)
app=Flask(__name__)

@app.route('/')
def home():
    return "Bot Running"

def run():
    app.run(host='0.0.0.0',port=10000)

def keep_alive():
    t=threading.Thread(target=run)
    t.start()

keep_alive()

print("Bot Running...")

bot.infinity_polling()
