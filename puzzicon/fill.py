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


_log = logging.getLogger(__name__)
_VALUE = 1
_BLANK = '_'
_EMPTY_SET = frozenset()


class WordTuple(Tuple[str, ...]):

    def length(self):
        return len(self)

class Pattern(Tuple[Optional[str], ...]):

    def length(self):
        return len(self)


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


class Template(Tuple[Union[int, str], ...]):
    pass

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

    def render_after(self, legend_updates: Dict[int, str]) -> Union[Pattern, WordTuple]:
        num_unknown = 0
        letters = []
        for spot in self.content:
            if isinstance(spot, int):
                val = legend_updates.get(spot, None)
                letters.append(val)
                num_unknown += (0 if val is None else 1)
            else:
                letters.append(spot)
        return WordTuple(letters) if num_unknown == 0 else Pattern(letters)



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


class FillState(NamedTuple):

    answers: Tuple[Answer, ...]
    crosses: Tuple[Tuple[int, ...]]     # maps each grid index to all indexes of answers that contain the grid index
    used: Tuple[Optional[str], ...]     # maps each answer index to rendering of that answer, if complete, or else None
    num_incomplete: int                 # number of incomplete answers remaining

    # deprecated: use from_answers instead
    @staticmethod
    def from_templates(templates: Tuple[Answer, ...], grid_size: Tuple[int, int]) -> 'FillState':
        return FillState.from_answers(templates, grid_size)

    @staticmethod
    def from_answers(answers: Tuple[Answer, ...], grid_size: Tuple[int, int]) -> 'FillState':
        crosses_dict = defaultdict(list)
        for a_idx, answer in enumerate(answers):
            for spot in filter(lambda s: isinstance(s, int), answer.content):
                crosses_dict[spot].append(a_idx)
        crosses = [None] * (grid_size[0] * grid_size[1])
        for grid_idx in crosses_dict:
            crosses[grid_idx] = tuple(crosses_dict[grid_idx])
        for i in range(len(crosses)):
            if crosses[i] is None:
                crosses[i] = tuple()
        used = [None if not a.is_all_defined() else ''.join(a.pattern) for a in answers]
        num_incomplete = sum([1 if u is None else 0 for u in used])
        return FillState(tuple(answers), tuple(crosses), tuple(used), num_incomplete)

    def is_complete(self):
        return self.num_incomplete == 0

    def unfilled(self) -> Iterator[int]:
        """Return a generator of indexes of answers that are not completely filled."""
        return map(lambda pair: pair[0], filter(lambda pair: pair[1] is None, enumerate(self.used)))

    def advance_unchecked(self, suggestion: Suggestion) -> 'FillState':
        answers = list(self.answers)
        used = list(self.used)  # some elements may go from None -> str
        num_incomplete = self.num_incomplete  # decreases by number of new strings in 'used'
        for a_idx in suggestion.new_entries:
            answer = self.answers[a_idx]
            # is this always true based on how we get the Suggestion in the first place?
            if not answer.is_all_defined() and answer.is_all_defined_after(suggestion.legend_updates):
                wtuple: WordTuple = answer.render_after(suggestion.legend_updates)
                answers[a_idx] = Answer.define(wtuple)
                rendering = ''.join(wtuple)
                used[a_idx] = rendering
                num_incomplete -= 1
        if num_incomplete == self.num_incomplete:
            # avoid re-tupling used list if nothing changed
            return FillState(tuple(answers), self.crosses, self.used, num_incomplete)
        else:
            return FillState(tuple(answers), self.crosses, tuple(used), num_incomplete)

    @staticmethod
    def from_grid(grid: GridModel) -> 'FillState':
        answers: List[Answer] = []
        for entry in grid.entries():
            indexes = []
            for square in entry.squares:
                index = grid.get_index(square)
                indexes.append(index)
            answers.append(Answer.define(indexes))
        return FillState.from_answers(tuple(answers), grid.dims())

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

    def to_legend_updates_dict(self, entry: BankItem, answer_idx: int) -> Dict[int, str]:
        """
        Shows what new grid index to letter mappings would be defined if a template were to be filled by the given entry.
        """
        answer: Answer = self.answers[answer_idx]
        assert answer.length() == entry.length(), f"entry '{entry}' does not fit in answer {answer.pattern}"
        legend_updates: Dict[int, str] = {}
        for i in range(entry.length()):
            if not answer.is_defined(i):
                k, v = answer.content[i], entry.tableau[i]
                legend_updates[k] = v
        return legend_updates

    def list_new_entries_using_updates(self, legend_updates: Dict[int, str],
                                       template_idx: int,
                                       include_template_idx: bool,
                                       evaluator: Optional[Callable[[WordTuple], bool]]=None) -> Optional[Dict[int, WordTuple]]:
        """
        Return a dictionary mapping answer indexes to word-tuples that includes only
        those mappings where the word-tuple becomes completed by the given legend updates.

        The answer corresponding to the given answer index is included
        in the set of updates only if include_template_idx is true.

        If an evaluator is provided, it must accept a word-tuple as an argument and
        return False if the word is not valid. This aborts the process of listing
        new entries and returns early with None.
        """
        # noinspection PyTypeChecker
        updated_answers: Dict[int, WordTuple] = {}
        for grid_index in legend_updates:
            crossing_answer_indexes = self.crosses[grid_index]
            for a_idx in crossing_answer_indexes:
                if include_template_idx or (a_idx != template_idx):
                    answer: Answer = self.answers[a_idx]
                    if answer.is_all_defined_after(legend_updates):
                        another_entry = answer.render_after(legend_updates)
                        if evaluator is not None and (not evaluator(another_entry)):
                            return None
                        # because render_after returns an effective WordTuple when is_all_defined_after returns True,
                        # we can ignore this type mismatch
                        # noinspection PyTypeChecker
                        updated_answers[a_idx] = another_entry
        return updated_answers


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


class Bank(NamedTuple):

    deposits: FrozenSet[BankItem]
    tableaus: FrozenSet[WordTuple]
    by_pattern: Dict[Pattern, List[BankItem]] = {}

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
            return filter(lambda entry: Bank.matches(entry, pattern), self)

    def suggest_updates(self, state: FillState, template_idx: int) -> Iterator[Suggestion]:
        this_bank = self
        answer: Answer = state.answers[template_idx]
        pattern = answer.pattern
        matches: Iterator[BankItem] = self.filter(pattern)
        unused: Iterator[BankItem] = filter(Bank.not_already_used_predicate(state.used), matches)
        updates_iter = map(lambda entry: state.to_legend_updates_dict(entry, template_idx), unused)
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

    def __init__(self, bank: Bank, tracer: Optional[Callable[[FillStateNode], Any]]=None):
        self.bank = bank
        self.tracer = tracer

    def fill(self, state: FillState, listener: FillListener=None) -> FillListener:
        listener = listener or FirstCompleteListener()
        self._fill(FillStateNode(state), listener)
        return listener

    def _fill(self, node: FillStateNode, listener: Callable[[FillState, Bank], bool]) -> bool:
        if self.tracer is not None:
            self.tracer(node)
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

