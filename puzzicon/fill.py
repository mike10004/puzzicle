#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from puzzicon import Puzzeme
import puzzicon.grid
from collections import defaultdict
import itertools
from puzzicon.grid import GridModel
from typing import Tuple, List, Sequence, Dict, Optional, Iterator, Callable
from typing import NamedTuple, Collection, FrozenSet, Union, Iterable
import logging


_log = logging.getLogger(__name__)
_VALUE = 1
_BLANK = '_'
_EMPTY_SET = frozenset()


class Word(NamedTuple):

    pass


class Answer(NamedTuple):

    content: Tuple[Union[int, str], ...]
    pattern: Tuple[Optional[str], ...]
    strength: int

    @staticmethod
    def define(content: Sequence[Union[int, str]]) -> 'Answer':
        assert isinstance(content, tuple)
        pattern = tuple([(None if isinstance(x, int) else x) for x in content])
        strength = len(pattern) - sum([0 if p is None else p for p in pattern])
        # noinspection PyTypeChecker
        return Answer(content, pattern, strength)

    def render(self, blank=_BLANK) -> str:
        return ''.join([blank if p is None else p for p in self.pattern])

    def is_defined(self, index: int):
        """Checks whether the grid index at the given content index is already mapped to a letter."""
        return self.pattern[index] is not None

    def is_all_defined(self) -> bool:
        raise NotImplementedError()

    def is_all_defined_after(self, legend_updates: Dict[int, str]) -> bool:
        raise NotImplementedError()

    def render_after(self, legend_updates: Dict[int, str]) -> Tuple[Optional[str], ...]:
        raise NotImplementedError()



def _sort_and_check_duplicates(items: list) -> bool:
    items.sort()
    for i in range(1, len(items)):
        if items[i - 1] == items[i]:
            return True
    return False


class Suggestion(object):

    def __init__(self, legend_updates: Dict[int, str], new_entries: Dict[int, str]):
        """
        Construct an instance.
        @param legend_updates: mapping of grid index to square value
        @param new_entries: mapping of answer index to bank words
        """
        self.legend_updates = legend_updates
        self.new_entries = new_entries
        assert new_entries, "suggestion must contain at least one new entry"


