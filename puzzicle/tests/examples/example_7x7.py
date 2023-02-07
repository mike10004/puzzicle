#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random

import examples
from puzzicon.grid import GridModel

_WORDS_7x7 = """\
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
_NONWORDS_7x7 = """\
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
_DICTIONARY_7x7 = _WORDS_7x7 + _NONWORDS_7x7

def main():
    grid = GridModel.build("___.___" +
                           "___.___" +
                           "_______" +
                           "..___.." +
                           "_______" +
                           "___.___" +
                           "___.___")
    wordlist = list(_DICTIONARY_7x7)
    rng = random.Random(0xf177)
    return examples.do_main(grid, wordlist, rng, 400 * 1000)

if __name__ == '__main__':
    exit(main())
