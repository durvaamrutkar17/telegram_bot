import logging
import os
import openai
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ChatAction
from flask import Flask, render_template

# --- Load environment variables ---
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- OpenAI Client Setup ---
openai.api_key = OPENAI_API_KEY

# --- System Prompt ---
SYSTEM_PROMPT = """
You are a helpful and caring AI assistant providing general information about pregnancy.
Your rules are:
1. ⚠️ This is general information and not medical advice. Always consult a healthcare professional.
2. NEVER recommend specific medications, dosages, or brands. If asked about medicine, state that you cannot give medical advice and that the user must talk to a doctor.
3. ALWAYS end every response by strongly recommending the user to consult a doctor or a qualified healthcare provider for any personal health questions.
4. Keep your answers informative, safe, and general. Do not provide personal opinions or diagnosis.
5. If the question is unrelated to pregnancy or prenatal care, politely decline to answer.
"""

# --- Logging Setup ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- OpenAI Interaction Function ---
async def get_openai_response(user_prompt: str) -> str:
    try:
        logger.info(f"Sending prompt to OpenAI: {user_prompt}")

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=250
        ))

        return response.choices[0].message["content"].strip()
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}")
        return "I'm sorry, but I'm having trouble connecting to my information source right now. Please try again later."

# --- Telegram Bot Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hi! I am an AI assistant providing general information on pregnancy symptoms and care.\n\n"
        "Ask me a question, like 'What are common symptoms in the first trimester?' or 'Why is folic acid important?'\n\n"
        "⚠️ *Remember, I am not a doctor. My information is not a substitute for professional medical advice.*"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    ai_response = await get_openai_response(user_message)
    await update.message.reply_text(ai_response)

# --- Main Bot Logic ---
def main() -> None:
    if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
        print("Error: TELEGRAM_TOKEN or OPENAI_API_KEY not set in .env")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    application.run_polling()
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')
if __name__ == '__main__':
    app.run(debug=True)
    main()
