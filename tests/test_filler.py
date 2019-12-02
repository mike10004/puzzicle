from typing import Sequence, Tuple
from unittest import TestCase
import puzzicon
from puzzicon.fill import Legend, FillState, Filler, Bank, FirstCompleteListener, AllCompleteListener, FillListener
from puzzicon.grid import GridModel
import logging
import tests

_log = logging.getLogger(__name__)

tests.configure_logging()


def create_bank(*args):
    puzzemes = puzzicon.create_puzzeme_set(args)
    return Bank([p.canonical for p in puzzemes])


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

    def redefine_1(self):
        d = Legend(['a', None, 'c'])
        f = d.redefine({1: 'b'})
        self.assertEqual(('a', 'b', 'c'), f)

    def redefine_2(self):
        d = Legend(['a', None, 'c'])
        f = d.redefine({5: 'b'})
        self.assertEqual(('a', None, 'c', None, None, 'b'), f)


class FillStateTest(TestCase):

    # noinspection PyTypeChecker
    def advance(self):
        d = Legend(['a', None, 'c'])
        templates = ((1, 2), (3, 4), (5, 6))
        state = FillState(templates, d)
        other = state.advance(Legend(['a', None, 'c', 'd']))
        self.assertIs(state.templates, other.templates)
        self.assertNotEqual(state, other)

    def test_is_template_filled(self):
        d = Legend(['a', None, 'c'])
        state = FillState(tuple(), d)
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
        state = FillState(templates, Legend(['a', 'b', 'c', 'd', 'e', 'f']))
        self.assertTrue(state.is_complete())
        templates = (
            (0, 1, 2),
            (1, 2),
            (12, 4, 1),  # 12 is not satisfed
            (5, 2),
            (4, 4, 4, 0, 4, 2),
        )

    # noinspection PyTypeChecker
    def test_unfilled(self):
        templates = (
            (0, 1, 2),
            (2, 0, 2),
            (12, 4, 1),  # 12 is not satisfed
            (5, 2),
            (4, 9, 4, 0, 4, 2),
        )
        state = FillState(templates, Legend(['a', 'b', 'c', 'd', 'e', 'f']))
        unfilled = list(state.unfilled())
        self.assertListEqual([2, 4], unfilled)


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

    def test_filter(self):
        bank = create_bank('ABC', 'DEF', 'ABX', 'G', 'HI', 'ACC')
        actual = list(bank.filter(['A', 'B', None]))
        self.assertListEqual(['ABC', 'ABX'], actual)


def _show_path(state: FillState, grid: GridModel):
    path = []
    while state is not None:
        path.append(state)
        state = state.previous
    path.reverse()
    for i, state in enumerate(path):
        print("Step {}:\n{}\n".format(i + 1, state.render(grid)))



_WORDS_2x2 = ['AB', 'BD', 'CD', 'AC']
_WORDS_3x3 = ['AB', 'CDE', 'FG', 'AC', 'BDF', 'EG']
_NONWORDS_3x3 = ['AD', 'ADG', 'EDC', 'BF']

# noinspection PyMethodMayBeStatic
class FillerTest(TestCase):

    def _do_fill_2x2(self, grid: GridModel, listener: FillListener):
        wordlist = _WORDS_2x2 + ['XY', 'GH', 'IJ']
        bank = create_bank(*wordlist)
        return self._do_fill(grid, listener, bank)

    def _do_fill(self, grid: GridModel, listener: FillListener, bank: Bank):
        filler = Filler(bank)
        state = FillState.from_grid(grid)
        filler.fill(state, listener)
        _log.info("count = %d", listener.count)
        return listener.value()

    def test_fill_2x2_first(self):
        grid = GridModel.build('____')
        filled = self._do_fill_2x2(grid, FirstCompleteListener(100000))
        self._check_2x2_filled(filled)

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
        all_filled = self._do_fill_2x2(grid, AllCompleteListener(100000))
        self.assertIsInstance(all_filled, set)
        for i, state in enumerate(all_filled):
            self.assertIsInstance(state, FillState)
            words = list(state.render_filled())
            if len(set(words)) != len(words):
                _show_path(state, grid)
            print("solution {}:\n{}\n".format(i + 1, state.render(grid)))
            self._check_2x2_filled(state)
        self.assertEqual(2, len(all_filled))

    def _do_fill_3x3(self, grid: GridModel, listener: FillListener):
        wordlist = _WORDS_3x3 + _NONWORDS_3x3
        bank = create_bank(*wordlist)
        return self._do_fill(grid, listener, bank)

    def _check_3x3_filled(self, state: FillState):
        self._check_filled(state, _WORDS_3x3)

    def test_fill_3x3_first(self):
        grid = GridModel.build('__.___.__')
        filled = self._do_fill_3x3(grid, FirstCompleteListener(100000))
        self._check_3x3_filled(filled)