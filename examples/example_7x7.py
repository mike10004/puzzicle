#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random

import examples
from puzzicon.grid import GridModel

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
    return examples.do_main(grid, wordlist, rng, 400 * 1000)

if __name__ == '__main__':
    exit(main())
