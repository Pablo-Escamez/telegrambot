# main.py (Versión WhatsApp Y Telegram)

from fastapi import FastAPI
from ai_companion.interfaces.telegram.telegram_response import telegram_router

app = FastAPI()

# Y también incluyes el router de Telegram
app.include_router(telegram_router)
