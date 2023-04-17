class SendMessageError(Exception):
    """Проблема с отправкой сообщения."""

    pass


class HttpError(Exception):
    """Ошибка http запроса."""

    pass


class ApiError(Exception):
    """Ошибка при запросе к API."""

    pass
