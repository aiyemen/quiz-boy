"""
Exceptions for Quiz Results and Ranking.
"""


class ResultError(Exception):
    pass


class ResultNotFoundError(ResultError):
    pass


class ResultOwnershipError(ResultError):
    pass


class IncompleteSessionError(ResultError):
    pass


class DuplicateResultError(ResultError):
    pass
