from functools import wraps
from sys import exc_info
from traceback import format_exc

from common.log import logUtils as log


def trackExceptions(moduleName=""):
    def _trackExceptions(func):
        def _decorator(request, *args, **kwargs):
            try:
                response = func(request, *args, **kwargs)
                return response
            except:
                log.error("Unknown error{}!\n```\n{}\n{}```".format(" in "+moduleName if moduleName != "" else "", exc_info(), format_exc()), True)
        return wraps(func)(_decorator)
    return _trackExceptions
