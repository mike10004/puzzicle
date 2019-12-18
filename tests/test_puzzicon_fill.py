#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Tuple, NamedTuple, Iterator, Sequence, List
from unittest import TestCase, SkipTest
import puzzicon
from puzzicon.fill import Answer
from puzzicon.fill.state import FillState
from puzzicon.fill import Template
from puzzicon.fill import Pattern
from puzzicon.fill import Suggestion
from puzzicon.grid import GridModel
from puzzicon.fill import WordTuple
from puzzicon.fill import BankItem
import logging
import tests
from tests import Render
_log = logging.getLogger(__name__)

tests.configure_logging()


# noinspection PyPep8Naming
def A(*args) -> Answer:
    """Create a template with the argument indices"""
    return Answer.define(args)

T = A

def template(*args) -> Template:
    return Template(args)

def pattern(*args) -> Pattern:
    return Pattern(args)

def map_all(templates: Sequence[int], legend: Sequence[str]) -> List[Answer]:
    def get_or_default(idx: int):
        try:
            return legend[idx]
        except IndexError:
            return idx
    return [Answer.define(list(map(get_or_default, template))) for template in templates]



class WordTupleTest(TestCase):

    def test_create_from_string(self):
        w = WordTuple('foo')
        self.assertTupleEqual(('f', 'o', 'o'), w)

    def test_create_from_sequence(self):
        w = WordTuple(['f', 'o', 'o'])
        self.assertTupleEqual(('f', 'o', 'o'), w)


class AnswerTest(TestCase):

    def test_create(self):
        t = Answer.define([0, 1, 2])
        self.assertIsInstance(t, tuple)
        self.assertTupleEqual((0, 1, 2), t.content)
        self.assertTupleEqual((None, None, None), t.pattern)
        self.assertEqual(0, t.strength, "strength")

    def test_create2(self):
        t = Answer.define([0, 'b', 2])
        self.assertTupleEqual((0, 'b', 2), t.content)
        self.assertTupleEqual((None, 'b', None), t.pattern)
        self.assertEqual(1, t.strength, "strength")

    def test_create_shortcut(self):
        t = T(0, 1, 2)
        self.assertIsInstance(t, Answer)
        self.assertEqual(0, t.strength, "strength")

    def test_to_legend_updates(self):
        answer = Answer.define(('G', 2))
        actual = answer.to_updates(BankItem.from_word('GX'))
        self.assertDictEqual({2: 'X'}, actual)



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

    def test_from_answers(self):
        answers = (A(0, 1), A(2, 3), A(0, 2), A(1, 3))
        state = FillState.from_answers(answers, (2, 2))
        self.assertTupleEqual(answers, state.answers)
        self.assertTupleEqual((
            (0, 2),
            (0, 3),
            (1, 2),
            (1, 3),
        ), state.crosses)
        self.assertTupleEqual((None, None, None, None), state.used)
        self.assertEqual(4, state.num_incomplete)

    def test_advance_basic(self):
        grid = GridModel.build("____")  # 2x2
        state1 = FillState.from_grid(grid)
        self.assertEqual(4, state1.num_incomplete)
        self.assertEqual(Answer.define((0, 2)), state1.answers[1], "precondition")
        self.assertEqual(Answer.define((1, 3)), state1.answers[2], "precondition")
        state2 = state1.advance_unchecked(Suggestion({0: 'a', 1: 'b'}, {0: WordTuple('ab')}))
        self.assertIs(state1.crosses, state2.crosses)
        self.assertNotEqual(state1, state2)
        self.assertSetEqual({'ab'}, set(Render.filled(state2)))
        self.assertEqual(3, state2.num_incomplete)
        self.assertEqual(Answer.define('ab'), state2.answers[0], "answer 0 change expected")
        self.assertEqual(Answer.define(('a', 2)), state2.answers[1], "answer 1 change expected")
        self.assertEqual(Answer.define(('b', 3)), state2.answers[2], "answer 1 change expected")
        self.assertSetEqual({
            Answer.define(('a', 'b')),
            Answer.define(('a', 2)),
            Answer.define(('b', 3)),
            Answer.define((2, 3)),
        }, set(state2.answers), "expect crossing answer to change")

    def test_advance_additional_entries_added(self):
        # noinspection PyTypeChecker
        state2 = FillState.from_answers((A('a','b'),A(2,3),A('a',2),A('b',3)), (2, 2))
        sugg = Suggestion({2: 'c', 3: 'd'}, {1: WordTuple('cd'), 2: WordTuple('ac'), 3: WordTuple('bd')})
        state3 = state2.advance_unchecked(sugg)
        self.assertSetEqual({'ab', 'cd', 'ac', 'bd'}, set(Render.filled(state3)))

    def test_advance_additional_entries_added_incorrect(self):
        # noinspection PyTypeChecker
        state2 = FillState.from_answers((A('a', 'c'),A(2,3),A('a',2),A('c',3)), (2, 2))
        sugg = Suggestion({2: 'c', 3: 'd'}, {1: WordTuple('cd'), 2: WordTuple('ac'), 3: WordTuple('cd')})
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
        state = FillState.from_answers(map_all(templates, ['a', 'b', 'c', 'd', 'e', 'f']), (3, 3))
        self.assertTrue(state.is_complete())
        templates = (
            (0, 1, 2),
            (1, 2),
            (12, 4, 1),  # 12 is not satisfed
            (5, 2),
            (4, 4, 4, 0, 4, 2),
        )
        state = FillState.from_answers(map_all(templates, ['a', 'b', 'c', 'd', 'e', 'f']), (4, 4))
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
        state = FillState.from_answers(answers, (4, 4))
        unfilled = list(state.unfilled())
        self.assertListEqual([2, 4], unfilled)

    def test_list_new_entries_using_updates_exclude(self):
        templates: Tuple[Answer, ...] = (T('A', 'B'), T(2,3), T('A', 2), T('B', 3))
        state = FillState.from_answers(templates, (2, 2))
        actual = state.list_new_entries_using_updates({2:'C', 3:'D'}, 1, False)
        self.assertDictEqual({2: WordTuple('AC'), 3: WordTuple('BD')}, actual)

    def test_list_new_entries_using_updates_include(self):
        templates: Tuple[Answer, ...] = (T('A', 'B'), T(2,3), T('A', 2), T('B', 3))
        state = FillState.from_answers(templates, (2, 2))
        actual = state.list_new_entries_using_updates({2:'C', 3:'D'}, 1, True)
        self.assertDictEqual({2: WordTuple('AC'), 3: WordTuple('BD'), 1: WordTuple('CD')}, actual)


