#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from puzzicon import Puzzeme
from puzzicon.grid import GridModel
from typing import Tuple, List, Sequence, Dict, Optional, Iterator, Callable

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

class FillState(tuple):

    templates, legend = None, None

    def __new__(cls, templates: Tuple[Tuple[int, ...]], legend: Legend):
        # noinspection PyTypeChecker
        instance = super(FillState, cls).__new__(cls, [templates, legend])
        instance.templates = templates
        instance.legend = legend
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

    def advance(self, new_legend: Legend) -> 'FillState':
        return FillState(self.templates, new_legend)

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
        already_used = set(state.render_filled())
        def not_already_used(entry: str):
            return entry not in already_used
        return filter(not_already_used, self.filter(pattern))

    def is_correct(self, state: FillState):
        for template in state.templates:
            rendering = state.legend.render(template)
            if not rendering in self:
                return False
        return True


def create_template_list(grid: GridModel) -> Tuple[Tuple[int, ...]]:
    templates = []
    for entry in grid.entries():
        indexes = []
        for square in entry.squares:
            index = grid.get_index(square)
            indexes.append(index)
        templates.append(tuple(indexes))
    return tuple(templates)


_CONTINUE = False
_STOP = True

class FillListener(object):

    def __init__(self, threshold: int=None):
        self.threshold = threshold
        self.count = 0

    def __call__(self, state: FillState, bank: Bank):
        keep_going = self.check_state(state, bank)
        if not keep_going:
            return _STOP
        self._increment()
        return self.is_over_threshold()

    def check_state(self, state: FillState, bank: Bank):
        raise NotImplementedError("subclass must implement")

    def _increment(self) -> int:
        self.count += 1
        return self.count

    def is_over_threshold(self):
        return self.threshold is not None and self.count > self.threshold

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
        self.completed = []

    def value(self):
        return self.completed

    def check_state(self, state: FillState, bank: Bank):
        if state.is_complete() and bank.is_correct(state):
            self.completed.append(state)
        return False


class Filler(object):

    def __init__(self, bank: Bank):
        self.bank = bank

    def fill(self, state: FillState, listener: FillListener=None) -> FillListener:
        listener = listener or FirstCompleteListener()
        self._fill(state, listener)
        return listener

    def _fill(self, state: FillState, listener: Callable[[FillState, Bank], bool]) -> bool:
        if not listener(state, self.bank):
            return False
        action_flag = _CONTINUE
        for template_i in state.unfilled():
            template = state.templates[template_i]
            for entry in self.bank.suggest(state, template_i):
                updates = {}
                for i in range(len(entry)):
                    updates[template[i]] = entry[i]
                legend = state.legend.redefine(updates)
                new_state = state.advance(legend)
                continue_now = self._fill(new_state, listener)
                if continue_now != _CONTINUE:
                    action_flag = _STOP
                    break
        return action_flag

