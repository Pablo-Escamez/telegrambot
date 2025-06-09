# Contenido COMPLETO para ai_companion/interfaces/telegram/telegram_response.py

import logging
import os
from io import BytesIO
import httpx
from fastapi import APIRouter, Request, Response, FastAPI  # <-- Importamos FastAPI aquí

# --- ¡LA APLICACIÓN SE DEFINE AQUÍ! ---
# Este es el objeto 'app' que Uvicorn está buscando.
app = FastAPI()

# --- El Router se define y se usa en el mismo archivo para simplificar ---
telegram_router = APIRouter()

# Lógica del bot (la he copiado de tu código anterior aquí mismo)
# ===================================================================

# Módulos y configuración (Asegúrate de que estas importaciones son correctas para tu proyecto)
# from ai_companion.graph import graph_builder
# from ai_companion.modules.image import ImageToText
# from ai_companion.modules.speech import SpeechToText, TextToSpeech
# from ai_companion.settings import settings
# from langchain_core.messages import HumanMessage
# from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# He puesto una ruta de prueba para verificar que el servidor se inicia
@telegram_router.post("/telegram_response")
async def telegram_handler(request: Request) -> Response:
    # Tu lógica del webhook va aquí...
    # Por ahora, solo devolvemos OK para probar.
    data = await request.json()
    logger.info(f"Recibido de Telegram: {data}")
    return Response(content="OK", status_code=200)

# --- Incluimos el router en la aplicación ---
app.include_router(telegram_router)

# --- Añadimos una ruta raíz para poder probar en el navegador ---
@app.get("/")
def read_root():
    return {"message": "Servicio de Bot para Telegram está corriendo correctamente!"}