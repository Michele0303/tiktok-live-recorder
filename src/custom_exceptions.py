class AccountPrivate(Exception):
    def __init__(self, message='Account is private, login required. Please add your cookies to cookies.json'):
        super().__init__(message)


class LiveRestriction(Exception):
    def __init__(self, message='Live is private, login required. Please add your cookies to cookies.json'):
        super().__init__(message)


class CountryBlacklisted(Exception):
    pass


class UserNotFound(Exception):
    pass


class UserNotLiveException(Exception):
    def __init__(self, message):
        super().__init__(message)


class IPBlockedByWAF(Exception):
    def __init__(self, message="Your IP is blocked by TikTok WAF. Please change your IP address."):
        super().__init__(message)


class LiveNotFound(Exception):
    pass


class ArgsParseError(Exception):
    pass
