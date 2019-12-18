#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Tuple, List, Sequence, Dict, Optional, Iterator, Callable, Any
from typing import NamedTuple, Collection, FrozenSet, Union, Iterable
import logging


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
        strength =  kwargs.get('strength', None)
        if strength is None:
            strength = 0
            for x in seq:
                if not isinstance(x, int):
                    strength += 1
        instance._strength = strength
        return instance

    def length(self):
        return len(self)

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
        pattern = Pattern([(None if isinstance(x, int) else x) for x in content])
        strength = sum([0 if p is None else 1 for p in pattern])
        # noinspection PyTypeChecker
        return Answer(content, pattern, strength)

    def render(self, blank=_BLANK) -> str:
        return ''.join([blank if p is None else p for p in self.pattern])

    def is_defined(self, index: int) -> bool:
        """Checks whether the grid index at the given content index is already mapped to a letter."""
        return self.pattern[index] is not None

    def length(self) -> int:
        return self.pattern.length()

    def is_all_defined(self) -> bool:
        return self.strength == self.length()

    def is_all_defined_after(self, legend_updates: Dict[int, str]) -> bool:
        for spot in self.content:
            if isinstance(spot, int) and not spot in legend_updates:
                return False
        return True

    def render_content(self, legend_updates: Dict[int, str]) -> Union[Template, WordTuple]:
        """
        Produces a new template or word-tuple by updating this answer's template
        with the given mapping of grid indexes to cell content.
        @param legend_updates: map of grid indexes to cell content
        @return: a template, or a word-tuple if the template would have zero unknowns
        """
        num_unknown = 0
        num_updates = 0
        letters = []
        for spot in self.content:
            if isinstance(spot, int):
                val = legend_updates.get(spot, None)
                if val is None:
                    val = spot
                    num_unknown += 1
                else:
                    num_updates += 1
                letters.append(val)
            else:
                letters.append(spot)
        return WordTuple(letters) if num_unknown == 0 else Template(letters)

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

    def __init__(self, legend_updates: Dict[int, str], new_entries: Dict[int, WordTuple]):
        """
        Construct an instance.
        @param legend_updates: mapping of grid index to square value
        @param new_entries: mapping of answer index to bank words
        """
        self.legend_updates = legend_updates
        self.new_entries = new_entries
        assert new_entries, "suggestion must contain at least one new entry"

