import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv


from exceptions import ApiError, SendMessageError, HttpError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('TOKEN_YANDEX')
TELEGRAM_TOKEN = os.getenv('TOKEN_TELEGRAM')
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
    for token in [{'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
                   'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
                   'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID}]:
        if None in token.values():
            logger.critical(f'Отсутствует переменная окружения {token}')
            raise SystemExit('Проверь токены!')


def send_message(bot, message):
    """ОТПРАВЛЯЕМ СООБЩЕНИЕ В ТЕЛЕГРАММ."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except SendMessageError:
        logger.error('Сообщение не отправлено!Проверь id чата или бота.')
    else:
        logger.debug('Сообщение успешно отправлено!')


def get_api_answer(timestamp):
    """ДЕЛАЕМ ЗАПРОС К ENDPOINT."""
    params = {'from_date': timestamp}
    logger.info(f'Отправка запроса на {ENDPOINT} с параметрами {params}')
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != HTTPStatus.OK:
        raise HttpError('Код ответа != 200.')
    return response.json()


def check_response(response):
    """ПРОВЕРЯЕМ ОТВЕТ API НА КОРРЕКТНОСТЬ."""
    if not isinstance(response, dict):
        logger.info('Некорректный ответ от API!')
        raise TypeError('Ответ не ввиде словаря!')
    homeworks = response.get('homeworks')
    current_dates = response.get('current_date')
    if homeworks is None:
        raise ValueError('Ответ не содержит значение Homeworks')
    if current_dates is None:
        raise ValueError('Ответ не содержит значение current_date')
    if not isinstance(homeworks, list):
        logger.info('Ответ не ввиде списка!')
        raise TypeError('Ответ не ввиде списка!')
    return homeworks


def parse_status(homework: dict) -> str:
    """ИЗВЛЕКАЕТ СТАТУС ДОМАШНЕЙ РАБОТЫ."""
    if not homework.get('homework_name'):
        logger.warning('Отсутствует имя домашней работы.')
        raise KeyError
    homework_name = homework.get('homework_name')

    homework_status = homework.get('status')
    if 'status' not in homework:
        message = 'Отсутстует ключ homework_status.'
        logging.error(message)

    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if homework_status not in HOMEWORK_VERDICTS:
        message = 'Неизвестный статус домашней работы'
        logger.error(message)
        raise ValueError(message)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    old_message = ''
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    while True:
        timestamp = int(time.time())
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
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
                timestamp = int(time.time())
        except ApiError:
            logger.error(f'Ошибка при запросе к API: {ApiError}')
        except ValueError as e:
            logger.error('Проблемы с json форматом', e)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message != old_message:
                old_message = message
                send_message(bot, message)
            logger.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
