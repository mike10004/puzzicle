#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

import examples
from examples.example_9x9 import _GRID_TEXT
# noinspection PyPep8Naming
from examples.example_9x9 import _WORDS_9x9 as _ANSWER_LIST
from puzzicon.fill.bank import BankLoader
from puzzicon.grid import GridModel
from argparse import ArgumentParser
import time
import logging


def main():
    grid = GridModel.build(_GRID_TEXT)
    p = ArgumentParser()
    p.add_argument("-t", "--threshold", type=int, default=10000)
    p.add_argument("--cache-dir")
    p.add_argument("-l", "--log-level", choices=('DEBUG', 'INFO', 'WARN', 'ERROR'), metavar="LEVEL", default='DEBUG')
    args = p.parse_args()
    logging.basicConfig(level=logging.__dict__[args.log_level])
    cache_dir = args.cache_dir or os.path.join(os.getcwd(), '.cache')
    def puzzeme_set_transform(puzzemes):
        strings = [z.canonical for z in puzzemes if (z.canonical.__hash__() % 10 == 0)] + _ANSWER_LIST
        return strings
    load_start = time.perf_counter()
    bank = BankLoader(cache_dir, 'subset10', 9, puzzeme_set_transform).load()
    load_end = time.perf_counter()
    print(bank.size(), "entries in bank; loaded in", (load_end - load_start), " seconds")
    return examples.do_main_with_bank(grid, bank, args.threshold)

if __name__ == '__main__':
    exit(main())
