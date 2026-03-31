"""Custom exceptions for Veda error handling."""


class ImageTooLargeError(Exception):
    pass


class ImageDownloadError(Exception):
    pass


class GeminiTimeoutError(Exception):
    pass


class WhatsApp24hWindowError(Exception):
    pass


class RateLimitError(Exception):
    pass
