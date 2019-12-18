#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from puzzicon import Puzzeme
import puzzicon.grid
from collections import defaultdict
import itertools
from puzzicon.grid import GridModel
from typing import Tuple, List, Sequence, Dict, Optional, Iterator, Callable, Any
from typing import NamedTuple, Collection, FrozenSet, Union, Iterable
import logging
from puzzicon.fill import Pattern, WordTuple, BankItem, Suggestion, Answer
from puzzicon.fill.state import FillState

_log = logging.getLogger(__name__)


def _powerset(iterable):
    """powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)"""
    s = list(iterable)
    return itertools.chain.from_iterable(itertools.combinations(s, r) for r in range(len(s)+1))


def _patterns(entry: WordTuple) -> List[Pattern]:
    entry_len = len(entry)
    positions = [i for i in range(entry_len)]
    patterns = []
    for subset in _powerset(positions):
        pattern = Pattern([(entry[i] if i in subset else None) for i in range(entry_len)])
        patterns.append(pattern)
    return patterns


class Bank(object):

    def __init__(self, deposits: FrozenSet[BankItem], tableaus: FrozenSet[WordTuple], by_pattern: Dict[Pattern, List[BankItem]], debug:bool=True):
        assert isinstance(deposits, frozenset)
        self.deposits = deposits
        assert isinstance(tableaus, frozenset)
        self.tableaus = tableaus
        assert isinstance(by_pattern, dict)
        self.by_pattern = by_pattern
        self.debug = debug

    @staticmethod
    def with_registry(entries: Sequence[str], pattern_registry_cap=9):
        deposits = frozenset([BankItem.from_word(entry) for entry in entries])
        tableaus = frozenset([item.tableau for item in deposits])
        by_pattern = defaultdict(list)
        for entry in deposits:
            if entry.length() <= pattern_registry_cap:
                patterns = _patterns(entry.tableau)
                for pattern in patterns:
                    by_pattern[pattern].append(entry)
        # for pattern_list in by_pattern.values():
        #     pattern_list.sort()
        return Bank(deposits, tableaus, by_pattern)

    @staticmethod
    def matches(entry: BankItem, pattern: Pattern):
        assert isinstance(entry, BankItem), "entry must be a BankItem"
        assert isinstance(pattern, Pattern), "pattern must be a Pattern"
        if entry.length() != len(pattern):
            return False
        for i in range(pattern.length()):
            if pattern[i] is not None and pattern[i] != entry.tableau[i]:
                return False
        return True

    def filter(self, pattern: Pattern) -> Iterator[BankItem]:
        if not isinstance(pattern, tuple):
            pattern = tuple(pattern)
        try:
            pattern_matches = self.by_pattern[pattern]
            return pattern_matches.__iter__()
        except KeyError:
            # This will happen either because (a) zero words correspond to the pattern, or (b) the pattern
            # was not registered because its length is above the registry cap
            # TODO keep track of cap on instantiation and return empty set if entry length is under the cap
            def must_match(entry: BankItem):
                return Bank.matches(entry, pattern)
            return filter(must_match, self.deposits)

    def _explode(self, iterator):
        if self.debug:
            return list(iterator)
        return iterator

    def suggest_updates(self, state: FillState, template_idx: int) -> Iterator[Suggestion]:
        this_bank = self
        answer: Answer = state.answers[template_idx]
        pattern = answer.pattern
        matches: Iterator[BankItem] = self._explode(self.filter(pattern))
        unused: Iterator[BankItem] = self._explode(filter(Bank.not_already_used_predicate(state.used), matches))
        updates_iter = self._explode(map(lambda entry: state.to_legend_updates_dict(entry, template_idx), unused))
        for legend_updates_ in updates_iter:
            def evaluator(entry: WordTuple):
                return this_bank.is_valid_new_entry(state, entry)
            new_answers: Dict[int, WordTuple] = state.list_new_entries_using_updates(legend_updates_, template_idx, True, evaluator)
            if new_answers is not None:
                new_entries_set: Dict[int, WordTuple] = dict()
                for a_idx, new_entry in new_answers.items():
                    # test if new batch of entries contains duplicates
                    if new_entry in new_entries_set.values():
                        return False
                    new_entries_set[a_idx] = new_entry
                yield Suggestion(legend_updates_, new_entries_set)

    @staticmethod
    def not_already_used_predicate(already_used: Collection[str]) -> Callable[[BankItem], bool]:
        def not_already_used(entry: BankItem):
            return entry.rendering not in already_used
        return not_already_used

    def is_valid_new_entry(self, state: FillState, entry: WordTuple):
        return entry not in state.used and self.has_word(entry)

    def has_word(self, entry: WordTuple):
        return entry in self.tableaus

    def __str__(self):
        return "Bank<num_words={},num_patterns_registered={}>".format(len(self.deposits), len(self.by_pattern))
