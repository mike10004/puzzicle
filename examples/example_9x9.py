#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random

import examples
from puzzicon.grid import GridModel

_GRID_TEXT =  (".___.___." +
               "_________" +
               "_________" +
               "___._____" +
               ".___.___." +
               "_____.___" +
               "_________" +
               "_________" +
               ".___.___.")

_WORDS_9x9 = list(map(str.upper, ["act",
"are",
"snootiest",
"inamorata",
"tog",
"denim",
"tub",
"dim",
"baled",
"Mae",
"stalemate",
"detonator",
"sew",
"oer",
"annotates",
"coagulate",
"tom",
"aired",
"reanimate",
"estimator",
"sit",
"Tod",
"tam",
"below",
"BSD",
"den",
"eer",
"Mao"]))


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
    grid = GridModel.build(".___.___." +
                           "_________" +
                           "_________" +
                           "___._____" +
                           ".___.___." +
                           "_____.___" +
                           "_________" +
                           "_________" +
                           ".___.___.")
    wordlist = list(_DICTIONARY_9x9)
    rng = random.Random(0xf177)
    return examples.do_main(grid, wordlist, rng, 400 * 1000)

if __name__ == '__main__':
    exit(main())
