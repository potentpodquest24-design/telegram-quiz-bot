import json
import random
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

# -------- JSON LOAD -------- #

def load_json(file):
    try:
        with open(file) as f:
            return json.load(f)
    except:
        return {}

def save_json(file,data):
    with open(file,"w") as f:
        json.dump(data,f,indent=4)

quiz_data = load_json("quiz_data.json")
users = load_json("users.json")
results = load_json("results.json")
leaderboard = load_json("leaderboard.json")

user_state = {}


# -------- START -------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = str(update.effective_user.id)

    users[user] = update.effective_user.first_name
    save_json("users.json",users)

    keyboard=[]

    for subject in quiz_data:
        keyboard.append([InlineKeyboardButton(subject,callback_data=f"subject|{subject}")])

    await update.message.reply_text(
        "📚 Subject પસંદ કરો",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# -------- BUTTONS -------- #

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    data = query.data.split("|")

# SUBJECT

    if data[0]=="subject":

        subject=data[1]

        keyboard=[]

        for chapter in quiz_data[subject]:
            keyboard.append([
                InlineKeyboardButton(
                    chapter,
                    callback_data=f"chapter|{subject}|{chapter}"
                )
            ])

        await query.edit_message_text(
            f"📖 {subject} Chapter પસંદ કરો",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# CHAPTER

    elif data[0]=="chapter":

        subject=data[1]
        chapter=data[2]

        questions=quiz_data[subject][chapter]

        q=random.choice(questions)

        user_state[query.from_user.id]={
            "subject":subject,
            "chapter":chapter,
            "question":q
        }

        keyboard=[]

        for i,opt in enumerate(q["options"]):

            keyboard.append([
                InlineKeyboardButton(
                    opt,
                    callback_data=f"answer|{i}"
                )
            ])

        await query.edit_message_text(
            q["question"],
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ANSWER

    elif data[0]=="answer":

        user=query.from_user.id
        ans=int(data[1])

        q=user_state[user]["question"]

        correct=q["answer"]

        if ans==correct:

            text="✅ Correct"

            results[str(user)]=results.get(str(user),0)+1

        else:

            text=f"❌ Wrong\nCorrect answer: {q['options'][correct]}"

        save_json("results.json",results)

# leaderboard update

        leaderboard[str(user)]=results[str(user)]
        save_json("leaderboard.json",leaderboard)

        keyboard=[[InlineKeyboardButton("➡️ Next Question",callback_data="next")]]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# NEXT QUESTION

    elif data[0]=="next":

        user=query.from_user.id

        subject=user_state[user]["subject"]
        chapter=user_state[user]["chapter"]

        questions=quiz_data[subject][chapter]

        q=random.choice(questions)

        user_state[user]["question"]=q

        keyboard=[]

        for i,opt in enumerate(q["options"]):

            keyboard.append([
                InlineKeyboardButton(
                    opt,
                    callback_data=f"answer|{i}"
                )
            ])

        await query.edit_message_text(
            q["question"],
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# -------- LEADERBOARD -------- #

async def leaderboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text="🏆 Leaderboard\n\n"

    sorted_lb=sorted(leaderboard.items(),key=lambda x:x[1],reverse=True)

    for i,(uid,score) in enumerate(sorted_lb[:10]):

        name=users.get(uid,"User")

        text+=f"{i+1}. {name} - {score}\n"

    await update.message.reply_text(text)


# -------- MAIN -------- #

def main():

    app=Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("leaderboard",leaderboard_cmd))
    app.add_handler(CallbackQueryHandler(buttons))

    print("Bot Running...")
    app.run_polling()


if __name__=="__main__":
    main()
