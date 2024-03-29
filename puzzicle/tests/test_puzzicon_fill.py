#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Tuple, NamedTuple, Iterator, Sequence, List
from unittest import TestCase, SkipTest
import puzzicle.puzzicon
from puzzicle.puzzicon.fill import Answer
from puzzicle.puzzicon.fill.state import FillState
from puzzicle.puzzicon.fill import Template
from puzzicle.puzzicon.fill import Pattern
from puzzicle.puzzicon.fill import Suggestion
from puzzicle.puzzicon.grid import GridModel
from puzzicle.puzzicon.fill import WordTuple
from puzzicle.puzzicon.fill import BankItem
import logging
from puzzicle import tests
from puzzicle.tests import Render
_log = logging.getLogger(__name__)

tests.configure_logging()


# noinspection PyPep8Naming
def A(*args) -> Answer:
    """Create a template with the argument indices"""
    return Answer.create(args)

# noinspection PyPep8Naming
def A2(s: str) -> Answer:
    return Answer.create(s)

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
    return [Answer.create(list(map(get_or_default, template))) for template in templates]



class WordTupleTest(TestCase):

    def test_create_from_string(self):
        w = WordTuple('foo')
        self.assertTupleEqual(('f', 'o', 'o'), w)

    def test_create_from_sequence(self):
        w = WordTuple(['f', 'o', 'o'])
        self.assertTupleEqual(('f', 'o', 'o'), w)


class TemplateTest(TestCase):

    def test_len(self):
        t = Template('foo')
        self.assertEqual(3, len(t))

    def test_equals(self):
        self.assertTupleEqual(Template('foo'), Template(('f', 'o', 'o')))

    def test_strength_arg(self):
        self.assertTupleEqual(Template('foo', strength=3), Template(('f', 'o', 'o'), strength=3))
        self.assertTrue(Template('foo', strength=3).is_complete())

    def test__strength(self):
        t = Template('foo')
        self.assertEqual(3, t._strength)
        u = Template(('f', 1, 'o'))
        self.assertEqual(2, u._strength)

    def test_create_from_string(self):
        t = Template('foo')
        self.assertTupleEqual(('f', 'o', 'o'), t)

    def test_create_from_sequence(self):
        w = Template(['f', 'o', 'o'])
        self.assertTupleEqual(('f', 'o', 'o'), w)

    def test_like_wordtuple(self):
        w = WordTuple('foo')
        t = Template('foo')
        self.assertTupleEqual(t, w)

    def test_is_complete_true(self):
        t = Template('foo')
        self.assertTrue(t.is_complete())

    def test_is_complete_false(self):
        t = Template(('a', 'b', 7))
        self.assertFalse(t.is_complete())



class AnswerTest(TestCase):

    def test_define(self):
        t = Answer.create([0, 1, 2])
        self.assertIsInstance(t, tuple)
        self.assertIsInstance(t, Answer)
        self.assertTupleEqual((0, 1, 2), t.content)
        self.assertTupleEqual((None, None, None), t.pattern)
        self.assertEqual(0, t.strength, "strength")

    def test_define_str(self):
        a = Answer.create('abc')
        self.assertIsInstance(a, Answer)
        self.assertTupleEqual(('a', 'b', 'c'), a.content)
        self.assertTupleEqual(('a', 'b', 'c'), a.pattern)

    def test_define_2(self):
        t = Answer.create([0, 'b', 2])
        self.assertTupleEqual((0, 'b', 2), t.content)
        self.assertTupleEqual((None, 'b', None), t.pattern)
        self.assertEqual(1, t.strength, "strength")

    def test_define_shortcut(self):
        t = A(0, 1, 2)
        self.assertIsInstance(t, Answer)
        self.assertEqual(0, t.strength, "strength")

    def test_to_legend_updates(self):
        answer = Answer.create(('G', 2))
        actual = answer.to_updates(BankItem.from_word('GX'))
        self.assertDictEqual({2: 'X'}, actual)


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
        self.assertEqual(Answer.create((0, 2)), state1.answers[1], "precondition")
        self.assertEqual(Answer.create((1, 3)), state1.answers[2], "precondition")
        state2 = state1.advance(Suggestion({0: 'a', 1: 'b'}, {0: A2('ab')}))
        self.assertIs(state1.crosses, state2.crosses)
        self.assertNotEqual(state1, state2)
        self.assertSetEqual({'ab'}, set(Render.filled(state2)))
        self.assertEqual(3, state2.num_incomplete)
        self.assertEqual(Answer.create('ab'), state2.answers[0], "answer 0 change expected")
        self.assertEqual(Answer.create(('a', 2)), state2.answers[1], "answer 1 change expected")
        self.assertEqual(Answer.create(('b', 3)), state2.answers[2], "answer 1 change expected")
        self.assertSetEqual({
            Answer.create(('a', 'b')),
            Answer.create(('a', 2)),
            Answer.create(('b', 3)),
            Answer.create((2, 3)),
        }, set(state2.answers), "expect crossing answer to change")

    def test_advance_additional_entries_added(self):
        # noinspection PyTypeChecker
        state2 = FillState.from_answers((A('a','b'),A(2,3),A('a',2),A('b',3)), (2, 2))
        sugg = Suggestion({2: 'c', 3: 'd'}, {1: A2('cd'), 2: A2('ac'), 3: A2('bd')})
        state3 = state2.advance(sugg)
        self.assertSetEqual({'ab', 'cd', 'ac', 'bd'}, set(Render.filled(state3)))

    def test_advance_additional_entries_added_incorrect(self):
        # noinspection PyTypeChecker
        state2 = FillState.from_answers((A('a', 'c'),A(2,3),A('a',2),A('c',3)), (2, 2))
        sugg = Suggestion({2: 'c', 3: 'd'}, {1: A2('cd'), 2: A2('ac'), 3: A2('cd')})
        state3 = state2.advance(sugg)
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
    def test_provide_unfilled(self):
        templates = (
            (0, 1, 2),
            (2, 0, 2),
            (12, 4, 1),
            (5, 2),
            (4, 9, 4, 0, 4, 2),
        )
        answers = map_all(templates, ['a', 'b', 'c', 'd', 'e', 'f'])
        state = FillState.from_answers(answers, (4, 4))
        unfilled = list(state.provide_unfilled())
        self.assertSetEqual({2, 4}, set(unfilled))

    def test_list_new_entries_using_updates_exclude(self):
        templates: Tuple[Answer, ...] = (A('A', 'B'), A(2,3), A('A', 2), A('B', 3))
        state = FillState.from_answers(templates, (2, 2))
        actual = state.list_new_entries_using_updates({2:'C', 3:'D'}, 1, False)
        self.assertDictEqual({2: A2('AC'), 3: A2('BD')}, actual)

    def test_list_new_entries_using_updates_include(self):
        templates: Tuple[Answer, ...] = (A('A', 'B'), A(2,3), A('A', 2), A('B', 3))
        state = FillState.from_answers(templates, (2, 2))
        actual = state.list_new_entries_using_updates({2:'C', 3:'D'}, 1, True)
        self.assertDictEqual({2: A2('AC'), 3: A2('BD'), 1: A2('CD')}, actual)


