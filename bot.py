import telebot
import os
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
    bot.send_message(message.chat.id, "Select Subject", reply_markup=keyboard)

# SUBJECT
@bot.callback_query_handler(func=lambda call: call.data.startswith("subject"))
def subject(call):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("Chapter 1", callback_data="chapter_1"),
        InlineKeyboardButton("Chapter 2", callback_data="chapter_2")
    )
    bot.edit_message_text("Select Chapter", call.message.chat.id, call.message.message_id, reply_markup=keyboard)

# CHAPTER
@bot.callback_query_handler(func=lambda call: call.data.startswith("chapter"))
def chapter(call):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("10", callback_data="q_10"),
        InlineKeyboardButton("20", callback_data="q_20"),
        InlineKeyboardButton("30", callback_data="q_30")
    )
    bot.edit_message_text("Select Number of Questions", call.message.chat.id, call.message.message_id, reply_markup=keyboard)

# QUESTION NUMBER
@bot.callback_query_handler(func=lambda call: call.data.startswith("q_"))
def question(call):
    q_no = int(call.data.split("_")[1])
    
    # Session Initialize
    user_data[call.message.chat.id] = {
        "total": q_no,
        "current": 0,
        "score": 0
    }

    # સીધી ક્વિઝ શરૂ કરો (ટાઈમર વગર)
    bot.answer_callback_query(call.id, "Quiz Starting...")
    send_question(call.message.chat.id)

# SEND QUESTION
def send_question(chat_id):
    try:
        data = user_data.get(chat_id)
        if not data: return

        if data["current"] >= data["total"]:
            finish_quiz(chat_id)
            return

        data["current"] += 1
        q_no = data["current"]

        keyboard = InlineKeyboardMarkup()
        # પ્રશ્ન ક્રમાંક સાથે callback_data મોકલો જેથી સાચો જવાબ ટ્રેક થાય
        keyboard.add(
            InlineKeyboardButton("3", callback_data=f"ans_3_{q_no}"),
            InlineKeyboardButton("4", callback_data=f"ans_4_{q_no}")
        )

        bot.send_message(
            chat_id,
            f"Question {q_no}/{data['total']}\n\n2 + 2 = ?",
            reply_markup=keyboard
        )

    except Exception as e:
        print("Error:", e)

# ANSWER
@bot.callback_query_handler(func=lambda call: call.data.startswith("ans_"))
def answer(call):
    chat_id = call.message.chat.id
    data_parts = call.data.split("_")
    ans = data_parts[1]
    q_answered = int(data_parts[2])

    # જો યુઝર ડેટા નથી અથવા જૂના પ્રશ્નનો જવાબ આપે છે તો ઇગ્નોર કરો
    if chat_id not in user_data or user_data[chat_id]["current"] != q_answered:
        bot.answer_callback_query(call.id, "Session expired or already answered.")
        return

    # સાચો જવાબ ચેક કરો
    if ans == "4":
        user_data[chat_id]["score"] += 1
        bot.answer_callback_query(call.id, "Correct! ✅")
    else:
        bot.answer_callback_query(call.id, "Wrong! ❌")

    # બટન દૂર કરો જેથી ફરી ક્લિક ના થાય
    bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
    
    # આગલો પ્રશ્ન મોકલો
    send_question(chat_id)

# FINISH
def finish_quiz(chat_id):
    data = user_data.get(chat_id)
    if data:
        bot.send_message(
            chat_id,
            f"🎊 Quiz Finished!\n\n✅ Final Score: {data['score']}/{data['total']}"
        )
        user_data.pop(chat_id, None)

# RUN
print("Bot Running on Render...")
bot.infinity_polling()
