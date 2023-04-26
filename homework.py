import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (ApiError,
                        HttpError,
                        JsonError,
                        CurrentDateError,
                        HomeworkStatusError)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s -'
                              '%(levelname)s - %(message)s')
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

file_handler = logging.FileHandler(filename="logger.log")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """ПРОВЕРЯЕМ ДОСТУПНОСТЬ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ."""
    tokens = ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']
    missing_tokens = [key for key in tokens if not globals().get(key)]
    if missing_tokens:
        logger.critical(f'Отсутствует переменная окружения! {missing_tokens}')
        raise SystemExit('Проверь токены!')


def send_message(bot, message):
    """ОТПРАВЛЯЕМ СООБЩЕНИЕ В ТЕЛЕГРАММ."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError:
        logger.error('Сообщение не отправлено!Проверь id чата или бота.')
    else:
        logger.debug('Сообщение успешно отправлено!')


def get_api_answer(timestamp):
    """ДЕЛАЕМ ЗАПРОС К ENDPOINT."""
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            raise HttpError('Код ответа != 200.')
        return response.json()
    except requests.JSONDecodeError as json_error:
        raise JsonError('Ошибка JSON') from json_error
    except requests.RequestException as request_error:
        raise ApiError('Ошибка подключения к API') from request_error


def check_response(response):
    """ПРОВЕРЯЕМ ОТВЕТ API НА КОРРЕКТНОСТЬ."""
    if not isinstance(response, dict):
        raise TypeError('Ответ не ввиде словаря!')
    homeworks = response.get('homeworks')
    current_date = response.get('current_date')
    if homeworks is None:
        raise KeyError('Отсутсвует значение Homeworks')
    if current_date is None:
        raise CurrentDateError('Отсутствует ключ "current_dates"'
                               'или ответ не ввиде числа.')
    if not isinstance(homeworks, list):
        raise TypeError('Ответ не ввиде списка!')
    if not isinstance(current_date, int):
        raise CurrentDateError('Значение "current_date" не является "int"')
    return homeworks


def parse_status(homework: dict) -> str:
    """ИЗВЛЕКАЕТ СТАТУС ДОМАШНЕЙ РАБОТЫ."""
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise KeyError('Отсутствует ключ "homework_name"')

    homework_status = homework.get('status')
    if 'status' not in homework:
        raise HomeworkStatusError('Отсутстует ключ homework_status.')

    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError('Неизвестный статус домашней работы')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    old_message = ''
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            timestamp = response.get('current_date', timestamp)
            if homeworks:
                homework = homeworks[0]
                status = parse_status(homework)
            else:
                status = 'Нет изменений в статусе работы'
            if status != old_message:
                old_message = status
                send_message(bot, status)
            else:
                logger.debug('Нет изменений в статусе работы')
        except CurrentDateError:
            logger.error
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message != old_message:
                old_message = message
                send_message(bot, message)
            logger.error(message, bot)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
