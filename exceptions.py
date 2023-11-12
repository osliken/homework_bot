class RequestError(Exception):
    """Исключение запроса."""

    pass


class HTTPError(Exception):
    """Исключение соединения запроса."""

    pass


class EmptyResponseAPI(Exception):
    """Исключение пустого ответа от API."""

    pass


class ExitError(Exception):
    """Исключение системного выхода из программы."""

    pass
