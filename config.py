import os
import pathlib
from dotenv import load_dotenv


load_dotenv()
APP_DIR = pathlib.Path(__file__).absolute().parent
LOG_PATH_DIR = APP_DIR / 'logs'
CHATS_PATH = APP_DIR / 'chats'

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
REDMINE_API_KEY = os.getenv('REDMINE_API_KEY')
REDMINE_URL = os.getenv('REDMINE_URL')
CSV_FILE_PATH = os.getenv('CSV_FILE_PATH')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
SCHEDULER_MISSFIRE_GRACE_TIME = 600


LOGGER_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'main_formatter': {
            'format': (
                '%(levelname)1.1s %(asctime)s %(name)s - %(message).600s'
                ' - %(filename)s - %(funcName)s - %(lineno)s'
            ),
            'datefmt': "%d.%m %H:%M:%S",
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'main_formatter',
        },
        'fileAppHandler': {
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': (LOG_PATH_DIR / 'app.log').as_posix(),
            'formatter': 'main_formatter',
            'when': 'midnight',
            'backupCount': 5,
        },
    },
    'loggers': {
        'app': {
            'handlers': ['console', 'fileAppHandler'],
            'level': 'DEBUG',
        },
    },
}

