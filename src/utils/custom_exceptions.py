class TikTokRecorderError(Exception):
    """Base exception for all TikTok Recorder errors."""

    def __init__(self, message):
        super().__init__(message)


class UserLiveError(TikTokRecorderError):
    """Error related to user live status."""

    def __init__(self, message):
        super().__init__(message)


class IPBlockedByWAF(TikTokRecorderError):
    """Raised when IP is blocked by WAF."""

    def __init__(self, message="IP blocked by WAF"):
        super().__init__(message)


class LiveNotFound(TikTokRecorderError):
    """Raised when a live stream is not found."""

    pass


class ArgsParseError(TikTokRecorderError):
    """Raised for argument parsing errors."""

    pass


class NetworkError(TikTokRecorderError):
    """Raised for network-related errors."""

    pass
