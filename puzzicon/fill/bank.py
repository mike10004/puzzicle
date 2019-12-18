#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import itertools
import logging
from collections import defaultdict
from typing import Collection, FrozenSet, Set, Optional
from typing import List, Sequence, Dict, Iterator, Callable

from puzzicon.fill import Pattern, WordTuple, BankItem, Suggestion, Answer
from puzzicon.fill.state import FillState

_log = logging.getLogger(__name__)
_EMPTY_SET = frozenset()

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

    def __init__(self, deposits: FrozenSet[BankItem], tableaus: FrozenSet[WordTuple], by_pattern: Dict[Pattern, List[BankItem]], pattern_registry_cap=None, debug:bool=False):
        assert isinstance(deposits, frozenset)
        self.deposits = deposits
        assert isinstance(tableaus, frozenset)
        self.tableaus = tableaus
        assert isinstance(by_pattern, dict)
        self.by_pattern = by_pattern
        self.debug = debug
        self.pattern_registry_cap = pattern_registry_cap

    @staticmethod
    def with_registry(entries: Sequence[str], pattern_registry_cap=9, debug: bool=False):
        deposits = frozenset([BankItem.from_word(entry) for entry in entries])
        tableaus = frozenset([item.tableau for item in deposits])
        by_pattern = defaultdict(list)
        for entry in deposits:
            if entry.length() <= pattern_registry_cap:
                patterns = _patterns(entry.tableau)
                for pattern in patterns:
                    by_pattern[pattern].append(entry)
        for pattern_list in by_pattern.values():
            pattern_list.sort()
        return Bank(deposits, tableaus, by_pattern, pattern_registry_cap, debug)

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
        if self.pattern_registry_cap is not None and pattern.length() <= self.pattern_registry_cap:
            try:
                pattern_matches = self.by_pattern[pattern]
                return pattern_matches.__iter__()
            except KeyError:  # implies zero words correspond to the pattern
                return _EMPTY_SET.__iter__()
        return self.filter_slowly(pattern)

    def filter_slowly(self, pattern: Pattern) -> Iterator[BankItem]:
        """
        Returns an iterator that supplies items that match the pattern
        by iterating over all bank items and filtering out nonmatches.
        @param pattern: the pattern
        @return: iterator over matching deposits
        """
        def must_match(entry: BankItem):
            return Bank.matches(entry, pattern)
        return filter(must_match, self.deposits)

    def _explode(self, iterator):
        if self.debug:
            return list(iterator)
        return iterator

    def suggest_updates(self, state: FillState, answer_idx: int) -> Iterator[Suggestion]:
        this_bank = self
        answer: Answer = state.answers[answer_idx]
        pattern = answer.pattern
        matches: Iterator[BankItem] = self._explode(self.filter(pattern))
        unused: Iterator[BankItem] = self._explode(filter(Bank.not_already_used_predicate(state.used), matches))
        for bank_item in unused:
            legend_updates_ = answer.to_updates(bank_item)
            def evaluator(entry: WordTuple):
                return this_bank.is_valid_new_entry(state, entry)
            new_answers: Optional[Dict[int, WordTuple]] = state.list_new_entries_using_updates(legend_updates_, answer_idx, True, evaluator)
            if new_answers is not None:
                new_entries_dict: Dict[int, WordTuple] = dict()
                new_entries_set: Set[WordTuple] = set()
                has_dupes = False
                for a_idx, new_entry in new_answers.items():
                    # test if new batch of entries contains duplicates
                    if new_entry in new_entries_set:
                        has_dupes = True
                        break
                    new_entries_dict[a_idx] = new_entry
                    new_entries_set.add(new_entry)
                if not has_dupes:
                    yield Suggestion(legend_updates_, new_entries_dict)

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
