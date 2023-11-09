import logging
import os
import sys
import time

import requests
import telegram

from dotenv import load_dotenv


load_dotenv()
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


log_format = '%(asctime)s [%(levelname)s] %(message)s'
logging.basicConfig(
    filename='homework_bot.log', format=log_format
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)


def check_tokens():
    """Проверка переменных окружения."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception:
        logger.error('Сообщение не отправлено')
    logger.debug('Уcпешная отправка сообщения')


def get_api_answer(timestamp):
    """Запрос к API-сервису."""
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params={'from_date': timestamp}
        )
        response.raise_for_status()
    except requests.RequestException as error:
        logger.error(error)
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        bot.send_message(TELEGRAM_CHAT_ID, f'{error}')
    if response.status_code == 200:
        return response.json()
    raise requests.HTTPError()


def check_response(response):
    """Проверка ответа API."""
    NOT_KEY = 'Отсутствует ожидаемый ключ "homeworks"'
    if type(response) is not dict:
        logger.error('Ответ API не соответствует ожидаемому типу')
        raise TypeError('Ответ API не соответствует ожидаемому типу')
    elif response.get('homeworks') is None:
        logger.error(NOT_KEY)
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        bot.send_message(TELEGRAM_CHAT_ID, NOT_KEY)
        raise KeyError(NOT_KEY)
    elif not isinstance(response['homeworks'], list):
        raise TypeError('Значение ключа "homeworks" не является списком')
    return True


def parse_status(homework):
    """Получить статус проверки работы."""
    try:
        homework_name = homework['homework_name']
    except KeyError:
        raise KeyError(
            'В списке "homeworks" отсутствует ключ "homework_name"'
        )
    try:
        verdict = HOMEWORK_VERDICTS[homework['status']]
    except KeyError:
        logger.error('Неожиданный статус домашней работы')
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        bot.send_message(
            TELEGRAM_CHAT_ID, 'Неожиданный статус домашней работы'
        )
        raise KeyError('В списке "homeworks" отсутствует ключ "status"')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствует обязательная переменная окружения')
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            if check_response(response):
                for homework in response.get('homeworks'):
                    message = parse_status(homework)
                    send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(f'Сбой в работе программы: {error}')
            bot.send_message(TELEGRAM_CHAT_ID, f'{error}')
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
