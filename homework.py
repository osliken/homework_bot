import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

import exceptions


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
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)


def check_tokens():
    """Проверка переменных окружения."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    missing_tokens = []
    for name, value in tokens.items():
        if not value:
            missing_tokens.append(name)
    return missing_tokens


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        logger.info('Сообщение отправляется')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError as error:
        logger.error(
            f'Не удалось отправить сообщение: {error}'
        )
    logger.debug('Уcпешная отправка сообщения')


def get_api_answer(timestamp):
    """Запрос к API-сервису."""
    request = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp}
    }
    try:
        logger.info(
            'Отправляется запрос: {url}; '
            'Данные заголовка: {headers}; '
            'Параметры: {params}'.format(**request)
        )
        response = requests.get(**request)
        response.raise_for_status()
    except requests.RequestException as error:
        raise exceptions.RequestError(f'нет ответа от API: {error}')
    if response.status_code == HTTPStatus.OK:
        return response.json()
    raise exceptions.HTTPError(
        'Ошибка ' + str(response.status_code) + ': {url}; '
        'Данные заголовка: {headers}; '
        'Параметры: {params}'.format(**request)
    )


def check_response(response):
    """Проверка ответа API."""
    if not isinstance(response, dict):
        raise TypeError('ответ API не соответствует ожидаемому типу')
    try:
        homeworks = response['homeworks']
    except KeyError as error:
        raise exceptions.EmptyResponseAPI(
            f'пустой ответ от API, нет ключа {error}'
        )
    if not isinstance(homeworks, list):
        raise TypeError(
            'в ответе от API ключ "homeworks" не является списком'
        )
    return homeworks


def parse_status(homework):
    """Получить статус проверки работы."""
    try:
        homework_name = homework['homework_name']
    except KeyError as error:
        raise KeyError(
            f'в списке "homeworks" отсутствует ключ {error}'
        )
    verdict = HOMEWORK_VERDICTS.get(homework.get('status'))
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError(
            f'неизвестный статус домашней работы: {homework_status}'
        )
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    tokens = check_tokens()
    if tokens:
        tokens = str(tokens)[1:-1]
        logger.critical(
            f'Отсутствуют обязательные переменные окружения: {tokens}'
        )
        raise exceptions.ExitError(
            f'Отсутствуют обязательные переменные окружения: {tokens}'
        )
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = 0
    old_status = ''
    new_status = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get('current_data', timestamp)
            homeworks = check_response(response)
            if not homeworks:
                new_status = 'Нет новых статусов'
            else:
                homework = homeworks[0]
                new_status = parse_status(homework)
            if old_status != new_status:
                send_message(bot, new_status)
        except exceptions.EmptyResponseAPI as error:
            logger.error(f'Пустой ответ от API: {error}')
        except Exception as error:
            logger.error(f'Сбой в работе программы: {error}')
            if old_status != new_status:
                bot.send_message(
                    TELEGRAM_CHAT_ID, f'Сбой в работе программы: {error}'
                )
        finally:
            old_status = new_status
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        filename='homework_bot.log', format=log_format, encoding='UTF-8'
    )
    main()
