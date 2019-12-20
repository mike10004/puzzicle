#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from typing import NamedTuple, Collection, FrozenSet, Union
from typing import Tuple, Sequence, Dict, Optional

_log = logging.getLogger(__name__)
_VALUE = 1
_BLANK = '_'
_EMPTY_SET = frozenset()


class WordTuple(Tuple[str, ...]):

    def length(self):
        return len(self)

    # noinspection PyMethodMayBeStatic
    def is_complete(self) -> bool:
        return True


class Pattern(Tuple[Optional[str], ...]):

    def length(self):
        return len(self)


class Template(Tuple[Union[int, str], ...]):

    _strength: int = None

    def __new__(cls, seq, **kwargs) -> 'Template':
        instance = tuple.__new__(Template, seq)
        t_strength =  kwargs.get('strength', None)
        if t_strength is None:
            t_strength = 0
            for x in seq:
                if Template.is_value_defined(x):
                    t_strength += 1
        instance._strength = t_strength
        return instance

    def length(self) -> int:
        return len(self)

    def strength(self) -> int:
        return self._strength

    @staticmethod
    def is_value_defined_at(instance: 'Template', index: int):
        return Template.is_value_defined(instance[index])

    @staticmethod
    def is_value_defined(value: Union[int, str]):
        return not isinstance(value, int)

    def is_defined_at(self, index: int):
        return Template.is_value_defined_at(self, index)

    def is_complete(self) -> bool:
        return self._strength == len(self)


class BankItem(NamedTuple):

    tableau: WordTuple
    rendering: str
    constituents: FrozenSet[str]

    @staticmethod
    def create(tableau: WordTuple, constituents: Optional[Collection[str]]=None):
        rendering = ''.join(tableau)
        if constituents is None:
            constituents = frozenset({rendering})
        constituents = frozenset(constituents)
        return BankItem(tableau, rendering, constituents)

    @staticmethod
    def from_word(word: str, constituents: Optional[str]=None):
        return BankItem.create(WordTuple(word), constituents)

    def length(self):
        return len(self.tableau)

    def __str__(self):
        return f"BankItem<{self.tableau}>"


class Answer(NamedTuple):

    content: Template
    pattern: Pattern
    strength: int

    @staticmethod
    def define(content: Sequence[Union[int, str]]) -> 'Answer':
        content = Template(content)
        pattern = Pattern([(x if Template.is_value_defined(x) else None) for x in content])
        strength = content.strength()
        # noinspection PyTypeChecker
        return Answer(content, pattern, strength)

    def normalized_strength(self) -> float:
        return self.strength / self.length()

    def render(self, blank=_BLANK) -> str:
        return ''.join([blank if p is None else p for p in self.pattern])

    def is_defined(self, index: int) -> bool:
        """Checks whether the grid index at the given content index is already mapped to a letter."""
        return self.pattern[index] is not None

    def length(self) -> int:
        return self.pattern.length()

    def is_all_defined(self) -> bool:
        return self.strength == self.length()

    def is_undefined_at(self, index):
        return not self.content.is_defined_at(index)

    def update(self, legend_updates: Dict[int, str]) -> 'Answer':
        num_unknown = 0
        num_updates = 0
        template_src = []
        pattern_src = []
        for i in range(self.length()):
            spot = self.content[i]
            if self.content.is_defined_at(i):
                template_src.append(spot)
                pattern_src.append(spot)
            else:
                p_val = legend_updates.get(spot, None)
                if p_val is None:
                    t_val = spot
                    num_unknown += 1
                else:
                    t_val = p_val
                    num_updates += 1
                template_src.append(t_val)
                pattern_src.append(p_val)
        pattern = Pattern(pattern_src)
        strength = pattern.length() - num_unknown
        content = Template(template_src, strength=strength)
        return Answer(content, pattern, strength)

    def to_updates(self, entry: BankItem) -> Dict[int, str]:
        """
        Returns a map of grid indexes to cell content that represents each new mapping
        forced by the given entry.
        @param entry: the entry
        @return: a dictionary
        """
        assert self.length() == entry.length()
        legend_updates: Dict[int, str] = {}
        for i in range(entry.length()):
            if not self.is_defined(i):
                k, v = self.content[i], entry.tableau[i]
                legend_updates[k] = v
        return legend_updates



def _sort_and_check_duplicates(items: list) -> bool:
    items.sort()
    for i in range(1, len(items)):
        if items[i - 1] == items[i]:
            return True
    return False


class Suggestion(object):

    def __init__(self, legend_updates: Dict[int, str], new_entries: Dict[int, Answer], rank: float=None):
        """
        Construct an instance.
        @param legend_updates: mapping of grid index to square value
        @param new_entries: mapping of answer index to bank words
        """
        self.legend_updates = legend_updates
        assert legend_updates, "suggestion must contain legend updates"
        self.new_entries = new_entries
        assert new_entries, "suggestion must contain at least one new entry"
        self.rank = rank

