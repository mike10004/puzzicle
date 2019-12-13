#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
import sys
import time
import unittest
from typing import Tuple, NamedTuple, Iterator, Sequence, List
from unittest import TestCase, SkipTest
import puzzicon
from puzzicon.fill import Answer
from puzzicon.fill import FillState
from puzzicon.fill import Filler
from puzzicon.fill import Bank
from puzzicon.fill import FillStateNode
from puzzicon.fill import Suggestion
from puzzicon.fill import FillListener, FirstCompleteListener, AllCompleteListener
from puzzicon.grid import GridModel
from puzzicon.fill import WordTuple
from puzzicon.fill import BankItem
import logging
import tests
from tests import Render


_log = logging.getLogger(__name__)

tests.configure_logging()



def render_node(node: FillStateNode, grid: GridModel):
    print(node.state.render(grid))

def _show_path(node: FillStateNode, grid: GridModel):
    path = []
    while node is not None:
        path.append(node.state)
        node = node.parent
    path.reverse()
    for i, state in enumerate(path):
        print("Step {}:\n{}\n".format(i + 1, state.render(grid)))



_WORDS_2x2 = ['AB', 'BD', 'CD', 'AC']
_WORDS_3x3 = ['AB', 'CDE', 'FG', 'AC', 'BDF', 'EG']
_NONWORDS_3x3 = ['AD', 'ADG', 'EDC', 'BF']
_WORDS_5x5 = ['cod', 'khaki', 'noble', 'islam', 'tee', 'knit', 'hose', 'cable', 'okla', 'diem']
_NONWORDS_5x5 = _WORDS_2x2 + ['mob', 'wed', 'yalow', 'downy', 'flabber', 'patter', 'dyad', 'infect', 'fest', 'feast']

class FillResult(NamedTuple):
    node: FillStateNode
    value: object


def _NOOP(*args):
    pass


def make_tracer(grid: GridModel):
    def trace(node: FillStateNode):
        render_node(node, grid)
    return trace

# noinspection PyMethodMayBeStatic
class FillerTest(TestCase):

    def _do_fill_2x2(self, grid: GridModel, listener: FillListener) -> FillResult:
        wordlist = _WORDS_2x2 + ['XY', 'GH', 'IJ']
        print("using words:", wordlist)
        bank = tests.create_bank(*wordlist)
        return self._do_fill(grid, listener, bank)

    def _do_fill(self, grid: GridModel, listener: FillListener, bank: Bank) -> FillResult:
        assert listener is not None
        #filler = Filler(bank, make_tracer(grid))
        filler = Filler(bank)
        state = FillState.from_grid(grid)
        node = FillStateNode(state)
        filler._fill(node, listener)
        print("count = {} for {} with {}".format(listener.count, grid, bank))
        return FillResult(node, listener.value())

    def _check_2x2_filled(self, state: FillState):
        self._check_filled(state, _WORDS_2x2)

    def _check_filled(self, state: FillState, expected_words):
        self.assertIsInstance(state, FillState)
        self.assertTrue(state.is_complete())
        renderings = [a.render() for a in state.answers]
        self.assertSetEqual(set(expected_words), set(renderings))

    def _do_fill_3x3(self, grid: GridModel, listener: FillListener) -> FillResult:
        wordlist = _WORDS_3x3 + _NONWORDS_3x3
        bank = tests.create_bank(*wordlist)
        return self._do_fill(grid, listener, bank)

    def _check_3x3_filled(self, state: FillState):
        self._check_filled(state, _WORDS_3x3)

    def test_fill_2x2_first(self):
        grid = GridModel.build('____')
        listener = FirstCompleteListener(100000)
        filled = self._do_fill_2x2(grid, listener)
        self.assertIsInstance(filled.value, FillState)
        print(filled.value.render(grid))
        # noinspection PyTypeChecker
        self._check_2x2_filled(filled.value)

    def test_fill_2x2_all(self):
        grid = GridModel.build('____')
        fill_result = self._do_fill_2x2(grid, AllCompleteListener(100000))
        all_filled = fill_result.value
        self.assertIsInstance(all_filled, set)
        for i, state in enumerate(all_filled):
            self.assertIsInstance(state, FillState)
            words = list(Render.filled(state))
            if len(set(words)) != len(words):
                _show_path(fill_result.node, grid)
            print("solution {}:\n{}\n".format(i + 1, state.render(grid)))
            self._check_2x2_filled(state)
        self.assertEqual(2, len(all_filled), "expect two solutions")

    def test_fill_2x2_low_threshold(self):
        grid = GridModel.build('____')
        threshold = 3
        listener = FirstCompleteListener(threshold)
        fill_result = self._do_fill_2x2(grid, listener)
        result = fill_result.value
        self.assertIsNone(result)
        self.assertEqual(threshold, listener.count)

    @unittest.skip("until the smaller grids pass")
    def test_fill_3x3_first(self):
        grid = GridModel.build('__.___.__')
        fill_result = self._do_fill_3x3(grid, FirstCompleteListener(100000))
        filled = fill_result.value
        # noinspection PyTypeChecker
        self._check_3x3_filled(filled)

    @unittest.skip("until the smaller grids pass")
    def test_fill_5x5_first(self):
        grid = GridModel.build('.._____________________..')
        wordlist = list(_WORDS_5x5) + list(_NONWORDS_5x5)
        rng = random.Random(0xf177)
        rng.shuffle(wordlist)
        bank = tests.create_bank(*wordlist)
        fill_result = self._do_fill(grid, FirstCompleteListener(100000), bank)
        state = fill_result.value
        # noinspection PyTypeChecker
        self._check_filled(state, set(map(str.upper, _WORDS_5x5)))