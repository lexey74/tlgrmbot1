import logging
import sys
import os
from contextlib import asynccontextmanager
from logging.config import dictConfig

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from telegram import Update
from telegram.error import TelegramError
from dotenv import load_dotenv

from config import LOGGER_CONFIG, TELEGRAM_BOT_TOKEN, WEBHOOK_URL

# Импортируем необходимые классы
from tg_service import TelegramService
from scheduler_service import ScheduleService

logger = logging.getLogger('app')

# Загрузка переменных окружения из .env файла
load_dotenv()

# Получение списка доверенных IP-адресов из переменных окружения
TRUSTED_IP_RANGES = os.getenv("TRUSTED_IP_RANGES", "").split(",")

def is_trusted_ip(ip: str) -> bool:
    ip_addr = ipaddress.ip_address(ip)
    for ip_range in TRUSTED_IP_RANGES:
        if ip_addr in ipaddress.ip_network(ip_range.strip()):
            return True
    return False

class CustomFastAPI(FastAPI):
    tg: 'TelegramService'
    scheduler: 'ScheduleService'


@asynccontextmanager
async def lifespan(app: CustomFastAPI):
    sys.stdout.reconfigure(encoding='utf-8')
    dictConfig(LOGGER_CONFIG)

    app.tg = TelegramService()
    app.scheduler = ScheduleService()
    app.tg.scheduler, app.scheduler.tg_service = app.scheduler, app.tg

    await app.tg.start()
    await app.scheduler.start()

    yield

    await app.scheduler.stop()
    await app.tg.stop()


app = CustomFastAPI(lifespan=lifespan)


def get_app() -> CustomFastAPI:
    return app


@app.post(f'/{TELEGRAM_BOT_TOKEN}')
async def webhook(request: Request, app: CustomFastAPI = Depends(get_app)):
    # Test IP address
    client_host = request.client.host
    if not is_trusted_ip(client_host):
        logger.warning(f'Недоверенный IP-адрес: {client_host}')
        raise HTTPException(status_code=403, detail="Forbidden")

    
    if request.headers.get('Content-Type') == 'application/json':
        logger.info(f'Получен Webhook запрос: {await request.body()}')
        update = Update.de_json(await request.json(), app.tg.bot_app.bot)
        logger.info('Обработка Webhook запроса...')
        try:
            await app.tg.bot_app.process_update(update)
            logger.info('Webhook запрос обработан.')
        except Exception as error:
            logger.exception(f'Webhook: {error}')
        return JSONResponse(content={'message': 'ok'}, status_code=200)
    else:
        return HTTPException(status_code=415, detail='Unsupported Media Type')


@app.api_route('/set_webhook', methods=['GET', 'POST'])
async def set_webhook(app: CustomFastAPI = Depends(get_app)):
    url = f'{WEBHOOK_URL}/{TELEGRAM_BOT_TOKEN}'
    try:
        await app.tg.bot_app.bot.setWebhook(url)
        return 'Webhook setup successful'
    except TelegramError as error:
        logger.error(error)
        return 'Webhook setup failed'

