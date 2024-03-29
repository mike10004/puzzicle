#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

import examples
from examples.example_9x9 import _GRID_TEXT
# noinspection PyPep8Naming
from examples.example_9x9 import _WORDS_9x9 as _ANSWER_LIST
from puzzicon.fill import Answer
from puzzicon.fill.bank import BankLoader
from puzzicon.fill.filler import FirstCompleteListener
from puzzicon.grid import GridModel
from argparse import ArgumentParser
import time
import logging
import random


def main():
    grid = GridModel.build(_GRID_TEXT)
    p = ArgumentParser()
    p.add_argument("-t", "--max-nodes", type=int, default=None)
    p.add_argument("--cache-dir")
    p.add_argument("-l", "--log-level", choices=('DEBUG', 'INFO', 'WARN', 'ERROR'), metavar="LEVEL", default='DEBUG')
    p.add_argument("--bank-size", type=int)
    p.add_argument("--random-seed", type=int)
    p.add_argument("--max-time", type=float, default=None)
    args = p.parse_args()
    logging.basicConfig(level=logging.__dict__[args.log_level])
    if args.max_time is None and args.max_nodes is None:
        args.max_time = 60.0
    cache_dir = args.cache_dir or os.path.join(os.getcwd(), '.cache')
    def puzzeme_set_transform(puzzemes):
        canonicals = [z.canonical for z in puzzemes]
        if args.bank_size is not None:
            puzzeme_limit = args.bank_size - len(_ANSWER_LIST)
            random.Random(args.random_seed).shuffle(canonicals)
            canonicals = canonicals[:puzzeme_limit]
        strings = canonicals + _ANSWER_LIST
        return strings
    load_start = time.perf_counter()
    bank = BankLoader(cache_dir, "subset{}".format(args.bank_size or ''), 9, puzzeme_set_transform).load()
    load_end = time.perf_counter()
    print("{} entries in bank; loaded in {:.1f} seconds".format(bank.size(), load_end - load_start))
    fill_listener = FirstCompleteListener(args.max_nodes, args.max_time)
    return examples.do_main_with_bank(grid, bank, fill_listener)

if __name__ == '__main__':
    exit(main())
