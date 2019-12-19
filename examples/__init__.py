#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
import sys
from typing import List

from puzzicon.fill.state import FillState
from puzzicon.fill.filler import Filler, FillListener, FirstCompleteListener
from puzzicon.fill.bank import Bank
from puzzicon.grid import GridModel
import time


def do_main_with_bank(grid: GridModel, bank: Bank, listener: FillListener):
    state = FillState.from_grid(grid)
    filler = Filler(bank)
    fill_start = time.perf_counter()
    filler.fill(state, listener)
    fill_end = time.perf_counter()
    print("{:.1f} seconds to complete".format(fill_end - fill_start))
    state = listener.value()
    print("{} nodes examined in {:.1f} seconds".format(listener.count, time.perf_counter() - listener.start))
    if state is not None:
        print(state.render(grid))
        return 0
    print("no solution found", file=sys.stderr)
    return 2


def do_main(grid: GridModel, wordlist: List[str], rng: random.Random, threshold: int):
    rng.shuffle(wordlist)
    bank = Bank.with_registry(list(map(str.upper, wordlist)))
    print("bank created with", bank.size(), "deposits")
    return do_main_with_bank(grid, bank, FirstCompleteListener(node_threshold=threshold))