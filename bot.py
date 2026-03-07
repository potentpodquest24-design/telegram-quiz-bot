import telebot
import json
import random
import os
from flask import Flask, request

TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

# ---------- JSON LOAD ----------

def load_json(file):
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

quiz_data = load_json("quiz_data.json")
users = load_json("users.json")
leaderboard = load_json("leaderboard.json")
results = load_json("results.json")

user_sessions = {}

# ---------- START ----------

@bot.message_handler(commands=["start"])
def start(message):

    user_id = str(message.from_user.id)

    users[user_id] = {
        "name": message.from_user.first_name
    }

    save_json("users.json", users)

    if message.from_user.id in user_sessions:
        del user_sessions[message.from_user.id]

    markup = telebot.types.InlineKeyboardMarkup()

    for chapter in quiz_data.keys():
        markup.add(
            telebot.types.InlineKeyboardButton(
                chapter,
                callback_data=f"chapter|{chapter}"
            )
        )

    bot.send_message(
        message.chat.id,
        "📚 Chapter પસંદ કરો",
        reply_markup=markup
    )

# ---------- CHAPTER SELECT ----------

@bot.callback_query_handler(func=lambda call: call.data.startswith("chapter"))
def select_chapter(call):

    chapter = call.data.split("|")[1]

    user_sessions[call.from_user.id] = {
        "chapter": chapter
    }

    markup = telebot.types.InlineKeyboardMarkup(row_width=3)

    buttons = [10,20,30,40,50,60]

    btn = []

    for b in buttons:
        btn.append(
            telebot.types.InlineKeyboardButton(
                str(b),
                callback_data=f"quiz|{b}"
            )
        )

    markup.add(*btn)

    bot.send_message(
        call.message.chat.id,
        "❓ કેટલા Question જોઈએ?",
        reply_markup=markup
    )

# ---------- QUIZ START ----------

@bot.callback_query_handler(func=lambda call: call.data.startswith("quiz"))
def start_quiz(call):

    try:

        count = int(call.data.split("|")[1])

        session = user_sessions.get(call.from_user.id)

        if not session:
            bot.send_message(call.message.chat.id,"⚠️ Session expired. ફરી /start કરો.")
            return

        chapter = session["chapter"]

        questions = quiz_data[chapter]

        selected = random.sample(questions, min(count, len(questions)))

        session["questions"] = selected
        session["index"] = 0
        session["score"] = 0
        session["total"] = len(selected)
        session["answered"] = False

        send_question(call.message.chat.id, call.from_user.id)

    except Exception as e:
        print("Quiz start error:", e)

# ---------- SEND QUESTION ----------

def send_question(chat_id, user_id):

    try:

        session = user_sessions.get(user_id)

        if not session:
            bot.send_message(chat_id,"⚠️ Session expired. /start કરો.")
            return

        index = session["index"]

        if index >= session["total"]:

            score = session["score"]
            total = session["total"]

            uid = str(user_id)

            results[uid] = {
                "score": score,
                "total": total
            }

            save_json("results.json", results)

            leaderboard[uid] = score

            save_json("leaderboard.json", leaderboard)

            markup = telebot.types.InlineKeyboardMarkup()

            markup.add(
                telebot.types.InlineKeyboardButton(
                    "🔁 Restart Quiz",
                    callback_data="restart"
                )
            )

            bot.send_message(
                chat_id,
                f"🏁 Quiz Complete\n\n📊 Final Score: {score}/{total}",
                reply_markup=markup
            )

            return

        q = session["questions"][index]

        markup = telebot.types.InlineKeyboardMarkup()

        for option in q["options"]:
            markup.add(
                telebot.types.InlineKeyboardButton(
                    option,
                    callback_data=f"answer|{option}"
                )
            )

        session["answered"] = False

        bot.send_message(
            chat_id,
            f"Q{index+1}. {q['question']}",
            reply_markup=markup
        )

    except Exception as e:
        print("Send question error:", e)

# ---------- ANSWER ----------

@bot.callback_query_handler(func=lambda call: call.data.startswith("answer"))
def answer(call):

    try:

        user_id = call.from_user.id

        session = user_sessions.get(user_id)

        if not session:
            bot.send_message(call.message.chat.id,"⚠️ Session expired. /start કરો.")
            return

        if session["answered"]:
            return

        session["answered"] = True

        index = session["index"]

        q = session["questions"][index]

        selected = call.data.split("|")[1]

        if selected == q["answer"]:
            session["score"] += 1

        session["index"] += 1

        send_question(call.message.chat.id, user_id)

    except Exception as e:
        print("Answer error:", e)

# ---------- RESTART ----------

@bot.callback_query_handler(func=lambda call: call.data == "restart")
def restart(call):

    if call.from_user.id in user_sessions:
        del user_sessions[call.from_user.id]

    start(call.message)

# ---------- WEBHOOK ----------

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():

    json_str = request.get_data().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)

    bot.process_new_updates([update])

    return "OK", 200

@app.route("/")
def home():
    return "Bot Running"

# ---------- RUN ----------

if __name__ == "__main__":

    bot.remove_webhook()

    RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")

    bot.set_webhook(url=f"{RENDER_URL}/{TOKEN}")

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
