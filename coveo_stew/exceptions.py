"""Exceptions thrown by the stew scripts."""


class PythonProjectException(Exception):
    ...


class CannotLoadProject(PythonProjectException):
    ...


class NotAPoetryProject(PythonProjectException):
    ...


class RequirementsOutdated(PythonProjectException):
    ...


class PythonProjectNotFound(PythonProjectException):
    ...


class ToolNotFound(PythonProjectException):
    ...


class MypyNotFound(PythonProjectException):
    ...


class CheckFailed(PythonProjectException):
    ...


class UsageError(PythonProjectException):
    ...
