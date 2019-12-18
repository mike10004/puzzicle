#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random

import examples
from puzzicon.grid import GridModel

_WORDS_5x5 = ['cod', 'khaki', 'noble', 'islam', 'tee', 'knit', 'hose', 'cable', 'okla', 'diem']
_NONWORDS_5x5 = ['mob', 'wed', 'yalow', 'downy', 'flabber', 'patter', 'dyad', 'infect', 'fest', 'feast']
_DICTIONARY_5x5 = _WORDS_5x5 + _NONWORDS_5x5


def main():
    grid = GridModel.build('.._____________________..')
    wordlist = list(_WORDS_5x5) + list(_NONWORDS_5x5)
    rng = random.Random(0xf177)
    return examples.do_main(grid, wordlist, rng, 200 * 1000)

if __name__ == '__main__':
    exit(main())
