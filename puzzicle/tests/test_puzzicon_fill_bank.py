#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
import sys
import time
import unittest
from typing import Tuple, NamedTuple, Iterator, Sequence, List, Set
from unittest import TestCase, SkipTest
import puzzicle.puzzicon
from puzzicle.puzzicon.fill import Answer
from puzzicle.puzzicon.fill import Pattern
from puzzicle.puzzicon.fill.state import FillState
from puzzicle.puzzicon.fill.bank import Bank
from puzzicle.puzzicon.fill import Suggestion
from puzzicle.puzzicon.fill import WordTuple
from puzzicle.puzzicon.fill import Template
from puzzicle.puzzicon.fill import BankItem
import logging
from puzzicle import tests
from puzzicle.tests import create_bank
from puzzicle.tests import create_bank_from_wordlist_file
_log = logging.getLogger(__name__)

tests.configure_logging()


# noinspection PyPep8Naming
def A(*args) -> Answer:
    """Define an Answer object"""
    return Answer.create(args)

# noinspection PyPep8Naming
def A2(s) -> Answer:
    return Answer.create(s)


# noinspection PyPep8Naming
def A_from_template(content: Template) -> 'Answer':
    pattern = Pattern([None if isinstance(c, int) else c for c in content])
    strength = content.strength()
    return Answer(content, pattern, strength)


B = BankItem.from_word
W = WordTuple

def render_words(bank: Bank) -> Iterator[str]:
    for tab in bank.tableaus:
        yield ''.join(tab)

class BankItemTest(TestCase):

    def test_from_word(self):
        b = BankItem.from_word('ABC')
        self.assertSetEqual({'ABC'}, b.constituents)
        self.assertEqual('ABC', b.rendering)
        self.assertEqual(WordTuple('ABC'), b.tableau)

    def test___str__(self):
        b = BankItem.from_word('ABC')
        self.assertEqual("BankItem<('A', 'B', 'C')>", str(b))


def collect_new_entries(suggestions: Iterator[Suggestion]) -> Set[WordTuple]:
    actual = set()
    for suggestion in suggestions:
        actual.update(suggestion.new_entries.values())
    return actual

