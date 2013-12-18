import argparse
from functools import wraps


def argument(*args, **kwargs):
    return lambda parser: parser.add_argument(*args, **kwargs)


class Command(object):

    def __init__(self, *args, **kwargs):
        self._parser = argparse.ArgumentParser(*args, **kwargs)
        self._subparsers = self._parser.add_subparsers(dest="COMMAND")
        self._commands = {}


    def print_help(self):
        self._parser.print_help()


    def run(self):
        args = self._parser.parse_args()
        return self._commands[args.COMMAND](args)


    def __call__(self, *arguments):
        def decorator(func):
            name = func.__name__.replace("_", "-")

            subparser = self._subparsers.add_parser(name, help = func.__doc__)
            dests = [arg(subparser).dest for arg in arguments]

            @wraps(func)
            def wrapper(args):
                return func(**{d:getattr(args, d) for d in dests if getattr(args, d) is not None})

            self._commands[name] = wrapper
            return wrapper

        return decorator
