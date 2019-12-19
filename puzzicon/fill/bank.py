#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import hashlib
import itertools
import logging
import pickle
import os.path
from collections import defaultdict
from typing import Collection, FrozenSet, Set, Optional, BinaryIO, Iterable
from typing import List, Dict, Iterator, Callable

import puzzicon
from puzzicon import Puzzeme
from puzzicon.fill import Pattern, WordTuple, BankItem, Suggestion, Answer, Template
from puzzicon.fill.state import FillState, AnswerChangeset

_log = logging.getLogger(__name__)
_EMPTY_SET = frozenset()
_DEFAULT_MAX_PATTERN_LEN = 9
_FILENAME_SAFE_CHARS = 'QWERTYUIOPASDFGHJKLZXCVBNMqwertyuiopasdfghjklzxcvbnm1234567890_'

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

    def size(self) -> int:
        return len(self.deposits)

    @staticmethod
    def with_registry(entries: Iterable[str], pattern_registry_cap=_DEFAULT_MAX_PATTERN_LEN, debug: bool=False):
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

    def count_filter(self, pattern: Pattern, uncountable=None) -> Optional[int]:
        """
        Counts the number of bank deposits that would be returned by a filter call.
        @param pattern:  pattern to match
        @param uncountable: value to return if uncountable
        @return: count of matching deposits, or the value of uncountable parameter
        """
        if not isinstance(pattern, tuple):
            pattern = tuple(pattern)
        if self.pattern_registry_cap is not None and pattern.length() <= self.pattern_registry_cap:
            try:
                pattern_matches = self.by_pattern[pattern]
                return len(pattern_matches)
            except KeyError:  # implies zero words correspond to the pattern
                return 0
        return uncountable

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
        matches: Iterator[BankItem] = self._explode(self.filter(answer.pattern))
        unused: Iterator[BankItem] = self._explode(filter(Bank.not_already_used_predicate(state.used), matches))
        suggestions = []
        for bank_item in unused:
            legend_updates_ = answer.to_updates(bank_item)
            def evaluator(candidate: Answer) -> int:
                return this_bank.rank_candidate(state, candidate)
            new_answers: AnswerChangeset = state.list_new_entries_using_updates(legend_updates_, answer_idx, True, evaluator)
            if new_answers and new_answers.rank > 0:
                new_entries_set: Set[Template] = set()
                has_dupes = False
                for a_idx, new_entry in new_answers.items():
                    # test if new batch of entries contains duplicates
                    if new_entry.content in new_entries_set:
                        has_dupes = True
                        break
                    new_entries_set.add(new_entry.content)
                if not has_dupes:
                    suggestions.append(Suggestion(legend_updates_, new_answers, new_answers.rank))
        suggestions.sort(key=lambda s: (0 if s.rank is None else s.rank), reverse=True)
        return suggestions.__iter__()

    @staticmethod
    def not_already_used_predicate(already_used: Collection[str]) -> Callable[[BankItem], bool]:
        def not_already_used(entry: BankItem):
            return entry.rendering not in already_used
        return not_already_used

    def rank_candidate(self, state: FillState, candidate: Answer) -> Optional[int]:
        count = self.count_filter(candidate.pattern, uncountable=None)
        if count is None:
            return None
        if count == 0:
            return 0
        assert count > 0
        if candidate.content.is_complete():
            if candidate.content in state.used:
                return -1
            # suppress inspection because complete Template acts as a WordTuple
            # noinspection PyTypeChecker
            if not self.has_word(candidate.content):
                return -1
        return count

    def has_word(self, entry: WordTuple):
        return entry in self.tableaus

    def __str__(self):
        return "Bank<num_words={},num_patterns_registered={}>".format(len(self.deposits), len(self.by_pattern))


# noinspection PyMethodMayBeStatic
class BankSerializer(object):

    def serialize(self, bank: Bank, ofile: BinaryIO):
        pickle.dump(bank, ofile)

    def serialize_to_file(self, bank: Bank, pathname: str):
        with open(pathname, 'wb') as ofile:
            self.serialize(bank, ofile)

    def deserialize(self, ifile: BinaryIO) -> Bank:
        return pickle.load(ifile)

    def deserialize_from_file(self, pathname: str) -> Bank:
        with open(pathname, 'rb') as ifile:
            return self.deserialize(ifile)


_DEFAULT_WORDLIST_PATHNAME = '/usr/share/dict/words'


# noinspection PyPep8Naming
def _CANONICAL_XFORM(puzzeme_set: Set[Puzzeme]):
    return [p.canonical for p in puzzeme_set]

class BankLoader(object):

    def __init__(self, cache_dir: Optional[str]=None, tag: Optional[str]=None, max_word_length: Optional[int]=None, puzzeme_set_transform: Callable[[Set[Puzzeme]], Set[str]]=_CANONICAL_XFORM):
        self.cache_dir = cache_dir
        self.tag = tag
        self.max_word_length = max_word_length
        self.puzzeme_set_transform = puzzeme_set_transform
        self.debug_bank = False

    @staticmethod
    def get_default_cache_dir():
        return os.path.join(os.getenv('HOME'), '.local', 'share', 'puzzicon', 'wordbank')

    def _construct_filename(self, wordlist_pathname) -> str:
        tag = str(self.tag or 'default')
        tag = ''.join([ch if ch in _FILENAME_SAFE_CHARS else '_' for ch in tag])
        h = hashlib.sha256()
        with open(wordlist_pathname, 'rb') as ifile:
            h.update(ifile.read())
        basename = h.hexdigest()
        return "bank-{}-{}.pickle".format(tag, basename)

    def load_fresh(self, wordlist_pathname=_DEFAULT_WORDLIST_PATHNAME):
        puzzemes = puzzicon.read_puzzeme_set(wordlist_pathname)
        if self.max_word_length is not None:
            puzzemes = filter(lambda p: len(p.canonical) <= self.max_word_length, puzzemes)
        strings = self.puzzeme_set_transform(puzzemes)
        bank = Bank.with_registry(strings, debug=self.debug_bank)
        serializer = BankSerializer()
        if self.cache_dir is not None:
            bank_pathname = self.get_cached_bank_pathname(wordlist_pathname)
            os.makedirs(os.path.dirname(bank_pathname), exist_ok=True)
            serializer.serialize_to_file(bank, bank_pathname)
            _log.debug("bank written to %s", bank_pathname)
        return bank

    def get_cached_bank_pathname(self, wordlist_pathname: str) -> str:
        assert self.cache_dir, "cache directory must be defined for this loader"
        return os.path.join(self.cache_dir, self._construct_filename(wordlist_pathname))

    def load(self, wordlist_pathname=_DEFAULT_WORDLIST_PATHNAME):
        if self.cache_dir is not None:
            cached_bank_pathname = self.get_cached_bank_pathname(wordlist_pathname)
            try:
                serializer = BankSerializer()
                bank = serializer.deserialize_from_file(cached_bank_pathname)
                _log.debug("cached bank loaded from %s", cached_bank_pathname)
                return bank
            except FileNotFoundError:
                pass
        return self.load_fresh(wordlist_pathname)