class BankTest(TestCase):

    def test_has_word(self):
        bank = create_bank('ALPHA', 'BETA', 'GAMMA', 'DELTA')
        for good in [tuple('ALPHA'), WordTuple('BETA'), Template('GAMMA')]:
            with self.subTest():
                self.assertTrue(bank.has_word(good))
        for bad in ['alpha', 'ALPHA', tuple('alpha'), WordTuple('alpha'), tuple('EPSILON'), WordTuple('ETA'), Template('ZETA')]:
            with self.subTest():
                self.assertFalse(bank.has_word(bad))

    def test_matches_true(self):
        good = [
            ('ABC', ['A', None, 'C']),
            ('ABC', [None, None, None]),
            ('ABC', ['A', 'B', 'C']),
            ('ABC', [None, None, 'C']),
            ('ABC', [None, 'B', 'C']),
            ('ABC', [None, 'B', None]),
        ]
        for word, pattern_src in good:
            with self.subTest():
                entry = BankItem.from_word(word)
                pattern = Pattern(pattern_src)
                self.assertTrue(Bank.matches(entry, pattern), f"expect {entry} matches {pattern}")

    def test_matches_false(self):
        bad = [
            ('ABC', ['X', None, 'C']),
            ('ABC', [None, 'C', None]),
            ('ABC', ['X', 'B', 'C']),
            ('ABC', ['A', 'B']),
        ]
        for entry, pattern in bad:
            with self.subTest():
                entry = BankItem.from_word(entry)
                pattern = Pattern(pattern)
                self.assertFalse(Bank.matches(entry, pattern), f"expect {entry} does NOT match {pattern}")

    def test_rank_candidate(self):
        bank = create_bank('AB', 'CD', 'AC', 'BD', 'XY', 'JJ', 'OP', 'BX', 'AX')
        state = FillState.from_answers(tuple(), (0, 0))
        self.assertGreater(bank.rank_candidate(state, A_from_template(Template('XY'))), 0)
        self.assertLessEqual(bank.rank_candidate(state, A_from_template(Template('MY'))), 0)
        self.assertLessEqual(bank.rank_candidate(state, A_from_template(Template(('M', None)))), 0)

    def test_not_already_used_predicate(self):
        already_used = {'ABC'}
        is_not_already_used = Bank.not_already_used_predicate(already_used)
        self.assertTrue(is_not_already_used(BankItem.from_word('DEF')))
        self.assertFalse(is_not_already_used(BankItem.from_word('ABC')))

    def test_count_filter(self):
        bank = create_bank('AB', 'CD', 'AC', 'BD', 'XY', 'JJ', 'OP', 'BX', 'AX')
        count = bank.count_filter(Pattern(('A', None)))
        self.assertEqual(3, count)

    def test_filter_unused(self):
        bank = create_bank('AB', 'CD', 'AC', 'BD', 'XY', 'JJ', 'OP', 'BX', 'AX')
        answer = Answer.create(['A', 2])
        pattern = answer.pattern
        matches = list(bank.filter(pattern))
        used = ('AB', None, None, None)
        unused = list(filter(Bank.not_already_used_predicate(used), matches))
        unused_words = set(map(lambda b: b.rendering, unused))
        self.assertSetEqual({'AC', 'AX'}, unused_words)

    def test_suggest_1(self):
        words = ['AB', 'CD', 'AC', 'BD', 'XY', 'JJ', 'OP']
        bank = create_bank(*words)
        answers: Tuple[Answer, ...] = (A(0,1), A(2,3), A(0,2), A(1,3))
        state = FillState.from_answers(answers, (2, 2))
        updates = list(bank.suggest(state, 0))
        actual = collect_new_entries(updates)
        self.assertSetEqual({A2('AB'), A2('AC'), A2('JJ')}, actual)

    def test_suggest_2(self):
        words_2chars = ['AB', 'CD', 'AC', 'BD', 'XY', 'JJ', 'OP']
        words_3chars = ['TAB', 'QCD', 'YAC', 'CBD', 'JXY', 'TJJ', 'NOP']
        all_words = words_2chars + words_3chars
        bank = create_bank(*all_words)
        templates = (A(0,1), A(2,3), A(0,2), A(1,3))
        state = FillState.from_answers(templates, (2, 2))
        actual = collect_new_entries(bank.suggest(state, 0))
        self.assertSetEqual({A2('AB'), A2('AC'), A2('JJ')}, actual)

    def test_suggest_3(self):
        bank = create_bank('AB', 'CD', 'AC', 'BD', 'XY', 'JJ', 'OP', 'BX', 'AX')

        # AB
        # __

        templates: Tuple[Answer, ...] = (A('A', 'B'), A(2,3), A('A',2), A('B',3))
        state = FillState.from_answers(templates, (2, 2))
        actual = collect_new_entries(bank.suggest(state, 2))
        self.assertSetEqual({A2('AC'), A2('AX')}, actual)

    def test_filter(self):
        bank = create_bank('ABC', 'DEF', 'ABX', 'G', 'HI', 'ACC')
        actual = set(bank.filter(Pattern(['A', 'B', None])))
        self.assertSetEqual({B('ABC'), B('ABX')}, actual)

    def test_big_bank(self):
        self.skipTest("this has an error but I can't remember what it's supposed to do")
        start = time.perf_counter()
        bank = create_bank_from_wordlist_file()
        end = time.perf_counter()
        print("sizeof(/usr/share/dict/words) =", sys.getsizeof(bank))
        print("created in {} seconds".format(end - start))
        matches = list(bank.filter(['A', None, None, 'L', 'E']))
        self.assertIn('APPLE', matches)
        self.assertIn('ADDLE', matches)

    @unittest.skip("functionality not yet implemented")
    def test_bank_create_clean(self):
        bank = create_bank("consciousness's", "d'Estaing", "sewing", "'allo", "ain't")
        actual = set(render_words(bank))
        self.assertSetEqual({"CONSCIOUSNESS", "DESTAING", "SEWING", "ALLO", "AINT"}, actual)

