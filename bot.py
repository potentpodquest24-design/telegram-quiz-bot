import telebot
import os
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# 1. ENV લોડ કરવા (BOT_TOKEN .env ફાઇલમાં હોવો જોઈએ)
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)
app = Flask('')

# --- 2. FLASK SERVER (Render પર બોટને જીવંત રાખવા માટે) ---
@app.route('/')
def home():
    return "Bot is alive and running!"

def run_flask():
    # Render સામાન્ય રીતે 8080 અથવા 10000 પોર્ટ વાપરે છે
    app.run(host='0.0.0.0', port=8080)

# --- 3. USER DATA STORAGE ---
user_data = {}

# --- 4. START COMMAND ---
@bot.message_handler(commands=['start'])
def start(message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Maths", callback_data="subject_maths"))
    bot.send_message(message.chat.id, "📊 વિષય પસંદ કરો:", reply_markup=keyboard)

# SUBJECT SELECTION
@bot.callback_query_handler(func=lambda call: call.data.startswith("subject"))
def subject(call):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("Chapter 1", callback_data="chapter_1"),
        InlineKeyboardButton("Chapter 2", callback_data="chapter_2")
    )
    bot.edit_message_text("📖 ચેપ્ટર પસંદ કરો:", call.message.chat.id, call.message.message_id, reply_markup=keyboard)

# CHAPTER SELECTION
@bot.callback_query_handler(func=lambda call: call.data.startswith("chapter"))
def chapter(call):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("10", callback_data="q_10"),
        InlineKeyboardButton("20", callback_data="q_20"),
        InlineKeyboardButton("30", callback_data="q_30")
    )
    bot.edit_message_text("📝 કેટલા પ્રશ્નો રાખવા છે?", call.message.chat.id, call.message.message_id, reply_markup=keyboard)

# QUESTION COUNT & SESSION START
@bot.callback_query_handler(func=lambda call: call.data.startswith("q_"))
def set_questions(call):
    q_count = int(call.data.split("_")[1])
    
    # યુઝરનું સેશન શરૂ કરવું
    user_data[call.message.chat.id] = {
        "total": q_count,
        "current": 0,
        "score": 0
    }
    
    bot.answer_callback_query(call.id, "ક્વિઝ શરૂ થઈ રહી છે...")
    send_question(call.message.chat.id)

# --- 5. SEND QUESTION LOGIC ---
def send_question(chat_id):
    try:
        data = user_data.get(chat_id)
        if not data: return

        # જો બધા પ્રશ્નો પૂરા થઈ ગયા હોય
        if data["current"] >= data["total"]:
            finish_quiz(chat_id)
            return

        data["current"] += 1
        q_idx = data["current"]

        keyboard = InlineKeyboardMarkup()
        # પ્રશ્ન નંબર સાથે callback મોકલીએ છીએ જેથી ડુપ્લિકેટ ક્લિક ના થાય
        keyboard.add(
            InlineKeyboardButton("3", callback_data=f"ans_3_{q_idx}"),
            InlineKeyboardButton("4", callback_data=f"ans_4_{q_idx}")
        )

        bot.send_message(
            chat_id,
            f"❓ પ્રશ્ન {q_idx}/{data['total']}\n\n2 + 2 = ?",
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Error in send_question: {e}")

# --- 6. ANSWER HANDLING ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("ans_"))
def handle_answer(call):
    chat_id = call.message.chat.id
    _, selected_ans, q_idx = call.data.split("_")

    # સુરક્ષા માટે: ચેક કરો કે યુઝર અત્યારે આ જ પ્રશ્ન પર છે ને?
    if chat_id not in user_data or user_data[chat_id]["current"] != int(q_idx):
        bot.answer_callback_query(call.id, "આ પ્રશ્ન જૂનો થઈ ગયો છે.")
        return

    # જવાબ ચેક કરવો
    if selected_ans == "4":
        user_data[chat_id]["score"] += 1
        bot.answer_callback_query(call.id, "સાચું! ✅")
    else:
        bot.answer_callback_query(call.id, "ખોટું! ❌")

    # મેસેજમાંથી બટન હટાવી દેવા
    bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
    
    # આગલો પ્રશ્ન મોકલવો
    send_question(chat_id)

# --- 7. FINISH QUIZ ---
def finish_quiz(chat_id):
    data = user_data.get(chat_id)
    if data:
        score = data['score']
        total = data['total']
        bot.send_message(
            chat_id,
            f"🎉 ક્વિઝ પૂરી થઈ!\n\n✅ તમારો સ્કોર: {score}/{total}"
        )
        # સેશન ડિલીટ કરવું
        user_data.pop(chat_id, None)

# --- 8. RUN BOT ---
if __name__ == "__main__":
    # Flask સર્વરને અલગ Thread માં ચલાવવું
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    
    # Conflict 409 દૂર કરવા માટે Webhook ડિલીટ કરવું
    print("Removing Webhook...")
    bot.remove_webhook()
    
    print("Bot is starting polling...")
    bot.infinity_polling()
