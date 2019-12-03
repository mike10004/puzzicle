#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
from puzzicon.fill import Legend, FillState, Filler, Bank, FirstCompleteListener, AllCompleteListener, FillListener
from puzzicon.grid import GridModel
import time

_WORDS_5x5 = ['cod', 'khaki', 'noble', 'islam', 'tee', 'knit', 'hose', 'cable', 'okla', 'diem']
_NONWORDS_5x5 = ['mob', 'wed', 'yalow', 'downy', 'flabber', 'patter', 'dyad', 'infect', 'fest', 'feast']
_DICTIONARY_5x5 = _WORDS_5x5 + _NONWORDS_5x5

def main():
    grid = GridModel.build('.._____________________..')
    wordlist = list(_WORDS_5x5) + list(_NONWORDS_5x5)
    rng = random.Random(0xf177)
    rng.shuffle(wordlist)
    bank = Bank.with_registry(list(map(str.upper, _DICTIONARY_5x5)))
    state = FillState.from_grid(grid)
    listener = FirstCompleteListener()
    filler = Filler(bank)
    fill_start = time.perf_counter()
    filler.fill(state, listener)
    fill_end = time.perf_counter()
    state = listener.value()
    assert state is not None
    print("{} seconds to complete".format(fill_end - fill_start))
    print(state.render(grid))
    return 0

if __name__ == '__main__':
    exit(main())
