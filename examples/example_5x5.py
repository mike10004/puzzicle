#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
from unittest import TestCase
import puzzicon
from puzzicon.fill import Legend, FillState, Filler, Bank, FirstCompleteListener, AllCompleteListener, FillListener
from puzzicon.grid import GridModel

_WORDS_5x5 = ['cod', 'khaki', 'noble', 'islam', 'tee', 'knit', 'hose', 'cable', 'okla', 'diem']
_NONWORDS_5x5 = ['mob', 'wed', 'yalow', 'downy', 'flabber', 'patter', 'dyad', 'infect', 'fest', 'feast']
_DICTIONARY_5x5 = _WORDS_5x5 + _NONWORDS_5x5

def main():
    grid = GridModel.build('.._____________________..')
    wordlist = list(_WORDS_5x5) + list(_NONWORDS_5x5)
    rng = random.Random(0xf177)
    rng.shuffle(wordlist)
    bank = Bank(list(map(str.upper, _DICTIONARY_5x5)))
    state = FillState.from_grid(grid)
    listener = FirstCompleteListener()
    filler = Filler(bank)
    filler.fill(state, listener)
    state = listener.value()
    assert state is not None
    print(state.render(grid))
    return 0

if __name__ == '__main__':
    exit(main())
