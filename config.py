import os
import pathlib
from dotenv import load_dotenv

load_dotenv()
APP_DIR = pathlib.Path(__file__).absolute().parent
LOG_PATH_DIR = APP_DIR / 'logs'
CHATS_PATH = APP_DIR / 'chats'

# Переменные из .env файла
REDMINE_API_KEY = os.getenv('REDMINE_API_KEY')
REDMINE_URL = os.getenv('REDMINE_URL')

GOOGLE_CREDENTIALS_JSON = os.getenv('GOOGLE_CREDENTIALS_JSON')
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

CRON_HOUR = int(os.getenv('CRON_HOUR', 13))
CRON_MINUTE = int(os.getenv('CRON_MINUTE', 0))
HOURS_THRESHOLD = float(os.getenv('HOURS_THRESHOLD', 0.5))
SCHEDULER_MISSFIRE_GRACE_TIME = int(os.getenv('SCHEDULER_MISSFIRE_GRACE_TIME', 600))

TRUSTED_IP_RANGES = os.getenv('TRUSTED_IP_RANGES', '').split(',')


# Проверка наличия всех необходимых переменных среды
required_env_vars = {
    'TELEGRAM_BOT_TOKEN': TELEGRAM_BOT_TOKEN,
    'REDMINE_API_KEY': REDMINE_API_KEY,
    'REDMINE_URL': REDMINE_URL,
    'WEBHOOK_URL': WEBHOOK_URL,
    'GOOGLE_SHEET_ID': GOOGLE_SHEET_ID,
    'GOOGLE_CREDENTIALS_JSON': GOOGLE_CREDENTIALS_JSON,
}

missing_vars = [key for key, value in required_env_vars.items() if not value]
if missing_vars:
    raise EnvironmentError(f'Missing required environment variables: {", ".join(missing_vars)}')

# Конфигурация логгирования
LOGGER_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'main_formatter': {
            'format': (
                '%(levelname)1.1s %(asctime)s %(name)s - %(message).20600s'
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

