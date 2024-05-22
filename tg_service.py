import logging
import typing

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import (Application, CallbackContext, CommandHandler,
                          MessageHandler, filters)

from config import CHATS_PATH, TELEGRAM_BOT_TOKEN

if typing.TYPE_CHECKING:
    from scheduler_service import ScheduleService

logger = logging.getLogger('app')


class TelegramService:
    bot_app: Application
    scheduler: 'ScheduleService' = None

    def __init__(self):
        self.bot_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self._add_handlers(self.bot_app)

    def _add_handlers(self, app: Application):
        app.add_handler(CommandHandler('start', self._start_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_response))

    async def start(self):
        await self.bot_app.initialize()
        await self.bot_app.start()
        await self.bot_app.updater.start_polling()

    async def stop(self):
        await self.bot_app.stop()


    async def send_message(self, chat_id, text):
        try:
            logger.info(f'Отправка сообщения в Telegram: {text}')
            await self.bot_app.bot.send_message(chat_id=chat_id, text=text,
                                                parse_mode=ParseMode.MARKDOWN)
            logger.info('Сообщение отправлено успешно')
        except TelegramError as e:
            logger.error(f'Ошибка при отправке сообщения в Telegram: {e}')

    async def _start_command(self, update: Update, _: CallbackContext):
        logger.info('Команда /start получена')
        chat_id = update.message.chat_id
        user_name = update.message.from_user.username
        logger.info(f'chat_id: {chat_id}, user_name: {user_name}')
        with open(CHATS_PATH / f'{user_name}.txt', 'a') as file:
            file.write(str(chat_id))
        logger.info('Сохранен chat_id в файл')
        try:
            logger.info(f'Попытка отправить сообщение пользователю {user_name}')
            await update.message.reply_text('Спасибо за запуск бота Mobicult 🎉!\n\nЯ сохранил код переписки, как только (в ближайшее время) его добавят мне в базу, я начну напоминать тебе о важных вещах 😉', parse_mode=ParseMode.MARKDOWN)
            logger.info(f'Отправлено сообщение: Спасибо за запуск бота! пользователю {user_name}')
        except Exception as e:
            logger.error(f'Ошибка при отправке сообщения: {e}')
        logger.info(f'Chat ID {chat_id} для пользователя {user_name} сохранен')

#        await self.scheduler.check_hours()

    async def handle_response(self, update: Update, _: CallbackContext):
        response = update.message.text.lower()
        chat_id = update.message.chat_id
        logger.info(f'Получен ответ от {chat_id}: {response}')
        if 'да' in response or 'верно' in response:
            await self.send_message(chat_id, 'Спасибо за подтверждение!\n\n Для нас очень важно, чтобы в трекере содержались честные часы, чтобы мы могли спланировать занятость команды.', parse_mode=ParseMode.MARKDOWN)
        elif 'нет' in response or 'неверно' in response:
            await self.send_message(chat_id, 'Исправь, пожалуйста, часы в Redmine прямо сейчас 🙏 ! Через 15 минут я соберу все часы, которые будут в трекере и они попадут в отчет руководству.', parse_mode=ParseMode.MARKDOWN)

