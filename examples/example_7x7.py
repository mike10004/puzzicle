#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
import sys

from puzzicon.fill import Legend, FillState, Filler, Bank, FirstCompleteListener, AllCompleteListener, FillListener
from puzzicon.grid import GridModel
import time

_WORDS_9x9 = """\
ABC
BAG
DOI
ANA
SPRINTS
COD
LILNASX
ACE
IKE
YES
DIS
ADS
BOP
CIRCLES
BANDAID
ANT
GAS
ION
LAY
ICE
SKI
XES
""".split("\n")
_NONWORDS_9x9 = """\
FIT
EXTERMINATE
PAT
OBJECT
LYNN
CHESTERTON
FEATHER
PRO
SALES
AUGMENT
PIN
AND
MAROON
""".split("\n")
_DICTIONARY_9x9 = _WORDS_9x9 + _NONWORDS_9x9

def main():
    grid = GridModel.build("___.___" +
                           "___.___" +
                           "_______" +
                           "..___.." +
                           "_______" +
                           "___.___" +
                           "___.___")
    wordlist = list(_DICTIONARY_9x9)
    rng = random.Random(0xf177)
    rng.shuffle(wordlist)
    bank = Bank(list(map(str.upper, _DICTIONARY_9x9)))
    state = FillState.from_grid(grid)
    listener = FirstCompleteListener(1 * 1000 * 1000)
    filler = Filler(bank)
    fill_start = time.perf_counter()
    filler.fill(state, listener)
    fill_end = time.perf_counter()
    print("{} seconds to complete".format(fill_end - fill_start))
    state = listener.value()
    if state is not None:
        print(state.render(grid))
        return 0
    print("no solution found", file=sys.stderr)
    return 2

if __name__ == '__main__':
    exit(main())
