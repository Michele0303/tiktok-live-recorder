from utils.enums import TikTokError


class TikTokException(Exception):
    def __init__(self, message):
        super().__init__(message)


class AccountPrivate(Exception):
    def __init__(self, message=TikTokError.ACCOUNT_PRIVATE):
        super().__init__(message)


class LiveRestriction(Exception):
    def __init__(self, message=TikTokError.LIVE_RESTRICTION):
        super().__init__(message)


class CountryBlacklisted(Exception):
    pass


class UserLiveException(Exception):
    def __init__(self, message):
        super().__init__(message)


class IPBlockedByWAF(Exception):
    def __init__(self, message=TikTokError.WAF_BLOCKED):
        super().__init__(message)


class LiveNotFound(Exception):
    pass


class ArgsParseError(Exception):
    pass