class FillState(NamedTuple):

    answers: Tuple[Answer, ...]
    crosses: Tuple[Tuple[int, ...]]     # maps each grid index to all indexes of answers that contain the grid index
    used: Tuple[Optional[str], ...]     # maps each answer index to rendering of that answer, if complete, or else None
    num_incomplete: int                 # number of incomplete answers remaining

    # deprecated: use from_answers instead
    @staticmethod
    def from_templates(templates: Tuple[Answer, ...]) -> 'FillState':
        return FillState.from_answers(templates)

    @staticmethod
    def from_answers(templates: Tuple[Answer, ...]) -> 'FillState':
        raise NotImplementedError()

    def is_complete(self):
        return self.num_incomplete == 0

    def unfilled(self) -> Iterator[int]:
        """Return a generator of indexes of answers that are not completely filled."""
        return map(lambda pair: pair[0], filter(lambda pair: pair[1] is None, enumerate(self.used)))

    def advance_unchecked(self, suggestion: Suggestion) -> 'FillState':
        raise NotImplementedError()

    @staticmethod
    def from_grid(grid: GridModel) -> 'FillState':
        answers: List[Answer] = []
        for entry in grid.entries():
            indexes = []
            for square in entry.squares:
                index = grid.get_index(square)
                indexes.append(index)
            answers.append(Answer.define(indexes))
        return FillState.from_answers(tuple(answers))

    # noinspection PyProtectedMember
    def render(self, grid: GridModel, newline="\n", none_val='_', dark=puzzicon.grid._DARK) -> str:
        legend = {}
        entries = grid.entries()
        assert len(entries) == len(self.answers)
        for i in range(len(self.answers)):
            entry, pattern = entries[i], self.answers[i].pattern
            assert len(entry.squares) == len(pattern)
            for j in range(len(pattern)):
                if pattern[j] is not None:
                    legend[entry.squares[j].index] = pattern[j]
        rows = []
        for r in range(grid.num_rows):
            row = []
            for c in range(grid.num_cols):
                s = grid.square(r, c)
                if s.dark():
                    row.append(dark)
                else:
                    i = grid.get_index(s)
                    v = legend.get(i, none_val)
                    row.append(v)
            rows.append(''.join(row))
        return newline.join(rows)

    def to_legend_updates_dict(self, entry: str, template_idx: int) -> Dict[int, str]:
        """
        Shows what new grid index to letter mappings would be defined if a template were to be filled by the given entry.
        """
        answer: Answer = self.answers[template_idx]
        legend_updates: Dict[int, str] = {}
        for i in range(len(entry)):
            if answer.is_defined(i):
                k, v = answer.content[i], entry[i]
                legend_updates[k] = v
        return legend_updates

    def list_new_entries_using_updates(self, legend_updates: Dict[int, str], template_idx: int,
                                       include_template_idx: bool, evaluator: Optional[Callable]=None) -> Optional[Dict[int, Tuple[str, ...]]]:
        """
        Return a dictionary mapping answer indexes to word-tuples that includes only
        those mappings where the word-tuple becomes completed by the given legend updates.

        The answer corresponding to the given answer index is included
        in the set of updates only if include_template_idx is true.

        If an evaluator is provided, it must accept a word-tuple as an argument and
        return False if the word is not valid. This aborts the process of listing
        new entries and returns early with None.
        """
        updated_answers = {}
        for grid_index in legend_updates:
            crossing_answer_indexes = self.crosses[grid_index]
            for a_idx in crossing_answer_indexes:
                if include_template_idx or (a_idx != template_idx):
                    answer: Answer = self.answers[a_idx]
                    if answer.is_all_defined_after(legend_updates):
                        another_entry = answer.render_after(legend_updates)
                        if evaluator is not None and (not evaluator(another_entry)):
                            return None
                        updated_answers[a_idx] = another_entry
        return updated_answers


def _powerset(iterable):
    """powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)"""
    s = list(iterable)
    return itertools.chain.from_iterable(itertools.combinations(s, r) for r in range(len(s)+1))


class Bank(NamedTuple):

    word_set: FrozenSet[str]
    by_pattern: Dict[Tuple[Optional[str]], List[str]] = {}

    @staticmethod
    def with_registry(entries: Sequence[str], pattern_registry_cap=9):
        word_set = frozenset(entries)
        by_pattern = defaultdict(list)
        for entry in entries:
            if len(entry) <= pattern_registry_cap:
                patterns = Bank.patterns(entry)
                for pattern in patterns:
                    by_pattern[pattern].append(entry)
        return Bank(word_set, by_pattern)

    @staticmethod
    def patterns(entry: str) -> List[Tuple]:
        positions = [i for i in range(len(entry))]
        patterns = []
        for subset in _powerset(positions):
            pattern = tuple([(entry[i] if i in subset else None) for i in range(len(entry))])
            patterns.append(pattern)
        return patterns

    @staticmethod
    def matches(entry, pattern):
        if len(entry) != len(pattern):
            return False
        for i in range(len(pattern)):
            if pattern[i] is not None and pattern[i] != entry[i]:
                return False
        return True

    def filter(self, pattern: Sequence[Optional[str]]) -> Iterator[str]:
        if not isinstance(pattern, tuple):
            pattern = tuple(pattern)
        try:
            pattern_matches = self.by_pattern[pattern]
        except KeyError:
            # This will happen either because (a) zero words correspond to the pattern, or (b) the pattern
            # was not registered because its length is above the registry cap
            # TODO keep track of cap on instantiation and return empty set if entry length is under the cap
            return filter(lambda entry: Bank.matches(entry, pattern), self)
        return pattern_matches.__iter__()

    def suggest_updates(self, state: FillState, template_idx: int) -> Iterator[Suggestion]:
        answer: Answer = state.answers[template_idx]
        pattern = answer.pattern
        matches = self.filter(pattern)
        unused = filter(Bank.not_already_used_predicate(state.used), matches)
        updates_iter = map(lambda entry: state.to_legend_updates_dict(entry, template_idx), unused)
        for legend_updates_ in updates_iter:
            evaluator = lambda entry: self.is_valid_new_entry(state, entry)
            new_answers: Dict[int, Tuple[str, ...]] = state.list_new_entries_using_updates(legend_updates_, template_idx, True, evaluator)
            if new_answers is not None:
                new_entries_set: Dict[int, Tuple[str,...]] = dict()
                for a_idx, new_entry in new_answers.items():
                    # test if new batch of entries contains duplicates
                    if new_entry in new_entries_set:
                        return False
                    new_entries_set[a_idx] = new_entry
                yield Suggestion(legend_updates_, new_entries_set)

    @staticmethod
    def not_already_used_predicate(already_used: Collection[str]) -> Callable[[str], bool]:
        def not_already_used(entry):
            return entry not in already_used
        return not_already_used

    def is_valid_new_entry(self, state: FillState, entry: str):
        return entry not in state.used and self.has_word(entry)

    def has_word(self, entry: str):
        return entry in self.word_set

    def __str__(self):
        return "Bank<num_words={},num_patterns_registered={}>".format(len(self.word_set), len(self.by_pattern))


