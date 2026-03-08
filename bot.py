import telebot
import os
import time
from dotenv import load_dotenv
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ENV
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

# USER SESSION
user_data = {}

# START
@bot.message_handler(commands=['start'])
def start(message):

    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Maths", callback_data="subject_maths"))

    bot.send_message(message.chat.id,"Select Subject",reply_markup=keyboard)


# SUBJECT
@bot.callback_query_handler(func=lambda call: call.data.startswith("subject"))
def subject(call):

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("Chapter 1", callback_data="chapter_1"),
        InlineKeyboardButton("Chapter 2", callback_data="chapter_2")
    )

    bot.edit_message_text(
        "Select Chapter",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )


# CHAPTER
@bot.callback_query_handler(func=lambda call: call.data.startswith("chapter"))
def chapter(call):

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("10", callback_data="q_10"),
        InlineKeyboardButton("20", callback_data="q_20"),
        InlineKeyboardButton("30", callback_data="q_30")
    )

    bot.edit_message_text(
        "Select Number of Questions",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )


# QUESTION NUMBER
@bot.callback_query_handler(func=lambda call: call.data.startswith("q_"))
def question(call):

    q_no = int(call.data.split("_")[1])

    user_data[call.message.chat.id] = {
        "total": q_no,
        "current": 0,
        "score": 0
    }

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("Without Time", callback_data="time_0")
    )
    keyboard.add(
        InlineKeyboardButton("60 Second", callback_data="time_60"),
        InlineKeyboardButton("80 Second", callback_data="time_80")
    )

    bot.edit_message_text(
        "Select Time Mode",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )


# TIME SELECT
@bot.callback_query_handler(func=lambda call: call.data.startswith("time_"))
def time_mode(call):

    time_limit = int(call.data.split("_")[1])

    user_data[call.message.chat.id]["time"] = time_limit

    bot.send_message(call.message.chat.id,"Quiz Starting...")

    send_question(call.message.chat.id)


# SEND QUESTION
def send_question(chat_id):

    try:

        data = user_data[chat_id]

        if data["current"] >= data["total"]:
            finish_quiz(chat_id)
            return

        q_no = data["current"] + 1

        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton("3", callback_data="ans_3"),
            InlineKeyboardButton("4", callback_data="ans_4")
        )

        bot.send_message(
            chat_id,
            f"Question {q_no}\n\n2 + 2 = ?",
            reply_markup=keyboard
        )

        data["current"] += 1

        time_limit = data["time"]

        if time_limit != 0:
            time.sleep(time_limit)
            send_question(chat_id)

    except Exception as e:
        print("Error:", e)


# ANSWER
@bot.callback_query_handler(func=lambda call: call.data.startswith("ans_"))
def answer(call):

    ans = call.data.split("_")[1]

    if ans == "4":
        user_data[call.message.chat.id]["score"] += 1

    send_question(call.message.chat.id)


# FINISH
def finish_quiz(chat_id):

    data = user_data[chat_id]

    bot.send_message(
        chat_id,
        f"Quiz Finished\n\nScore: {data['score']}/{data['total']}"
    )

    user_data.pop(chat_id)


# RUN
print("Bot Running...")
bot.infinity_polling()
