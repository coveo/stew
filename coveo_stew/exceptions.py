"""Exceptions thrown by the stew scripts."""


class StewException(Exception):
    ...


class CannotLoadProject(StewException):
    ...


class NotAPoetryProject(StewException):
    ...


class RequirementsOutdated(StewException):
    ...


class PythonProjectNotFound(StewException):
    ...


class LockNotFound(StewException):
    ...


class ToolNotFound(StewException):
    ...


class MypyNotFound(StewException):
    ...


class CheckFailed(StewException):
    ...


class CheckError(StewException):
    ...


class UsageError(StewException):
    ...
