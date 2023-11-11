import requests


class RequestError(requests.RequestException):
    """Исключение запроса."""

    pass


class HTTPError(requests.HTTPError):
    """Исключение соединения запроса."""

    pass


class EmptyResponseAPI(ValueError):
    """Исключение пустого ответа от API."""

    pass


class ExitError(SystemExit):
    """Исключение системного выхода из программы."""

    pass
