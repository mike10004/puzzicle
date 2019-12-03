#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
import sys
import time
from typing import Tuple, Optional, NamedTuple
from unittest import TestCase, SkipTest
import puzzicon
from puzzicon.fill import Legend, FillState, Filler, Bank, FirstCompleteListener, AllCompleteListener, FillListener, FillStateNode, Template
from puzzicon.grid import GridModel
import logging
import tests

_log = logging.getLogger(__name__)

tests.configure_logging()

def T(*args):
    """Create a template with the argument indices"""
    return Template(args)

def create_bank(*args):
    puzzemes = puzzicon.create_puzzeme_set(args)
    return Bank.with_registry([p.canonical for p in puzzemes])


def create_bank_from_wordlist_file(pathname: str='/usr/share/dict/words'):
    puzzemes = puzzicon.read_puzzeme_set(pathname)
    return Bank.with_registry([p.canonical for p in puzzemes])


class TemplateTest(TestCase):

    def test_create(self):
        t = Template([0, 1, 2])
        self.assertIsInstance(t, tuple)
        for val in t:
            self.assertIsInstance(val, int)

    def test_create_shortcut(self):
        t = T(0, 1, 2)
        self.assertIsInstance(t, tuple)
        self.assertEqual(3, len(t))
        for val in t:
            self.assertIsInstance(val, int)

class LegendTest(TestCase):

    def test_has_value(self):
        d = Legend(['a', None, 'c'])
        self.assertTrue(d.has_value(0))
        self.assertFalse(d.has_value(10))
        self.assertFalse(d.has_value(1))
        self.assertFalse(d.has_value(3))
        self.assertTrue(d.has_value(2))

    def test_equals_tuple(self):
        d = Legend(['a', None, 'c'])
        self.assertTupleEqual(('a', None, 'c'), d)

    def test_get(self):
        d = Legend(['a', None, 'c'])
        self.assertEqual('a', d.get(0))
        self.assertEqual('c', d.get(2))
        self.assertIsNone(d.get(1))
        self.assertIsNone(d.get(10))
        self.assertIsNone(d.get(3))

    def test_render(self):
        d = Legend(['a', None, 'b', None, 'c', None])
        self.assertEqual('abc', d.render([0, 2, 4]))
        self.assertEqual('a_c', d.render([0, 1, 4]))
        self.assertEqual('___', d.render([3, 1, 10]))

    def test_redefine_1(self):
        d = Legend(['a', None, 'c'])
        f = d.redefine({1: 'b'})
        self.assertEqual(('a', 'b', 'c'), f)

    def test_redefine_2(self):
        d = Legend(['a', None, 'c'])
        f = d.redefine({5: 'b'})
        self.assertEqual(('a', None, 'c', None, None, 'b'), f)

    def test_render_after(self):
        d = Legend(['a', None, 'c', None])
        actual = d.render_after([0, 1, 2], {1: 'b'})
        self.assertEqual('abc', actual)

    def test_is_all_defined_after_true(self):
        d = Legend(['a', None, 'c', None])
        actual = d.is_all_defined_after([0, 1, 2], {1: 'b'})
        self.assertTrue(actual)

    def test_is_all_defined_after_false(self):
        d = Legend(['a', None, 'c', None])
        actual = d.is_all_defined_after([0, 3, 2], {1: 'b'})
        self.assertFalse(actual)

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


