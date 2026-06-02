class AppError(Exception):
    status_code: int = 500

    def __init__(self, message: str, status_code: int = None, payload: dict = None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload or {}

    def to_dict(self) -> dict:
        return {"error": self.message, **self.payload}


class ScraperError(AppError):
    status_code = 500


class NoContentError(AppError):
    status_code = 422


class ValidationError(AppError):
    status_code = 400


class DatabaseError(AppError):
    status_code = 500


class ArticleNotFoundError(AppError):
    status_code = 404