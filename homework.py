"""бот для проверки статуса домашней работы."""
import logging
import os
import requests
import time
import telegram
from dotenv import load_dotenv

load_dotenv()


class ResponseStatus(Exception):
    """Ошибка для вывода статуса."""

    def __init__(self, *args):
        """просто init."""
        self.code_error = args[0]

    def __str__(self) -> str:
        """просто str."""
        return f'ResponseStatus error {self.code_error}'


PRACTICUM_TOKEN = os.getenv('YANDEX_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('USER_TOKEN')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s'
)
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())


def check_tokens():
    """Проверяем доступность переменных окружения."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN}
    for token, value in tokens.items():
        if value is None:
            logger.error(f'{token} not found')
    return all(tokens.values())


def send_message(bot, message):
    """отправка сообщений в телеграм."""
    logger.info('Попытка отправить сообщение')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(
            f'Сообщение в телеграм отправлено: {message}')
    except Exception:
        logger.error(
            f'Сообщение в телеграм  не отправлено: {message}')


def get_api_answer(timestamp):
    """Запрос к эндпоиту API."""
    logger.info('Начало запроса к API')
    try:
        resp = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
        if resp.status_code != 200:
            logging.error(
                f'ошибка в коде ответа, {resp.status_code}',
                f'params = {resp.params}')
            raise ResponseStatus(resp.status_code)
        return resp.json()
    except Exception as error:
        logging.error(f'Ошибка ресурса, {error}')
        raise SystemError(f'Ошибка ресурса, {error}')


def check_response(response):
    """Проверка ответа."""
    if not isinstance(response, dict):
        raise TypeError('Ответ не соответствует типу dict')
    if missed_keys := {'homeworks', 'current_date'} - response.keys():
        logger.error(f'В ответе API нет ожидаемых ключей: {missed_keys}')
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError('Тип перечня домашних работ не является списком')
    return homeworks


def parse_status(homework):
    """Статус работы."""
    status = homework.get('status')
    homework_name = homework.get('homework_name')
    if 'homework_name' not in homework or None:
        raise KeyError(f'Не найден {homework_name}.')
    if status not in HOMEWORK_VERDICTS or None:
        raise Exception('ошибка статуса сервера')
    verdict = HOMEWORK_VERDICTS.get(status)
    return f'Изменился статус проверки работы "{homework_name}": {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('нет токена')
        raise SystemExit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_error = ''
    last_message = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            timestamp = response.get('current_date')
            if len(homeworks) == 0:
                message = 'Домашка ещё не проверена'
            else:
                message = parse_status(homeworks[0])
            if last_message != message:
                send_message(bot, message)
                last_message = message
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if last_error != message:
                send_message(bot, message)
                last_error = message
            logging.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
