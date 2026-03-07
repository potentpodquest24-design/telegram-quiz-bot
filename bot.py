import json
import random
import os
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    PollAnswerHandler,
    ContextTypes
)

TOKEN = os.getenv("BOT_TOKEN")

with open("quiz_data.json") as f:
    quiz_data = json.load(f)

user_state = {}

# ---------------- START ---------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard=[]

    for subject in quiz_data:
        keyboard.append(
            [InlineKeyboardButton(subject,callback_data=f"subject|{subject}")]
        )

    await update.message.reply_text(
        "📚 Subject પસંદ કરો",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ---------------- BUTTONS ---------------- #

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query=update.callback_query
    await query.answer()

    data=query.data.split("|")

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
            "📖 Chapter પસંદ કરો",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# CHAPTER

    elif data[0]=="chapter":

        subject=data[1]
        chapter=data[2]

        keyboard=[
            [InlineKeyboardButton("10",callback_data=f"count|{subject}|{chapter}|10")],
            [InlineKeyboardButton("20",callback_data=f"count|{subject}|{chapter}|20")],
            [InlineKeyboardButton("30",callback_data=f"count|{subject}|{chapter}|30")],
            [InlineKeyboardButton("40",callback_data=f"count|{subject}|{chapter}|40")],
            [InlineKeyboardButton("50",callback_data=f"count|{subject}|{chapter}|50")],
            [InlineKeyboardButton("60",callback_data=f"count|{subject}|{chapter}|60")]
        ]

        await query.edit_message_text(
            "📊 કેટલા Question જોઈએ?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# QUESTION COUNT

    elif data[0]=="count":

        subject=data[1]
        chapter=data[2]
        count=int(data[3])

        keyboard=[
            [InlineKeyboardButton("Without Time",callback_data=f"mode|{subject}|{chapter}|{count}|0")],
            [InlineKeyboardButton("60 Second",callback_data=f"mode|{subject}|{chapter}|{count}|60")],
            [InlineKeyboardButton("80 Second",callback_data=f"mode|{subject}|{chapter}|{count}|80")]
        ]

        await query.edit_message_text(
            "⏱ Quiz Mode પસંદ કરો",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# MODE SELECT

    elif data[0]=="mode":

        subject=data[1]
        chapter=data[2]
        count=int(data[3])
        timer=int(data[4])

        questions=quiz_data[subject][chapter]
        random.shuffle(questions)

        user_state[query.from_user.id]={
            "questions":questions[:count],
            "index":0,
            "timer":timer
        }

        await send_question(query.from_user.id,context)


# ---------------- SEND QUESTION ---------------- #

async def send_question(user_id,context):

    state=user_state[user_id]

    if state["index"]>=len(state["questions"]):

        keyboard=[[InlineKeyboardButton("🔄 Restart",callback_data="restart")]]

        await context.bot.send_message(
            chat_id=user_id,
            text="✅ Quiz Finished",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return

    q=state["questions"][state["index"]]

    timer=state["timer"]

    if timer==0:

        poll=await context.bot.send_poll(
            chat_id=user_id,
            question=q["question"],
            options=q["options"],
            type="quiz",
            correct_option_id=q["answer"],
            is_anonymous=False
        )

    else:

        poll=await context.bot.send_poll(
            chat_id=user_id,
            question=q["question"],
            options=q["options"],
            type="quiz",
            correct_option_id=q["answer"],
            open_period=timer,
            is_anonymous=False
        )

        asyncio.create_task(auto_next(user_id,context,timer))

    state["poll_id"]=poll.poll.id


# -------- AUTO NEXT IF NO ANSWER -------- #

async def auto_next(user_id,context,timer):

    await asyncio.sleep(timer+1)

    if user_id not in user_state:
        return

    user_state[user_id]["index"]+=1

    await send_question(user_id,context)


# -------- POLL ANSWER -------- #

async def poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user=update.poll_answer.user.id

    if user not in user_state:
        return

    user_state[user]["index"]+=1

    await send_question(user,context)


# -------- RESTART -------- #

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query=update.callback_query
    await query.answer()

    await start(update,context)


# ---------------- MAIN ---------------- #

def main():

    app=Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start",start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(CallbackQueryHandler(restart,pattern="restart"))
    app.add_handler(PollAnswerHandler(poll_answer))

    print("Bot Running...")

    app.run_polling()


if __name__=="__main__":
    main()
