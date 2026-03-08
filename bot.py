import telebot
import os
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ENV લોડ કરવા
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)
app = Flask('')

# --- FLASK SERVER FOR RENDER ---
@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# --- BOT LOGIC ---
user_data = {}

@bot.message_handler(commands=['start'])
def start(message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Maths", callback_data="subject_maths"))
    bot.send_message(message.chat.id, "Select Subject", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("subject"))
def subject(call):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("Chapter 1", callback_data="chapter_1"),
        InlineKeyboardButton("Chapter 2", callback_data="chapter_2")
    )
    bot.edit_message_text("Select Chapter", call.message.chat.id, call.message.message_id, reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("chapter"))
def chapter(call):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("10", callback_data="q_10"),
        InlineKeyboardButton("20", callback_data="q_20")
    )
    bot.edit_message_text("Select Number of Questions", call.message.chat.id, call.message.message_id, reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("q_"))
def question(call):
    q_no = int(call.data.split("_")[1])
    user_data[call.message.chat.id] = {"total": q_no, "current": 0, "score": 0}
    bot.answer_callback_query(call.id, "Quiz Starting...")
    send_question(call.message.chat.id)

def send_question(chat_id):
    data = user_data.get(chat_id)
    if not data or data["current"] >= data["total"]:
        finish_quiz(chat_id)
        return

    data["current"] += 1
    q_idx = data["current"]
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("3", callback_data=f"ans_3_{q_idx}"),
        InlineKeyboardButton("4", callback_data=f"ans_4_{q_idx}")
    )
    bot.send_message(chat_id, f"Question {q_idx}/{data['total']}\n\n2 + 2 = ?", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("ans_"))
def answer(call):
    chat_id = call.message.chat.id
    _, ans, q_idx = call.data.split("_")

    if chat_id not in user_data or user_data[chat_id]["current"] != int(q_idx):
        return

    if ans == "4":
        user_data[chat_id]["score"] += 1
        bot.answer_callback_query(call.id, "Correct! ✅")
    else:
        bot.answer_callback_query(call.id, "Wrong! ❌")

    bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
    send_question(chat_id)

def finish_quiz(chat_id):
    data = user_data.get(chat_id)
    if data:
        bot.send_message(chat_id, f"🏁 Quiz Finished!\nScore: {data['score']}/{data['total']}")
        user_data.pop(chat_id, None)

# --- RUN BOT ---
if __name__ == "__main__":
    # Flask ને અલગ થ્રેડમાં ચલાવો જેથી બોટ બ્લોક ના થાય
    t = Thread(target=run_flask)
    t.start()
    
    print("Bot is running...")
    bot.infinity_polling()
