class HttpError(Exception):
    """Ошибка http запроса."""

    pass


class ApiError(Exception):
    """Ошибка при запросе к API."""

    pass


class TokenError(Exception):
    """Не хватает переменных окружения."""

    pass


class JsonError(Exception):
    """Проблемы с JSON."""

    pass
