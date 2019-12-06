#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
import sys
import time
from typing import Tuple, NamedTuple, Iterator, Sequence, List
from unittest import TestCase, SkipTest
import puzzicon
from puzzicon.fill import Answer, FillState, Filler, Bank, FillStateNode, Suggestion
from puzzicon.fill import FillListener, FirstCompleteListener, AllCompleteListener
from puzzicon.grid import GridModel
import logging
import tests

_log = logging.getLogger(__name__)

tests.configure_logging()


# noinspection PyPep8Naming
def A(*args) -> Answer:
    """Create a template with the argument indices"""
    return Answer.define(args)

T = A


def map_all(templates: Sequence[int], legend: Sequence[str]) -> List[Answer]:
    def get_or_default(idx: int):
        try:
            return legend[idx]
        except IndexError:
            return idx
    return [Answer.define(list(map(get_or_default, template))) for template in templates]


def create_bank(*args):
    puzzemes = puzzicon.create_puzzeme_set(args)
    return Bank.with_registry([p.canonical for p in puzzemes])


def create_bank_from_wordlist_file(pathname: str='/usr/share/dict/words'):
    puzzemes = puzzicon.read_puzzeme_set(pathname)
    return Bank.with_registry([p.canonical for p in puzzemes])


class Answer(TestCase):

    def test_create(self):
        t = Answer.define([0, 1, 2])
        self.assertIsInstance(t, tuple)
        self.assertTupleEqual((0, 1, 2), t.content)
        self.assertTupleEqual((None, None, None), t.pattern)
        self.assertEqual(0, t.strength)

    def test_create2(self):
        t = Answer.define([0, 'b', 2])
        self.assertTupleEqual((0, 'b', 2), t.content)
        self.assertTupleEqual((None, 'b', None), t.pattern)
        self.assertEqual(1, t.strength)

    def test_create_shortcut(self):
        t = T(0, 1, 2)
        self.assertIsInstance(t, Answer)
        self.assertEqual(0, t.strength)

class ModuleTest(TestCase):

    def test__sort_and_check_duplicates_presorted_hasdupes_words(self):
        a = ['ac', 'cd', 'ac', 'cd']
        b = a.copy()
        self.assertTrue(puzzicon.fill._sort_and_check_duplicates(a))
        self.assertListEqual(a, sorted(b))

    def test__sort_and_check_duplicates_presorted_nodupes(self):
        a = [1, 2, 3]
        self.assertFalse(puzzicon.fill._sort_and_check_duplicates(a))
        self.assertListEqual(a, sorted(a))

    def test__sort_and_check_duplicates_presorted_dupes(self):
        for b in [[1, 1, 2, 3], [1, 2, 2, 3], [1, 2, 3, 3]]:
            a = b.copy()
            self.assertTrue(puzzicon.fill._sort_and_check_duplicates(a))
            self.assertListEqual(a, sorted(b))

    def test__sort_and_check_duplicates_notsorted_dupes(self):
        for b in [[1, 1, 3, 2], [3, 2, 1, 2], [2, 1, 3, 3], [3, 1, 2, 3]]:
            a = b.copy()
            self.assertTrue(puzzicon.fill._sort_and_check_duplicates(a))
            self.assertListEqual(a, sorted(b))

    def test__sort_and_check_duplicates_notsorted_nodupes(self):
        for b in [[1, 3, 2], [3, 1, 2], [2, 1, 3]]:
            a = b.copy()
            self.assertFalse(puzzicon.fill._sort_and_check_duplicates(a))
            self.assertListEqual(a, sorted(b))


class Render(object):

    @staticmethod
    def filled(state: FillState) -> Iterator[str]:
        return filter(lambda x: x is not None, state.used)




