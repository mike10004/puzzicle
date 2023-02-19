#!/usr/bin/env python3

import puz
from puzzicle.puzio.qxw import QxwParser

class PuzzleReader(object):

    # noinspection PyMethodMayBeStatic
    def read(self, pathname: str) -> puz.Puzzle:
        if pathname.lower().endswith('.qxw'):
            with open(pathname, 'r') as ifile:
                qxw_model = QxwParser().parse(ifile)
            puzzle = puz.Puzzle()
            puzzle.preamble = b''
            puzzle.solution = qxw_model.to_puz_solution()
            puzzle.scrambled_cksum = 0
            puzzle.width = qxw_model.width
            puzzle.height = qxw_model.height
        else:
            puzzle = puz.read(pathname)
        return puzzle
