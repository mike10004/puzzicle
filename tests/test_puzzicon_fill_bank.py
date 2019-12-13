#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import random
import sys
import time
from typing import Tuple, NamedTuple, Iterator, Sequence, List, Set
from unittest import TestCase, SkipTest
import puzzicon
from puzzicon.fill import Answer
from puzzicon.fill import Pattern
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
from tests import create_bank
from tests import create_bank_from_wordlist_file
_log = logging.getLogger(__name__)

tests.configure_logging()


# noinspection PyPep8Naming
def A(*args) -> Answer:
    """Create a template with the argument indices"""
    return Answer.define(args)

T = A
B = BankItem.from_word
W = WordTuple

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

    def test_matches(self):
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

    def test_suggest_1(self):
        words = ['AB', 'CD', 'AC', 'BD', 'XY', 'JJ', 'OP']
        bank = create_bank(*words)
        answers: Tuple[Answer, ...] = (T(0,1), T(2,3), T(0,2), T(1,3))
        state = FillState.from_answers(answers, (2, 2))
        actual = collect_new_entries(bank.suggest_updates(state, 0))
        self.assertSetEqual(set(map(WordTuple, words)), actual)

    def test_not_already_used_predicate(self):
        already_used = {'ABC'}
        is_not_already_used = Bank.not_already_used_predicate(already_used)
        self.assertTrue(is_not_already_used(BankItem.from_word('DEF')))
        self.assertFalse(is_not_already_used(BankItem.from_word('ABC')))


    def test_filter_unused(self):
        bank = create_bank('AB', 'CD', 'AC', 'BD', 'XY', 'JJ', 'OP', 'BX', 'AX')
        answer = Answer.define(['A', 2])
        pattern = answer.pattern
        matches = list(bank.filter(pattern))
        used = ('AB', None, None, None)
        unused = list(filter(Bank.not_already_used_predicate(used), matches))
        unused_words = set(map(lambda b: b.rendering, unused))
        self.assertSetEqual({'AC', 'AX'}, unused_words)

    def test_suggest_3(self):
        bank = create_bank('AB', 'CD', 'AC', 'BD', 'XY', 'JJ', 'OP', 'BX', 'AX')

        # AB
        # __

        templates: Tuple[Answer, ...] = (T('A', 'B'), T(2,3), T('A',2), T('B',3))
        state = FillState.from_answers(templates, (2, 2))
        actual = collect_new_entries(bank.suggest_updates(state, 2))
        self.assertSetEqual({W('AC'), W('AX')}, actual)

    def test_suggest_2(self):
        words_2chars = ['AB', 'CD', 'AC', 'BD', 'XY', 'JJ', 'OP']
        words_3chars = ['TAB', 'QCD', 'YAC', 'CBD', 'JXY', 'TJJ', 'NOP']
        all_words = words_2chars + words_3chars
        bank = create_bank(*all_words)
        templates = (T(0,1), T(2,3), T(0,2), T(1,3))
        state = FillState.from_templates(templates, (2, 2))
        actual = collect_new_entries(bank.suggest_updates(state, 0))
        self.assertSetEqual(set(map(WordTuple, words_2chars)), actual)

    def test_filter(self):
        bank = create_bank('ABC', 'DEF', 'ABX', 'G', 'HI', 'ACC')
        actual = set(bank.filter(['A', 'B', None]))
        self.assertSetEqual({B('ABC'), B('ABX')}, actual)

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