class FillStateTest(TestCase):

    def test_advance_basic(self):
        grid = GridModel.build("____")
        state1 = FillState.from_grid(grid)
        state2 = state1.advance_unchecked(Suggestion({0: 'a', 1: 'b'}, {0: 'ab'}))
        self.assertIs(state1.crosses, state2.crosses)
        self.assertNotEqual(state1, state2)
        self.assertSetEqual({'ab'}, set(Render.filled(state2)))

    def test_advance_additional_entries_added(self):
        # noinspection PyTypeChecker
        state2 = FillState.from_answers((A('a','b'),A(2,3),A('a',2),A('b',3)))
        sugg = Suggestion({2: 'c', 3: 'd'}, {1: 'cd', 2: 'ac', 3: 'bd'})
        state3 = state2.advance_unchecked(sugg)
        self.assertSetEqual({'ab', 'cd', 'ac', 'bd'}, set(Render.filled(state3)))

    def test_advance_additional_entries_added_incorrect(self):
        # noinspection PyTypeChecker
        state2 = FillState.from_answers((A('a', 'c'),A(2,3),A('a',2),A('c',3)))
        sugg = Suggestion({2: 'c', 3: 'd'}, {1: 'cd', 2: 'ac', 3: 'cd'})
        state3 = state2.advance_unchecked(sugg)
        self.assertSetEqual({'ac', 'cd'}, set(Render.filled(state3)))

    # noinspection PyTypeChecker
    def test_is_complete(self):
        templates = (
            (0, 1, 2),
            (1, 2),
            (3, 0, 1),
            (5, 2),
            (4, 4, 4, 0, 4, 2),
        )
        state = FillState.from_answers(map_all(templates, ['a', 'b', 'c', 'd', 'e', 'f']))
        self.assertTrue(state.is_complete())
        templates = (
            (0, 1, 2),
            (1, 2),
            (12, 4, 1),  # 12 is not satisfed
            (5, 2),
            (4, 4, 4, 0, 4, 2),
        )
        state = FillState.from_answers(map_all(templates, ['a', 'b', 'c', 'd', 'e', 'f']))
        self.assertFalse(state.is_complete())

    # noinspection PyTypeChecker
    def test_unfilled(self):
        templates = (
            (0, 1, 2),
            (2, 0, 2),
            (12, 4, 1),  # 12 is not satisfed
            (5, 2),
            (4, 9, 4, 0, 4, 2),
        )
        answers = map_all(templates, ['a', 'b', 'c', 'd', 'e', 'f'])
        state = FillState.from_answers(answers)
        unfilled = list(state.unfilled())
        self.assertListEqual([2, 4], unfilled)

    def test_to_legend_updates(self):
        state = FillState.from_answers((T('G', 'H'), T('G', 2), T('H', 3), T(2, 3)))
        actual = state.to_legend_updates_dict('GX', 1)
        self.assertDictEqual({2: 'X'}, actual)

    def test_list_new_entries_using_updates(self):
        templates: Tuple[Answer, ...] = (T(0,1), T(2,3), T(0,2), T(1,3))
        state = FillState.from_answers(templates)
        actual = state.list_new_entries_using_updates({2:'C',3:'D'}, 1, False)
        self.assertDictEqual({2: 'AC', 3: 'BD'}, actual)


class BankTest(TestCase):

    def test_matches(self):
        good = [
            ('ABC', ['A', None, 'C']),
            ('ABC', [None, None, None]),
            ('ABC', ['A', 'B', 'C']),
            ('ABC', [None, None, 'C']),
            ('ABC', [None, 'B', 'C']),
            ('ABC', [None, 'B', None]),
        ]
        for entry, pattern in good:
            with self.subTest():
                self.assertTrue(Bank.matches(entry, pattern))

    def test_matches_false(self):
        bad = [
            ('ABC', ['X', None, 'C']),
            ('ABC', [None, 'C', None]),
            ('ABC', ['X', 'B', 'C']),
            ('ABC', ['A', 'B']),
        ]
        for entry, pattern in bad:
            with self.subTest():
                self.assertFalse(Bank.matches(entry, pattern))

    def test_suggest_1(self):
        words = ['AB', 'CD', 'AC', 'BD', 'XY', 'JJ', 'OP']
        bank = create_bank(*words)
        templates: Tuple[Answer, ...] = (T(0,1), T(2,3), T(0,2), T(1,3))
        state = FillState.from_templates(templates)
        actual = set(bank.suggest_updates(state, 0).new_entries)
        self.assertSetEqual(set(words), actual)

    def test_suggest_3(self):
        bank = create_bank('AB', 'CD', 'AC', 'BD', 'XY', 'JJ', 'OP', 'BX', 'AX')
        templates: Tuple[Answer, ...] = (T('A', 'B'), T(2,3), T('A',2), T('B',3))
        state = FillState.from_answers(templates)
        actual = set(bank.suggest_updates(state, 2).new_entries)
        self.assertSetEqual({'AC', 'AX'}, actual)

    def test_suggest_2(self):
        words_2chars = ['AB', 'CD', 'AC', 'BD', 'XY', 'JJ', 'OP']
        words_3chars = ['TAB', 'QCD', 'YAC', 'CBD', 'JXY', 'TJJ', 'NOP']
        all_words = words_2chars + words_3chars
        bank = create_bank(*all_words)
        templates = (T(0,1), T(2,3), T(0,2), T(1,3))
        state = FillState.from_templates(templates)
        actual = set(bank.suggest_updates(state, 0).new_entries)
        self.assertSetEqual(set(words_2chars), actual)

    def test_filter(self):
        bank = create_bank('ABC', 'DEF', 'ABX', 'G', 'HI', 'ACC')
        actual = set(bank.filter(['A', 'B', None]))
        self.assertSetEqual({'ABC', 'ABX'}, actual)

    def test_big_bank(self):
        if not tests.is_long_tests_enabled():
            raise SkipTest("long tests are not enabled")
        start = time.perf_counter()
        bank = create_bank_from_wordlist_file()
        end = time.perf_counter()
        print("sizeof(/usr/share/dict/words) =", sys.getsizeof(bank))
        print("created in {} seconds".format(end - start))
        matches = list(bank.filter(['A', None, None, 'L', 'E']))
        self.assertIn('APPLE', matches)
        self.assertIn('ADDLE', matches)


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

