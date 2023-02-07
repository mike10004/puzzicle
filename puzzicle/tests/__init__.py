import sys
from collections import defaultdict
import logging
import os
import os.path
import errno
from typing import List, Dict, DefaultDict, Iterator
from puzzicle import puzzicon
import puzzicle.puzzicon.fill
import puzzicle.puzzicon.fill.state
import puzzicle.puzzicon.fill.bank

_ENV_LOG_LEVEL = 'UNIT_TESTS_LOG_LEVEL'
_TESTS_ENV_FILE_FILENAME = 'tests.env'
_MERGED_ENV = None
_LOGGING_CONFIGURED = False


def get_env_files():
    dirs = [os.getcwd()]
    parent = os.path.dirname(os.getcwd())
    if parent:
        dirs.append(parent)
    return list(map(lambda dirname: os.path.join(dirname, _TESTS_ENV_FILE_FILENAME), dirs))


def parse_env_file(pathnames: List[str]) -> Dict[str, str]:
    env = {}
    for pathname in pathnames:
        try:
            with open(pathname, 'r') as ifile:
                for lineno, line in enumerate(ifile):
                    line = line[:-1]
                    try:
                        name, value = line.split('=', 1)
                    except Exception as e:
                        print(f"tests: invalid line {lineno} in {pathname}: {e}", file=sys.stderr)
                        continue
                    env[name] = value
        except IOError as e:
            if e.errno != errno.ENOENT:
                print(f"tests: error reading {pathname}: {e}")
    return env


def get_merged_env() -> DefaultDict[str, str]:
    global _MERGED_ENV
    if _MERGED_ENV is None:
        file_env = parse_env_file(get_env_files())
        process_env = dict(os.environ)
        merged_env = defaultdict(lambda: None)
        merged_env.update(file_env)
        merged_env.update(process_env)
        _MERGED_ENV = merged_env
    return _MERGED_ENV


def configure_logging():
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return
    env = get_merged_env()
    level_str = env[_ENV_LOG_LEVEL] or 'INFO'
    try:
        level = logging.__dict__[level_str]
    except KeyError:
        print(f"tests: illegal log level {level_str}", file=sys.stderr)
        level = logging.INFO
    logging.basicConfig(level=level)
    _LOGGING_CONFIGURED = True


configure_logging()


class _Data(object):

    def __init__(self, directory=None):
        if directory is None:
            this_file = os.path.abspath(__file__)
            parent = os.path.dirname(this_file)
            self.directory = os.path.join(parent, 'testdata')
        else:
            self.directory = directory

    def get_file(self, relative_path: str) -> str:
        pathname = os.path.join(self.directory, relative_path)
        if not os.path.exists(pathname):
            raise ValueError("testdata file not found: " + relative_path + " at " + pathname)
        return pathname


    def open_file(self, relative_path: str, mode: str='rb'):
        return open(self.get_file(relative_path), mode)


    def load_file(self, relative_path, mode='rb'):
        with self.open_file(relative_path, mode) as ifile:
            return ifile.read()


data = _Data()


def is_long_tests_enabled():
    return True


_BANK_DEBUG = False


def create_bank(*args):
    puzzemes = puzzicle.puzzicon.create_puzzeme_set(args)
    return puzzicle.puzzicon.fill.bank.Bank.with_registry([p.canonical for p in puzzemes], debug=_BANK_DEBUG)


def create_bank_from_wordlist_file(pathname: str='/usr/share/dict/words'):
    puzzemes = puzzicle.puzzicon.read_puzzeme_set(pathname)
    return puzzicle.puzzicon.fill.bank.Bank.with_registry([p.canonical for p in puzzemes], debug=_BANK_DEBUG)


class Render(object):

    @staticmethod
    def filled(state: puzzicle.puzzicon.fill.state.FillState) -> Iterator[str]:
        return filter(lambda x: x is not None, state.used)


