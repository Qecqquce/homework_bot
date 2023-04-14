import logging
import os
import requests
import time

import telegram
from http import HTTPStatus
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('TOKEN_YANDEX')
TELEGRAM_TOKEN = os.getenv('TOKEN_TELEGRAM')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """ПРОВЕРЯЕМ ДОСТУПНОСТЬ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ."""
    for token in (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID):
        if token is None:
            logging.critical(f'Отсутствует переменная окружения {token}\n'
                             f'Программа остановлена.')
            exit()
    return (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)


def send_message(bot, message):
    """ОТПРАВЛЯЕМ СООБЩЕНИЕ В ТЕЛЕГРАММ."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Сообщение успешно отправлено!')
    except Exception:
        logging.error('Сообщение не отправлено!')


def get_api_answer(timestamp):
    """ДЕЛАЕМ ЗАПРОС К ENDPOINT."""
    params = {'from_date': timestamp}
    logging.info(f'Отправка запроса на {ENDPOINT} с параметрами {params}')
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            raise ('Код ответа не 200.')
    except Exception as error:
        logging.error(f'Ошибка при запросе к API: {error}')
        raise ('Ошибка при запросе к API')
    return response.json()


def check_response(response):
    """ПРОВЕРЯЕМ ОТВЕТ API НА КОРРЕКТНОСТЬ."""
    if not isinstance(response, dict):
        logging.info('Некорректный ответ от API!')
        raise TypeError('Ответ не ввиде словаря!')
    homeworks = response.get('homeworks')
    if homeworks is None:
        raise KeyError('Ответ не содержит ключ Homeworks')
    if not isinstance(homeworks, list):
        logging.info('Ответ не ввиде списка!')
        raise TypeError('Ответ не ввиде списка!')
    return homeworks


def parse_status(homework: dict) -> str:
    """ИЗВЛЕКАЕТ СТАТУС ДОМАШНЕЙ РАБОТЫ."""
    if not homework.get('homework_name'):
        logging.warning('Отсутствует имя домашней работы.')
        raise KeyError
    else:
        homework_name = homework.get('homework_name')

    homework_status = homework.get('status')
    if 'status' not in homework:
        message = 'Отсутстует ключ homework_status.'
        logging.error(message)

    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if homework_status not in HOMEWORK_VERDICTS:
        message = 'Неизвестный статус домашней работы'
        logging.error(message)
        raise KeyError(message)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    last_send = {
        'error': None,
    }
    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 1681465700

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if len(homeworks) == 0:
                logging.debug('Ответ API пуст: нет домашних работ.')
                break
            for homework in homeworks:
                message = parse_status(homework)
                if last_send.get(homework['homework_name']) != message:
                    send_message(bot, message)
                    last_send[homework['homework_name']] = message
            current_timestamp = response.get('current_date')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if last_send['error'] != message:
                send_message(bot, message)
                last_send['error'] = message
        else:
            last_send['error'] = None
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