# noinspection PyMethodMayBeStatic
class FillerTest(TestCase):

    def _do_fill_2x2(self, grid: GridModel, listener: FillListener) -> FillResult:
        wordlist = _WORDS_2x2 + ['XY', 'GH', 'IJ']
        bank = create_bank(*wordlist)
        return self._do_fill(grid, listener, bank)

    def _do_fill(self, grid: GridModel, listener: FillListener, bank: Bank) -> FillResult:
        assert listener is not None
        filler = Filler(bank)
        state = FillState.from_grid(grid)
        node = FillStateNode(state)
        filler._fill(node, listener)
        print("count = {} for {} with {}".format(listener.count, grid, bank))
        return FillResult(node, listener.value())

    def test_fill_2x2_first(self):
        grid = GridModel.build('____')
        listener = FirstCompleteListener(100000)
        filled = self._do_fill_2x2(grid, listener)
        # noinspection PyTypeChecker
        self._check_2x2_filled(filled.value)

    def _check_2x2_filled(self, state: FillState):
        self._check_filled(state, _WORDS_2x2)

    def _check_filled(self, state: FillState, expected_words):
        self.assertIsInstance(state, FillState)
        self.assertTrue(state.is_complete())
        renderings = [a.render() for a in state.answers]
        self.assertSetEqual(set(expected_words), set(renderings))

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

    def _do_fill_3x3(self, grid: GridModel, listener: FillListener) -> FillResult:
        wordlist = _WORDS_3x3 + _NONWORDS_3x3
        bank = create_bank(*wordlist)
        return self._do_fill(grid, listener, bank)

    def _check_3x3_filled(self, state: FillState):
        self._check_filled(state, _WORDS_3x3)

    def test_fill_2x2_low_threshold(self):
        grid = GridModel.build('____')
        threshold = 3
        listener = FirstCompleteListener(threshold)
        fill_result = self._do_fill_2x2(grid, listener)
        result = fill_result.value
        self.assertIsNone(result)
        self.assertEqual(threshold, listener.count)

    def test_fill_3x3_first(self):
        grid = GridModel.build('__.___.__')
        fill_result = self._do_fill_3x3(grid, FirstCompleteListener(100000))
        filled = fill_result.value
        # noinspection PyTypeChecker
        self._check_3x3_filled(filled)

    def test_fill_5x5_first(self):
        grid = GridModel.build('.._____________________..')
        wordlist = list(_WORDS_5x5) + list(_NONWORDS_5x5)
        rng = random.Random(0xf177)
        rng.shuffle(wordlist)
        bank = create_bank(*wordlist)
        fill_result = self._do_fill(grid, FirstCompleteListener(100000), bank)
        state = fill_result.value
        # noinspection PyTypeChecker
        self._check_filled(state, set(map(str.upper, _WORDS_5x5)))