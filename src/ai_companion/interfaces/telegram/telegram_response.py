import logging
import os
from io import BytesIO
from typing import Dict, Optional, Tuple

import httpx
from fastapi import APIRouter, Request, Response
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

# Importa tus módulos existentes
from ai_companion.graph import graph_builder
from ai_companion.modules.image import ImageToText
from ai_companion.modules.speech import SpeechToText, TextToSpeech
from ai_companion.settings import settings

logger = logging.getLogger(__name__)

# --- Módulos Globales (sin cambios) ---
speech_to_text = SpeechToText()
text_to_speech = TextToSpeech()
image_to_text = ImageToText()

# --- Router para Telegram ---
telegram_router = APIRouter()

# --- Credenciales de la API de Telegram ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


async def download_telegram_file(file_id: str) -> Optional[bytes]:
    """Descarga un archivo desde los servidores de Telegram usando su file_id."""
    async with httpx.AsyncClient() as client:
        # 1. Obtener la ruta del archivo (file_path)
        get_file_url = f"{TELEGRAM_API_URL}/getFile"
        response = await client.post(get_file_url, json={"file_id": file_id})
        if response.status_code != 200:
            logger.error(f"Error al obtener info del archivo: {response.text}")
            return None
        
        file_path = response.json()["result"]["file_path"]
        
        # 2. Descargar el archivo usando el file_path
        file_download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
        file_response = await client.get(file_download_url)
        
        if file_response.status_code != 200:
            logger.error(f"Error al descargar el archivo: {file_response.text}")
            return None
            
        return file_response.content


@telegram_router.post("/telegram_response")
async def telegram_handler(request: Request) -> Response:
    """Maneja las actualizaciones (mensajes) entrantes desde un webhook de Telegram."""
    try:
        data = await request.json()
        
        # Extraer el mensaje del objeto de actualización de Telegram
        if "message" not in data:
            logger.warning("Actualización sin mensaje recibida.")
            return Response(status_code=200) # Responde OK para que Telegram no reintente

        message = data["message"]
        chat_id = message["chat"]["id"]
        session_id = str(chat_id)  # LangGraph necesita un string para thread_id

        content = ""
        image_bytes = None

        # Determinar el tipo de mensaje y procesarlo
        if "text" in message:
            content = message["text"]
        
        elif "voice" in message: # Para notas de voz
            voice_id = message["voice"]["file_id"]
            audio_bytes = await download_telegram_file(voice_id)
            if audio_bytes:
                content = await speech_to_text.transcribe(audio_bytes)
            else:
                content = "[Error al procesar el audio]"
        
        elif "photo" in message: # Para imágenes
            # Telegram envía varias resoluciones, usamos la más alta
            photo_id = message["photo"][-1]["file_id"]
            image_bytes = await download_telegram_file(photo_id)
            content = message.get("caption", "") # Usar el pie de foto si existe
            
            if image_bytes:
                try:
                    description = await image_to_text.analyze_image(
                        image_bytes,
                        "Please describe what you see in this image in the context of our conversation."
                    )
                    content += f"\n[Análisis de Imagen: {description}]"
                except Exception as e:
                    logger.warning(f"Fallo al analizar la imagen: {e}")
            else:
                content += "\n[Error al procesar la imagen]"

        else:
            # Ignorar otros tipos de mensaje por ahora (stickers, documentos, etc.)
            logger.info(f"Tipo de mensaje no soportado recibido: {message.keys()}")
            return Response(status_code=200)

        # --- Lógica del Agente (sin cambios) ---
        async with AsyncSqliteSaver.from_conn_string(settings.SHORT_TERM_MEMORY_DB_PATH) as short_term_memory:
            graph = graph_builder.compile(checkpointer=short_term_memory)
            await graph.ainvoke(
                {"messages": [HumanMessage(content=content)]},
                {"configurable": {"thread_id": session_id}},
            )

            output_state = await graph.aget_state(config={"configurable": {"thread_id": session_id}})

        workflow = output_state.values.get("workflow", "conversation")
        response_message = output_state.values["messages"][-1].content

        # --- Enviar Respuesta al Usuario ---
        if workflow == "audio":
            audio_buffer = output_state.values["audio_buffer"]
            await send_telegram_media(chat_id, "voice", audio_buffer)
        elif workflow == "image":
            image_path = output_state.values["image_path"]
            with open(image_path, "rb") as f:
                image_data = f.read()
            await send_telegram_media(chat_id, "photo", image_data, caption=response_message)
        else:
            await send_telegram_text(chat_id, response_message)

        return Response(content="OK", status_code=200)

    except Exception as e:
        logger.error(f"Error procesando el mensaje de Telegram: {e}", exc_info=True)
        return Response(content="Internal server error", status_code=500)


async def send_telegram_text(chat_id: int, text: str) -> bool:
    """Envía un mensaje de texto a un chat de Telegram."""
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown" # Opcional, para formato
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
    if response.status_code != 200:
        logger.error(f"Error al enviar texto a Telegram: {response.text}")
        return False
    return True


async def send_telegram_media(
    chat_id: int, 
    media_type: str, # "photo" o "voice"
    media_content: bytes, 
    caption: str = None
) -> bool:
    """Envía un medio (foto o audio) a un chat de Telegram."""
    if media_type == "photo":
        url = f"{TELEGRAM_API_URL}/sendPhoto"
        files = {"photo": ("image.png", media_content, "image/png")}
    elif media_type == "voice":
        url = f"{TELEGRAM_API_URL}/sendVoice"
        files = {"voice": ("voice.ogg", media_content, "audio/ogg")}
    else:
        logger.error(f"Tipo de media no soportado: {media_type}")
        return False
        
    data = {"chat_id": str(chat_id)}
    if caption:
        data["caption"] = caption

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, data=data, files=files)
        
    if response.status_code != 200:
        logger.error(f"Error al enviar media a Telegram: {response.text}")
        return False
    return True