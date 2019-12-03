#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from puzzicon import Puzzeme
import puzzicon.grid
from collections import defaultdict
import itertools
from puzzicon.grid import GridModel
from typing import Tuple, List, Sequence, Dict, Optional, Iterator, Callable, FrozenSet, Collection

_VALUE = 1
_BLANK = '_'

class Legend(tuple):

    def __new__(cls, values_list: Sequence[str]):
        # noinspection PyTypeChecker
        return super(Legend, cls).__new__(cls, values_list)

    def has_value(self, index: int):
        try:
            return self[index] is not None
        except IndexError:
            return False

    def get(self, index):
        try:
            return self[index]
        except IndexError:
            return None

    # noinspection PyTypeChecker
    @staticmethod
    def from_dict(values_dict: Dict[int, str]):
        max_index = max(values_dict.keys())
        if max_index == 0:
            return Legend([values_dict[0]])
        values_list = [None] * (max_index + 1)
        for k, v in values_dict.items():
            values_list[k] = v
        return Legend(values_list)

    def render(self, indexes: Sequence[int]):
        return ''.join(map(lambda val: _BLANK if val is None else val, map(lambda index: self.get(index), indexes)))

    def render_after(self, indexes: Sequence[int], updates: Dict[int, str]):
        def get_value(index: int):
            value = self.get(index)
            if value is None:
                value = updates.get(index, None)
            if value is None:
                value = _BLANK
            return value
        return ''.join(map(get_value, indexes))

    def redefine(self, definitions: Dict[int, str]):
        mutable = list(self)
        for i in range(len(mutable), max(definitions.keys()) + 1):
            mutable.append(None)
        for k, v in definitions.items():
            mutable[k] = v
        return Legend(mutable)

    @staticmethod
    def empty():
        return Legend([])

    def is_all_defined(self, indexes: Sequence[int]):
        for index in indexes:
            if not self.has_value(index):
                return False
        return True

    def is_all_defined_after(self, indexes: Sequence[int], legend_updates: Dict[int, str]):
        """Tests whether each index is defined in either this legend or a set of updates."""
        for index in indexes:
            if not self.has_value(index) and index not in legend_updates:
                return False
        return True

_EMPTY_SET = frozenset()


def _sort_and_check_duplicates(items: list):
    items.sort()
    for i in range(1, len(items)):
        if items[i - 1] == items[i]:
            return True
    return False


def _NOT_NONE(x):
    return x is not None


class FillState(tuple):

    templates, legend, used = None, None, None
    previous = None

    def __new__(cls, templates: Tuple[Tuple[int, ...]], legend: Legend, used: Tuple[Optional[str], ...]=None, known_incorrect: bool=False):
        assert isinstance(templates, tuple)
        assert isinstance(legend, Legend)
        assert used is None or isinstance(used, tuple), "used has wrong type: {}".format(used)
        # noinspection PyTypeChecker
        instance = super(FillState, cls).__new__(cls, [templates, legend, used, known_incorrect])
        instance.templates = templates
        instance.legend = legend
        instance.used = tuple([None] * len(templates)) if used is None else used
        instance.known_incorrect = known_incorrect
        return instance

    def is_template_filled(self, template: Tuple[int, ...]):
        for index in template:
            if not self.legend.has_value(index):
                return False
        return True

    def is_complete(self):
        # could make this a set first at the expense of memory, but it's only max twice as big
        for template in self.templates:
            if not self.is_template_filled(template):
                return False
        return True

    def render_filled(self) -> Iterator[str]:
        return filter(_NOT_NONE, self.used)

    def unfilled(self) -> Iterator[int]:
        """Return a generator of indexes of templates that are not completely filled."""
        for i, entry in enumerate(self.used):
        #     if not self.is_template_filled(template):
        #         yield i
            if entry is None:
                yield i

    def _list_new_entries(self, new_legend: Legend, legend_updates: Dict[int, str]) -> Dict[int, str]:
        """Return a map of template index to completed entry."""
        more_entries = {}
        updated_templates = set()
        for ti, template in enumerate(self.templates):
            for index in legend_updates:
                if index in template:
                    updated_templates.add((ti, template))
        for t_idx, template in updated_templates:
            if new_legend.is_all_defined(template):
                another_entry = new_legend.render(template)
                more_entries[t_idx] = another_entry
        return more_entries

    def advance(self, legend_updates: Dict[int, str]) -> 'FillState':
        new_legend = self.legend.redefine(legend_updates)
        more_entries = self._list_new_entries(new_legend, legend_updates)
        used: List[Optional[str]] = list(self.used)
        for template_idx, new_entry in more_entries.items():
            used[template_idx] = new_entry
        used_not_none = list(filter(lambda x: x is not None, used))
        has_dupes = _sort_and_check_duplicates(used_not_none)
        # has_dupes = len(used) < (len(self.used) + len(more_entries))
        state = FillState(self.templates, new_legend, tuple(used), has_dupes)
        state.previous = self
        return state

    @staticmethod
    def from_grid(grid: GridModel) -> 'FillState':
        templates = []
        for entry in grid.entries():
            indexes = []
            for square in entry.squares:
                index = grid.get_index(square)
                indexes.append(index)
            templates.append(tuple(indexes))
        return FillState(tuple(templates), Legend.empty())

    # noinspection PyProtectedMember
    def render(self, grid: GridModel, newline="\n", none_val='_', dark=puzzicon.grid._DARK) -> str:
        rows = []
        for r in range(grid.num_rows):
            row = []
            for c in range(grid.num_cols):
                s = grid.square(r, c)
                if s.dark():
                    row.append(dark)
                else:
                    i = grid.get_index(s)
                    v = self.legend.get(i)
                    row.append(none_val if v is None else v)
            rows.append(''.join(row))
        return newline.join(rows)

