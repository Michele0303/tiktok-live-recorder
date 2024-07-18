class AccountPrivate(Exception):
    pass


class CountryBlacklisted(Exception):
    pass


class UserNotFound(Exception):
    pass


class UserNotLiveException(Exception):
    def __init__(self, message):
        super().__init__(message)


class LiveNotFound(Exception):
    pass


class ArgsParseError(Exception):
    pass
