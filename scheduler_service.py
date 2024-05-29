import asyncio
import datetime
import logging
import typing

import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from httpx import AsyncClient, RequestError
import pytz
from telegram.constants import ParseMode

from config import (REDMINE_API_KEY, REDMINE_URL, SCHEDULER_MISSFIRE_GRACE_TIME, 
                    CRON_HOUR, CRON_MINUTE, HOURS_THRESHOLD, GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS_JSON)

if typing.TYPE_CHECKING:
    from tg_service import TelegramService

logger = logging.getLogger('app')

# Определяем временную зону UTC+3
TZ = pytz.timezone('Europe/Moscow')

# Укажите области, которые будут использоваться
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

class ScheduleService:
    scheduler: AsyncIOScheduler
    tg_service: 'TelegramService' = None
    pending_task: asyncio.Task = None
    tasks: list

    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler(timezone=TZ)
        self._add_jobs()

    async def start(self):
        self.scheduler.start()

    async def stop(self):
        self.scheduler.shutdown(wait=True)

    def _add_jobs(self):
        logger.info(f'Настройка задания на {CRON_HOUR:02d}:{CRON_MINUTE:02d} (UTC+3)')
        self.scheduler.add_job(
            func=self.check_hours,
            trigger=CronTrigger(hour=CRON_HOUR, minute=CRON_MINUTE, timezone=TZ),
            misfire_grace_time=SCHEDULER_MISSFIRE_GRACE_TIME
        )

    def _get_employees_from_google_sheet(self):
        creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_JSON, scopes=SCOPES)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        logger.info(f'Названия столбцов из Google Sheet: {df.columns.tolist()}')
        return df

    async def check_hours(self):
        try:
            logger.info('Запуск проверки часов')
            employees = self._get_employees_from_google_sheet()
            logger.info(f'Названия столбцов DataFrame: {employees.columns.tolist()}')  # Вывод имен столбцов для отладки
            yesterday = (datetime.datetime.now(TZ) - datetime.timedelta(days=1)).strftime('%Y%m%d')
            logger.info(f'Собираем часы на дату {yesterday}')
  # Преобразуем дату из ГГГГММДД в ГГГГ-ММ-ДД, который понимает redmine по API
            year = yesterday[:4]
            month = yesterday[4:6]
            day = yesterday[6:]
            yesterday = f"{year}-{month}-{day}"
            logger.info(f'Дата после преобразования {yesterday}')


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

                if hours < required_hours - HOURS_THRESHOLD:
                    message = (f'{name}, правильно ли я вижу, что ты затрекал(а) {hours} часов за вчерашний день в Redmine?\n\n'
                               'Если все верно - ты молодец, ничего корректировать не нужно!\n\n'
                               'Если картина не соответствует действительности - исправь, пожалуйста, часы в Redmine прямо сейчас 🙏 ! '
                               'Через 15 минут я соберу все часы, которые будут в трекере и они попадут в отчет руководству 🧐 .')
                    await self.tg_service.send_message(chat_id, message, parse_mode=ParseMode.MARKDOWN)

                logger.info(f'Проверка для {name} завершена')

        except Exception as e:
            logger.error(f'Ошибка при проверке часов: {str(e)}', exc_info=True)

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