def _powerset(iterable):
    """powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)"""
    s = list(iterable)
    return itertools.chain.from_iterable(itertools.combinations(s, r) for r in range(len(s)+1))

class Bank(tuple):

    word_set = None
    by_pattern = None

    def __new__(cls, entries: Sequence[str], pattern_registry_cap=9):
        word_set = frozenset(entries)
        # noinspection PyTypeChecker
        instance = super(Bank, cls).__new__(cls, [word_set])
        instance.word_set = word_set
        instance.by_pattern = defaultdict(list)
        for entry in entries:
            if len(entry) <= pattern_registry_cap:
                patterns = Bank.patterns(entry)
                for pattern in patterns:
                    instance.by_pattern[pattern].append(entry)
        return instance

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

    def suggest(self, state: FillState, template_i: int) -> Iterator[str]:
        indexes = state.templates[template_i]
        pattern = [state.legend.get(index) for index in indexes]
        matches = self.filter(pattern)
        unused = filter(Bank.not_already_used_predicate(state.used), matches)
        def stays_correct(entry):
            # we could optimize by not generating this entire list before checking each one
            new_entries = Bank.list_new_entries(entry, template_i, state)
            new_entries_set = set()
            for new_entry in new_entries.values():
                if (new_entry in new_entries_set) or not self.is_valid_new_entry(state, new_entry):
                    return False
                new_entries_set.add(new_entry)
            return True
        return filter(stays_correct, unused)

    @staticmethod
    def not_already_used_predicate(already_used: Collection[str]) -> Callable[[str], bool]:
        def not_already_used(entry):
            return entry not in already_used
        return not_already_used

    def is_valid_new_entry(self, state: FillState, entry: str):
        return entry not in state.used and self.has_word(entry)

    @staticmethod
    def list_new_entries(entry: str, template_idx: int, state: FillState) -> Dict[int, str]:
        """
        Return a map of template index to completed entry for all filled
        templates *except* the template corresponding to the given index.
        """
        template = state.templates[template_idx]
        legend_updates: Dict[int, str] = {}
        for i in range(len(entry)):
            k, v = template[i], entry[i]
            if state.legend.get(k) != v:
                legend_updates[k] = v
        more_entries = {}
        updated_templates = set()
        for t_idx, template in enumerate(state.templates):
            if t_idx != template_idx:
                for index in legend_updates:
                    if index in template:
                        updated_templates.add((t_idx, template))
        for t_idx, template in updated_templates:
            if state.legend.is_all_defined_after(template, legend_updates):
                another_entry = state.legend.render_after(template, legend_updates)
                more_entries[t_idx] = another_entry
        return more_entries

    def has_word(self, entry: str):
        return entry in self.word_set

    def is_correct(self, state: FillState):
        if state.known_incorrect:
            return False
        for rendering in state.used:
            if not self.has_word(rendering):  # can we short-circuit this in suggest function?
                return False
        return True

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
        if state.is_complete() and bank.is_correct(state):
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
        if state.is_complete() and bank.is_correct(state):
            self.completed.add(state)
        return _CONTINUE


class Filler(object):

    def __init__(self, bank: Bank):
        self.bank = bank

    def fill(self, state: FillState, listener: FillListener=None) -> FillListener:
        listener = listener or FirstCompleteListener()
        self._fill(state, listener)
        return listener

    def _fill(self, state: FillState, listener: Callable[[FillState, Bank], bool]) -> bool:
        if listener(state, self.bank) == _STOP:
            return _STOP
        action_flag = _CONTINUE
        for template_i in state.unfilled():
            template = state.templates[template_i]
            for entry in self.bank.suggest(state, template_i):
                updates = {}
                for i in range(len(entry)):
                    position = template[i]
                    if position not in state.legend:
                        updates[position] = entry[i]
                new_state = state.advance(updates)
                continue_now =  self._fill(new_state, listener)
                if continue_now != _CONTINUE:
                    action_flag = _STOP
                    break
            if action_flag == _STOP:
                break
        return action_flag

