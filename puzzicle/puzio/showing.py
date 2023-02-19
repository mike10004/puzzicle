#!/usr/bin/env python3

import sys
import logging
from collections import defaultdict
from argparse import ArgumentParser
from typing import Sequence, TextIO
import puz

from puzzicle.puzio.reading import PuzzleReader

_log = logging.getLogger(__name__)
GRID = "grid"
STATS = "stats"
METADATA = "metadata"

def render_text(puzzle: puz.Puzzle, ofile: TextIO):
    nrows, ncols = puzzle.width, puzzle.height
    for r in range(nrows):
        for c in range(ncols):
            val = puzzle.solution[r * ncols + c]
            print(val, end="", file=ofile)
        print(file=ofile)


def main(argl: Sequence[str]=None, stdout: TextIO=sys.stdout):
    parser = ArgumentParser()
    parser.add_argument("input", help=".puz input file")
    parser.add_argument("-s", "--show", action='append', choices=(METADATA, STATS, GRID))
    args = parser.parse_args(argl)
    show = args.show or (METADATA, STATS)
    puzzle = PuzzleReader().read(args.input)
    if METADATA in show:
        for attrib in ('title', 'author', 'copyright', 'notes'):
            value = puzzle.__dict__.get(attrib, '')
            print(f"{attrib}: {value}", file=stdout)
    if STATS in show:
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
        pct = "" if not puzzle.fill else f"({100 * darks / len(puzzle.fill):.1f}%)"
        print(f"{darks} darks {pct}", file=stdout)
    if GRID in show:
        render_text(puzzle, ofile=stdout)
    return 0