class FillStateTest(TestCase):

    def test_advance_basic(self):
        grid = GridModel.build("____")
        state1 = FillState.from_grid(grid)
        state2 = state1.advance({0: 'a', 1: 'b'})
        self.assertIs(state1.templates, state2.templates)
        self.assertNotEqual(state1, state2)
        self.assertSetEqual({'ab'}, set(state2.render_filled()))

    def test_advance_additional_entries_added(self):
        # noinspection PyTypeChecker
        state2 = FillState(((0,1),(2,3),(0,2),(1,3)), Legend(['a', 'b']), ('ab', None, None, None))
        state3 = state2.advance({2: 'c', 3: 'd'})
        self.assertSetEqual({'ab', 'cd', 'ac', 'bd'}, set(state3.render_filled()))

    def test_advance_additional_entries_added_incorrect(self):
        # noinspection PyTypeChecker
        state2 = FillState(((0,1),(2,3),(0,2),(1,3)), Legend(['a', 'c']), ('ac', None, None, None))
        state3 = state2.advance({2: 'c', 3: 'd'})
        self.assertSetEqual({'ac', 'cd'}, set(state3.render_filled()))

    def test_is_template_filled(self):
        d = Legend(['a', None, 'c'])
        state = FillState(tuple(), d, tuple())
        self.assertTrue(state.is_template_filled((0, 2, 2, 0)))
        self.assertFalse(state.is_template_filled((0, 1, 2, 0)))
        self.assertFalse(state.is_template_filled((1, 3, 5)))
        self.assertTrue(state.is_template_filled(tuple()))

    # noinspection PyTypeChecker
    def test_is_complete(self):
        templates = (
            (0, 1, 2),
            (1, 2),
            (3, 0, 1),
            (5, 2),
            (4, 4, 4, 0, 4, 2),
        )
        state = FillState(templates, Legend(['a', 'b', 'c', 'd', 'e', 'f']), ('acb', 'bc', 'dab', 'fc', 'eeeaec'))
        self.assertTrue(state.is_complete())
        templates = (
            (0, 1, 2),
            (1, 2),
            (12, 4, 1),  # 12 is not satisfed
            (5, 2),
            (4, 4, 4, 0, 4, 2),
        )
        state = FillState(templates, Legend(['a', 'b', 'c', 'd', 'e', 'f']), ('acb', 'bc', None, 'fc', 'eeeaec'))
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
        state = FillState(templates, Legend(['a', 'b', 'c', 'd', 'e', 'f']), ('abc', 'cac', None, 'ec', None))
        unfilled = list(state.unfilled())
        self.assertListEqual([2, 4], unfilled)

    def test_to_legend_updates(self):
        state = FillState((T(0, 1), T(0, 2), T(1, 3), T(2, 3)), Legend(['G', 'H']), ('GH', None, None, None))
        actual = state.to_legend_updates_dict('GX', 1)
        self.assertDictEqual({2: 'X'}, actual)

    def test_list_new_entries(self):
        # bank = create_bank('AB', 'CD', 'AC', 'BD', 'XY', 'JJ', 'OP')
        used: Tuple[Optional[str], ...] = ('AB', None, None, None)
        templates: Tuple[Template, ...] = (T(0,1), T(2,3), T(0,2), T(1,3))
        state = FillState(templates, Legend(['A', 'B', None, None]), used)
        actual = state.list_new_entries('CD', 1)
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
        templates: Tuple[Template, ...] = (T(0,1), T(2,3), T(0,2), T(1,3))
        state = FillState.from_templates(templates)
        actual = set(bank.suggest(state, 0))
        self.assertSetEqual(set(words), actual)

    def test_suggest_3(self):
        bank = create_bank('AB', 'CD', 'AC', 'BD', 'XY', 'JJ', 'OP', 'BX', 'AX')
        used: Tuple[Optional[str], ...] = ('AB', None, None, None)
        templates: Tuple[Template, ...] = (T(0,1), T(2,3), T(0,2), T(1,3))
        state = FillState(templates, Legend(['A', 'B', None, None]), used)
        actual = set(bank.suggest(state, 2))
        self.assertSetEqual({'AC', 'AX'}, actual)

    def test_suggest_2(self):
        words_2chars = ['AB', 'CD', 'AC', 'BD', 'XY', 'JJ', 'OP']
        words_3chars = ['TAB', 'QCD', 'YAC', 'CBD', 'JXY', 'TJJ', 'NOP']
        all_words = words_2chars + words_3chars
        bank = create_bank(*all_words)
        templates: Tuple[Template, ...] = ( T(0,1), T(2,3), T(0,2), T(1,3))
        state = FillState.from_templates(templates)
        actual = set(bank.suggest(state, 0))
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
        templates = state.templates
        self.assertTrue(state.is_complete())
        renderings = [state.legend.render(template) for template in templates]
        self.assertSetEqual(set(expected_words), set(renderings))

    def test_fill_2x2_all(self):
        grid = GridModel.build('____')
        fill_result = self._do_fill_2x2(grid, AllCompleteListener(100000))
        all_filled = fill_result.value
        self.assertIsInstance(all_filled, set)
        for i, state in enumerate(all_filled):
            self.assertIsInstance(state, FillState)
            words = list(state.render_filled())
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