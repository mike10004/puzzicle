#!/usr/bin/env python3

import puz
from puzzicle.puzio.qxw import QxwParser

class PuzzleReader(object):

    # noinspection PyMethodMayBeStatic
    def read(self, pathname: str) -> puz.Puzzle:
        if pathname.lower().endswith('.qxw'):
            with open(pathname, 'r') as ifile:
                qxw_model = QxwParser().parse(ifile)
            puzzle = qxw_model.to_puz()
        else:
            puzzle = puz.read(pathname)
        return puzzle
