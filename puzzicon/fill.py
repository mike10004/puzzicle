#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from puzzicon import Puzzeme
import puzzicon.grid
from puzzicon.grid import GridModel
from typing import Tuple, List, Sequence, Dict, Optional, Iterator, Callable, FrozenSet

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

    def render(self, indexes):
        return ''.join(map(lambda val: _BLANK if val is None else val, map(lambda index: self.get(index), indexes)))

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

_EMPTY_SET = frozenset()


def _sort_and_check_duplicates(items: list):
    items.sort()
    for i in range(1, len(items)):
        if items[i - 1] == items[i]:
            return True
    return False


class FillState(tuple):

    templates, legend, used = None, None, None
    previous = None

    def __new__(cls, templates: Tuple[Tuple[int, ...]], legend: Legend, used: FrozenSet[str]=_EMPTY_SET, known_incorrect: bool=False):
        assert isinstance(templates, tuple)
        assert isinstance(legend, Legend)
        assert isinstance(used, frozenset)
        # noinspection PyTypeChecker
        instance = super(FillState, cls).__new__(cls, [templates, legend, used, known_incorrect])
        instance.templates = templates
        instance.legend = legend
        instance.used = used
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
        for template in self.templates:
            if self.is_template_filled(template):
                yield self.legend.render(template)

    def unfilled(self) -> Iterator[int]:
        """Return a generator of indexes of templates that are not completely filled."""
        for i, template in enumerate(self.templates):
            if not self.is_template_filled(template):
                yield i

    def advance(self, legend_updates: Dict[int, str]) -> 'FillState':
        new_legend = self.legend.redefine(legend_updates)
        more_entries = []
        for index in legend_updates:
            for template in filter(lambda t: index in t, self.templates):
                if new_legend.is_all_defined(template):
                    another_entry = new_legend.render(template)
                    more_entries.append(another_entry)
        used = frozenset(list(self.used) + more_entries)
        has_dupes = len(used) < (len(self.used) + len(more_entries))
        state = FillState(self.templates, new_legend, used, has_dupes)
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
        return FillState(tuple(templates), Legend.empty(), frozenset())

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



class Bank(tuple):

    def __new__(cls, entries: Sequence[str]):
        # noinspection PyTypeChecker
        instance = super(Bank, cls).__new__(cls, entries)
        return instance

    @staticmethod
    def matches(entry, pattern):
        if len(entry) != len(pattern):
            return False
        for i in range(len(pattern)):
            if pattern[i] is not None:
                if pattern[i] != entry[i]:
                    return False
        return True

    def filter(self, pattern: Sequence[Optional[str]]) -> Iterator[str]:
        return filter(lambda entry: Bank.matches(entry, pattern), self)

    def suggest(self, state: FillState, template_i: int) -> Iterator[str]:
        indexes = state.templates[template_i]
        pattern = [state.legend.get(index) for index in indexes]
        def not_already_used(entry: str):
            return entry not in state.used
        return filter(not_already_used, self.filter(pattern))

    def is_correct(self, state: FillState):
        renderings = state.render_filled()
        used = set()
        for rendering in renderings:
            if not rendering in self:
                return False
            if rendering in used:
                return False
            used.add(rendering)
        return True


_CONTINUE = False
_STOP = True

class FillListener(object):

    def __init__(self, threshold: int=None):
        self.threshold = threshold
        self.count = 0

    def __call__(self, state: FillState, bank: Bank):
        keep_going = self.check_state(state, bank)
        self.count += 1
        if keep_going != _CONTINUE:
            return _STOP
        if self.is_over_threshold():
            return _STOP
        return _CONTINUE

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
