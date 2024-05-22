import asyncio
import datetime
import logging
import typing
import os

import pandas as pd
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from httpx import AsyncClient, RequestError
import pytz
from dotenv import load_dotenv

from config import (CSV_FILE_PATH, REDMINE_API_KEY, REDMINE_URL,
                    SCHEDULER_MISSFIRE_GRACE_TIME)

if typing.TYPE_CHECKING:
    from tg_service import TelegramService

logger = logging.getLogger('app')

# Загружаем переменные окружения из .env файла
load_dotenv()

# Получаем час и минуту для выполнения задания из переменных окружения
CRON_HOUR = int(os.getenv('CRON_HOUR', 13))  # по умолчанию 13, если переменная не задана
CRON_MINUTE = int(os.getenv('CRON_MINUTE', 0))  # по умолчанию 0, если переменная не задана

# Получаем пороговое значение для разницы во времени из переменных окружения
TIME_DIFFERENCE_THRESHOLD = float(os.getenv('TIME_DIFFERENCE_THRESHOLD', 0.5))  # по умолчанию 0.5 часа

# Определяем временную зону UTC+3
TZ = pytz.timezone('Europe/Moscow')

class ScheduleService:
    scheduler: AsyncIOScheduler
    tg_service: 'TelegramService' = None
    pending_task: asyncio.Task = None
    tasks: list

    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler(timezone=TZ)  # Используем временную зону UTC+3
        self._add_jobs()

    async def start(self):
        self.scheduler.start()

    async def stop(self):
        self.scheduler.shutdown(wait=True)

    def _add_jobs(self):
        logger.info(f'Настройка задания на {CRON_HOUR:02d}:{CRON_MINUTE:02d} (UTC+3)')
        self.scheduler.add_job(
            func=self.check_hours,
            trigger=CronTrigger(hour=CRON_HOUR, minute=CRON_MINUTE, timezone=TZ),  # Указываем час и минуту из переменных окружения
            misfire_grace_time=SCHEDULER_MISSFIRE_GRACE_TIME
        )

    async def check_hours(self):
        try:
            logger.info('Запуск проверки часов')
            employees = pd.read_csv(CSV_FILE_PATH)
            yesterday = (datetime.datetime.now(TZ) - datetime.timedelta(days=1)).strftime('%Y%m%d')

            if not await self._is_workday(yesterday):
                logger.info(f'{yesterday} - нерабочий день')
                return

            for _, employee in employees.iterrows():
                user_id = employee['user_id']
                chat_id = employee['telegram_user_name']
                name = employee['name']
                required_hours = employee['hours_per_day']

                logger.info(f'Проверка часов для {name} (user_id: {user_id})')

                hours = await self._get_hours_from_redmine(user_id, yesterday)
                logger.info(f'{name} отработал {hours} часов, требуемые часы: {required_hours}')

                if hours < required_hours - TIME_DIFFERENCE_THRESHOLD: # Проверяем, что часов меньше требуемого на более, чем нужно 
                    message = f'Привет, {name}!\n\nУвидел в трекере, что у тебя за вчерашний день отработано {hours} часов(а). Это верная информация, оставляем так?\n(Подсказка: я понимаю ответ да/нет или верно/неверно)'
                    await self.tg_service.send_message(chat_id, message)

                logger.info(f'Проверка для {name} завершена')

        except Exception as e:
            logger.error(f'Ошибка при проверке часов: {e}')

    async def _is_workday(self, date):
        try:
            async with AsyncClient() as client:
                response = await client.get(url=f'https://isdayoff.ru/{date}')
                return response.text == '0'
        except RequestError as error:
            logger.error(error)

    async def _get_hours_from_redmine(self, user_id, date):
        try:
            async with AsyncClient() as client:
                response = await client.get(f'{REDMINE_URL}/time_entries.json?spent_on={date}',
                                            headers={'X-Redmine-API-Key': REDMINE_API_KEY})
            data = response.json()

            # Фильтрация записей по user_id
            total_hours = sum(entry['hours'] for entry in data['time_entries'] if entry['user']['id'] == user_id)
            return round(total_hours, 2)
        except Exception as e:
            logger.error(f'Ошибка при получении данных из Redmine для user_id {user_id} и date {date}: {e}')
            return 0.0

