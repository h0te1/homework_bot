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
    filemod='w',
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
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(
            f'Сообщение в телеграм отправлено: {message}')
    except Exception:
        logger.error(
            f'Сообщение в телеграм  не отправлено: {message}')


def get_api_answer(timestamp):
    """Запрос к эндпоиту API."""
    try:
        hw_stat = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'form_date': timestamp}
        )
        if hw_stat.status_code != 200:
            logging.error(
                f'ошибка ресурса, {hw_stat.status_code}')
            raise ResponseStatus(hw_stat.status_code)
        return hw_stat.json()
    except Exception as error:
        logging.error(f'Ошибка ресурса, {error}')
        raise SystemError(f'Ошибка ресурса, {error}')


def check_response(response):
    """Проверка ответа."""
    if not isinstance(response, dict):
        raise TypeError('Переменная не соответствует типу dict')
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError('Тип перечня домашних работ не является списком')
    return response.get('homeworks')[0]


def parse_status(homework):
    """Статус работы."""
    status = homework.get('status')
    homework_name = homework.get('homework_name')
    if 'homework_name' not in homework or None:
        raise KeyError(f'Не найден {homework_name}.')
    if status not in HOMEWORK_VERDICTS is None:
        raise Exception('ошибка статуса сервера')
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


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
            if not homeworks:
                message = 'Домашка ещё не сдана'
            else:
                message = parse_status(homeworks[0])
            if last_message != message:
                send_message(bot, message)
                last_message = message
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if last_error != error:
                send_message(bot, message)
                last_error = error
            logging.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
