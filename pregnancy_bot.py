
import json
import os
import uuid
import requests
import openai
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters, ConversationHandler
)
from dotenv import load_dotenv
import os

load_dotenv()  # Loads from .env by default

OPENAI_API_KEY = os.getenv("API_KEY")

TELEGRAM_BOT_TOKEN = "7599193424:AAGUtgkx7QnYxd_hzneuOcsVJL_0QYlQE0I"
openai.api_key = OPENAI_API_KEY

TOKEN, NAME, AGE, SYMPTOMS = range(4)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome! Do you have a token from last visit? If yes, please type it. If not, type 'new'")
    return TOKEN

async def handle_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = update.message.text.strip()
    context.user_data["token"] = token

    if token.lower() == "new":
        new_token = str(uuid.uuid4())
        context.user_data["token"] = new_token
        await update.message.reply_text(
            f"🆕 New token generated: `{new_token}`\n\nSave this safely for future visits.\n\nWhat is your name?",
            parse_mode='Markdown'
        )
        return NAME

    try:
        response = requests.get(f"http://localhost:5000/get_patient/{token}")
        if response.status_code == 200:
            data = response.json()
            name = data["name"]
            age = data["age"]
            symptoms = data["symptoms"]

            context.user_data["name"] = name
            context.user_data["age"] = str(age)
            context.user_data["symptoms"] = symptoms

            await update.message.reply_text(
                f"👋 Welcome back, *{name}*!\n\n📅 Age: {age}\n💬 Last symptoms: {symptoms}",
                parse_mode='Markdown'
            )
            await update.message.reply_text("Please describe any new or continuing symptoms.")
            return SYMPTOMS
        else:
            await update.message.reply_text("⚠️ Token not found. Please enter your name to register as a new patient.")
            return NAME
    except Exception as e:
        print(f"Token check error: {e}")
        await update.message.reply_text("❌ Server error while checking token.")
        return NAME

async def ask_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text("📅 How old are you?")
    return AGE

async def ask_symptoms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["age"] = update.message.text.strip()
    await update.message.reply_text("💬 Please describe your current symptoms (e.g., nausea, headache, pain, etc.)")
    return SYMPTOMS

async def get_medicine_advice(symptoms: str, age: str) -> str:
    try:
        prompt = (
            f"Patient is {age} years old and reports these symptoms: {symptoms}. "
            "This is an Indian pregnant woman. Suggest safe medicine (preferably OTC if possible), "
            "dosage, and precautions. Also mention if a doctor visit is required."
        )
        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful, empathetic medical assistant for Indian pregnant women."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.7
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"OpenAI Error: {e}")
        return "⚠️ Unable to fetch advice right now."

async def handle_symptoms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["symptoms"] = update.message.text.strip()
        token = context.user_data["token"]
        name = context.user_data["name"]
        age = context.user_data["age"]
        symptoms = context.user_data["symptoms"]

        patient = {
            "token": token,
            "name": name,
            "age": age,
            "symptoms": symptoms
        }
        requests.post("http://localhost:5000/save_patient", json=patient)

        await update.message.reply_text("⏳ Analyzing your symptoms...")
        advice = await get_medicine_advice(symptoms, age)
        await update.message.reply_text(f"👩‍⚕️ {name}, here is your health suggestion:\n\n{advice}")
        return ConversationHandler.END

    except Exception as e:
        print(f"Handle Error: {e}")
        await update.message.reply_text("⚠️ Something went wrong.")
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Session cancelled.")
    return ConversationHandler.END

if __name__ == '__main__':
    print("🚀 Starting bot...")
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            TOKEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_token)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_age)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_symptoms)],
            SYMPTOMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_symptoms)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.run_polling()
