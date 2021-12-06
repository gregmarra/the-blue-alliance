from typing import Any

class Error(Exception): ...
class DownloadError(Error): ...
class MalformedReplyError(DownloadError): ...
class TooManyRedirectsError(DownloadError): ...
class InternalTransientError(Error): ...
class ConnectionClosedError(DownloadError): ...
class InvalidURLError(Error): ...
class PayloadTooLargeError(InvalidURLError): ...
class DNSLookupFailedError(DownloadError): ...
class DeadlineExceededError(DownloadError): ...

class ResponseTooLargeError(Error):
    response: Any
    def __init__(self, response) -> None: ...

class InvalidMethodError(Error): ...
class SSLCertificateError(Error): ...