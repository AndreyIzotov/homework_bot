import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
    filemode='a',
)

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщения."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        return True
    except Exception as error:
        error_message = f'Ошибка при отправке сообщения: {error}'
        logger.error(error_message)


def get_api_answer(current_timestamp):
    """Проверка от вета API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            logger.error('Код ответа != 200')
            raise ConnectionError('Ошибка статуса ответа от API')
    except Exception as error:
        error_message = f'Ошибка при запросе к API: {error}'
        logger.error(error_message)
        raise ConnectionError(error_message)
    response = response.json()
    return response


def check_response(response):
    """Проверка ответа сервера."""
    if not isinstance(response['homeworks'], list):
        error_message = 'Ответ API не соответствует ожиданиям'
        logger.error(error_message)
        raise TypeError(error_message)
    try:
        homeworks = response['homeworks']
    except Exception as error:
        error_message = f'Работ по ключу homeworks не найдено {error}'
        logger.error(error_message)
        raise KeyError(error_message)
    return homeworks


def parse_status(homework):
    """Проверка статуса работ."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES.keys():
        error_message = 'Неверное значение статуса работы'
        logger.error(error_message)
        raise KeyError(error_message)
    if homework_name is None or homework_status is None:
        error_message = 'Ответ сервера не соответствует ожиданиям'
        logger.error(error_message)
        raise ValueError(error_message)
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка локальных токенов."""
    tokens = all([
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID
    ])
    return tokens


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        error_message = 'Ошибка проверки токенов'
        logger.error(error_message)
        raise KeyError(error_message)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework:
                send_message(bot, parse_status(homework[0]))
            current_timestamp = response.get('current_date',
                                             current_timestamp)
            time.sleep(RETRY_TIME)
        except Exception as error:
            error_message = f'Сбой в работе программы: {error}'
            result = send_message(bot, error_message)
            if result:
                send_message(bot, error_message)
                logger.error(error_message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