_CONTINUE = False
_STOP = True

class FillListener(object):

    def __init__(self, threshold: int=None, notify: Optional[Callable[['FillListener', FillState, Bank, bool], None]]=None):
        self.threshold = threshold
        self.count = 0
        self.notify = notify

    def __call__(self, state: FillState, bank: Bank):
        keep_going = self.check_state(state, bank)
        self.count += 1
        if keep_going != _CONTINUE:
            result = _STOP
        elif self.is_over_threshold():
            result = _STOP
        else:
            result = _CONTINUE
        if self.notify is not None:
            self.notify(self, state, bank, result)
        return result

    def check_state(self, state: FillState, bank: Bank):
        raise NotImplementedError("subclass must implement")

    def is_over_threshold(self):
        return self.threshold is not None and self.count >= self.threshold

    def value(self):
        raise NotImplementedError("subclass must implement")

class FirstCompleteListener(FillListener):

    def __init__(self, threshold: int=None):
        super().__init__(threshold)
        self.completed = None

    def check_state(self, state: FillState, bank: Bank):
        if state.is_complete():
            self.completed = state
            return _STOP
        return _CONTINUE

    def value(self):
        return self.completed


class AllCompleteListener(FillListener):

    def __init__(self, threshold: int=None):
        super().__init__(threshold)
        self.completed = set()

    def value(self):
        return self.completed

    def check_state(self, state: FillState, bank: Bank):
        if state.is_complete():
            self.completed.add(state)
        return _CONTINUE


class FillStateNode(object):

    def __init__(self, state: FillState, parent: 'FillStateNode'=None):
        self.state = state
        self.parent = parent
        self.known_unfillable = False


class Filler(object):

    def __init__(self, bank: Bank):
        self.bank = bank

    def fill(self, state: FillState, listener: FillListener=None) -> FillListener:
        listener = listener or FirstCompleteListener()
        self._fill(FillStateNode(state), listener)
        return listener

    def _fill(self, node: FillStateNode, listener: Callable[[FillState, Bank], bool]) -> bool:
        if listener(node.state, self.bank) == _STOP:
            return _STOP
        action_flag = _CONTINUE
        for template_idx in node.state.unfilled():
            for legend_updates in self.bank.suggest_updates(node.state, template_idx):
                new_state = node.state.advance_unchecked(legend_updates)
                new_node = FillStateNode(new_state, node)
                continue_now =  self._fill(new_node, listener)
                if continue_now != _CONTINUE:
                    action_flag = _STOP
                    break
            if action_flag == _STOP:
                break
        return action_flag

