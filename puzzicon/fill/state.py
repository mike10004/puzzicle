#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from collections import defaultdict
from typing import NamedTuple
from typing import Tuple, List, Dict, Optional, Iterator, Callable

import puzzicon.grid
from puzzicon.fill import Answer, Suggestion, Template
from puzzicon.grid import GridModel

_log = logging.getLogger(__name__)


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
            for spot in filter(lambda s: not Template.is_value_defined(s), answer.content):
                crosses_dict[spot].append(a_idx)
        # List elements are not yet of the correct type, but they will be eventually
        # noinspection PyTypeChecker
        crosses: List[Tuple[int, ...]] = [None] * (grid_size[0] * grid_size[1])
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
        newly_defined_answer_indexes = set()
        for a_idx, new_answer in suggestion.new_entries.items():
            answer = self.answers[a_idx]
            # is this always true based on how we get the Suggestion in the first place?
            if not answer.is_all_defined() and new_answer.is_all_defined():
                    answers[a_idx] = new_answer
                    newly_defined_answer_indexes.add(a_idx)
                    rendering = ''.join(new_answer.content)
                    used[a_idx] = rendering
                    num_incomplete -= 1
        for grid_idx in suggestion.legend_updates:
            crossing_answer_indexes = self.crosses[grid_idx]
            pass
            for a_idx in crossing_answer_indexes:
                pass
                if a_idx not in newly_defined_answer_indexes:
                    changed_answer = answers[a_idx].update(suggestion.legend_updates)
                    answers[a_idx] = changed_answer
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

    def list_new_entries_using_updates(self, legend_updates: Dict[int, str],
                                       answer_idx: int,
                                       include_answer_idx: bool,
                                       evaluator: Optional[Callable[[Answer], bool]]=None) -> Optional[Dict[int, Answer]]:
        """
        Return a dictionary mapping answer indexes to new complete answers.

        The answer corresponding to the given answer index is included
        in the set of updates only if include_template_idx is true.

        If an evaluator is provided, it must accept an Answer parameter argument and
        return False if the word is not valid. This aborts the process of listing
        new entries and returns early with None.

        @param legend_updates: map of grid index to cell content
        @param answer_idx: the answer index
        @param include_answer_idx: true iff Answer corresponding to answer_idx is to be included
        @param evaluator: callable accepting an Answer object
        @return: map of answer index to new Answer object
        """
        # noinspection PyTypeChecker
        updated_answers: Dict[int, Answer] = {}
        for grid_index in legend_updates:
            crossing_answer_indexes = self.crosses[grid_index]
            for a_idx in crossing_answer_indexes:
                if include_answer_idx or (a_idx != answer_idx):
                    answer: Answer = self.answers[a_idx]
                    another_entry: Answer = answer.update(legend_updates)
                    if evaluator is not None and (not evaluator(another_entry)):
                        return None
                    if another_entry.content.is_complete():
                        # a complete Template is effectively a WordTuple, so we
                        # can ignore this type mismatch.
                        # noinspection PyTypeChecker
                        updated_answers[a_idx] = another_entry
        return updated_answers


