#!/usr/bin/env python3


import puz

from unittest import TestCase

from puzzicle.puzio.reading import PuzzleReader
from puzzicle.tests import _Data


class ReadingTest(TestCase):

    def test_read_qxw(self):
        pathname = _Data().get_file("autofill-9x9.qxw")
        puzzle = PuzzleReader().read(pathname)
        self.assertIsInstance(puzzle, puz.Puzzle)
        self.assertEqual(9, puzzle.height)
        self.assertEqual(9, puzzle.width)
        chars = set(puzzle.solution)
        self.assertGreater(chars, {'.'})
