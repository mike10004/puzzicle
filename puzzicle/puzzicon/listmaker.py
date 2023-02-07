#!/usr/bin/env python3

import sys
from typing import Optional, TextIO, Callable
from puzzicle.puzzicon import Puzzeme, InvalidPuzzemeException
import re


def make_cleaner(clean_expr: Optional[str], fullmatch=False) -> Optional[Callable[[str], str]]:
    if not clean_expr:
        return None
    regex = re.compile(clean_expr)
    def clean(line):
        m = regex.fullmatch(line) if fullmatch else regex.match(line)
        if m is None:
            return line
        return m.group(1)
    return clean


class ListMaker(object):

    def __init__(self, clean: Callable[[str], str], preserve_spaces: bool=False, error_mode='drop', preserve_case: bool=False):
        self.clean = clean or str.strip
        self.preserve_spaces = preserve_spaces
        self.error_mode = error_mode
        assert error_mode in ('keep', 'drop', 'halt')
        self.allowed = 'alphanumeric'
        self.preserve_case = preserve_case

    def transliterate(self, line: str, ofile: Optional[TextIO]=None) -> Optional[str]:
        line = self.clean(line)
        cs = None
        create_kwargs = {
            'allowed': self.allowed,
            'preserve': {'case'} if self.preserve_case else frozenset()
        }
        try:
            if self.preserve_spaces:
                cs = [Puzzeme.canonicalize(part, **create_kwargs) for part in line.split()]
            else:
                cs = [Puzzeme.canonicalize(line, **create_kwargs)]
        except InvalidPuzzemeException:
            if self.error_mode == 'halt':
                raise
            elif self.error_mode == 'keep':
                print(line, file=ofile)
                return line
            elif self.error_mode == 'drop':
                return None
        assert cs
        outcome = ' '.join(cs)
        if ofile is not None:
            print(outcome, file=ofile)
        return outcome


def main():
    from argparse import ArgumentParser
    p = ArgumentParser()
    p.add_argument("--clean", metavar="REGEX", help="regex where first group is desired string fragment")
    p.add_argument("--preserve", metavar="X[,X...]", default='', help="things to preserve; valid elements are 'case', 'spaces'")
    args = p.parse_args()
    clean = make_cleaner(args.clean)
    preserve = set(filter(lambda x: x, args.preserve.split(',')))
    listmaker = ListMaker(clean, preserve_spaces='spaces' in preserve, preserve_case='case' in preserve)
    ifile, ofile = sys.stdin, sys.stdout
    for line in ifile:
        outcome = listmaker.transliterate(line)
        print(outcome, file=ofile)
    return 0
