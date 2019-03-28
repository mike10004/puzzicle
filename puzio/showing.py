#!/usr/bin/env python3

from __future__ import print_function
from collections import defaultdict
from argparse import ArgumentParser
from typing import Sequence, TextIO
import puz
import sys
import logging


_log = logging.getLogger(__name__)


def main(argl: Sequence[str]=None, stdout: TextIO=sys.stdout):
    parser = ArgumentParser()
    parser.add_argument("input", help=".puz input file")
    args = parser.parse_args(argl)
    puzzle = puz.read(args.input)
    for attrib in ('title', 'author', 'copyright', 'notes'):
        value = puzzle.__dict__.get(attrib, '')
        print(f"{attrib}: {value}", file=stdout)
    cn = puzzle.clue_numbering()
    all_clues = cn.across + cn.down
    histo = defaultdict(int)
    for clue in all_clues:
        histo[clue['len']] += 1
    for length in sorted(histo.keys()):
        freq = histo[length]
        print("%2d: %d" % (length, freq), file=stdout)
    print("{} clues total".format(len(all_clues)), file=stdout)
    darks = sum([1 if ch == '.' else 0 for ch in puzzle.fill])
    print("%d darks (%.1f%%)" % (darks, 100 * darks / len(puzzle.fill)), file=stdout)
    return 0
