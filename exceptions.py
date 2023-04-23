class HttpError(Exception):
    """Ошибка http запроса."""

    pass


class ApiError(Exception):
    """Ошибка при запросе к API."""

    pass


class TokenError(Exception):
    """Не хватает переменных окружения."""

    pass


class JsonError(ValueError):
    """Проблемы с JSON."""

    pass


class CurrentDateError(Exception):
    """Отсутствует ключ "current_dates" или ответ не ввиде числа."""

    pass


class HomeworkStatusError(Exception):
    """Отсутстует ключ homework_status."""

    pass
