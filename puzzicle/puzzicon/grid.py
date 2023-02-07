#!/usr/bin/env python3

import math
from typing import List, Tuple, NamedTuple
import itertools


_ACROSS = 'across'
_DOWN = 'down'
_DARK = '.'


class Square(NamedTuple):

    row: int
    col: int
    index: int
    value: str = None

    def dark(self) -> bool:
        return self.value == _DARK

    def __eq__(self, other):
        return isinstance(other, Square) and self.row == other.row and self.col == other.col and self.value == other.value

    def __str__(self):
        return "({}, {}, {}, {})".format(self.row, self.col, self.index, repr(self.value))


class Location(NamedTuple):

    direction: str
    number: int
    row_index: int
    col_index: int

    @staticmethod
    def across(number, row_index, col_index):
        return Location(_ACROSS, number, row_index, col_index)

    @staticmethod
    def down(number, row_index, col_index):
        return Location(_DOWN, number, row_index, col_index)


class Entry(object):

    def __init__(self, location: Location, squares: List[Square]):
        self.location = location
        self.squares = squares

    def __str__(self) -> str:
        return "Entry<at={};{}>".format(self.location, self.squares)


class GridModel(object):

    def __init__(self, rows: List[List[Square]]):
        self.rows = rows
        self.num_rows = len(rows)
        self.num_cols = len(rows[0]) if len(rows) > 0 else 0

    @staticmethod
    def determine_dims(grid_chars: str) -> Tuple[int, int]:
        num_squares = len(list(filter(lambda ch: ch not in "\r\n\t", grid_chars)))
        dim = math.sqrt(num_squares)
        assert round(dim) == dim, "expect puzzle to be a square"
        return int(dim), int(dim)

    def dims(self) -> Tuple[int, int]:
        return self.num_rows, self.num_cols

    def get_index(self, square: Square) -> int:
        return square.row * self.num_cols + square.col

    def to_text(self, newline="") -> str:
        cells = []
        for row in self.rows:
            for cell in row:
                cells.append(' ' if (cell.value is None or cell.value == '') else cell.value)
        return newline.join(cells) + newline

    def square(self, row: int, col: int) -> Square:
        return self.rows[row][col]

    def value(self, row: int, col: int) -> str:
        return self.square(row, col).value

    def is_across(self, r, c) -> bool:
        my_val = self.value(r, c)
        if my_val == '.':
            return False
        if c == 0:
            return True
        left_val = self.value(r, c - 1)
        try:
            right_val = self.value(r, c + 1)
        except IndexError:
            right_val = '.'
        return left_val == '.' and right_val != '.'

    def is_down(self, r, c) -> bool:
        my_val = self.value(r, c)
        if my_val == '.':
            return False
        if r == 0:
            return True
        up_val = self.value(r - 1, c)
        try:
            down_val = self.value(r + 1, c)
        except IndexError:
            down_val = '.'
        return up_val == '.' and down_val != '.'

    @classmethod
    def build(cls, grid_chars: str) -> 'GridModel':
        nrows, ncols = GridModel.determine_dims(grid_chars)
        rows = []
        for r in range(nrows):
            cols = []
            for c in range(ncols):
                val = grid_chars[r * ncols + c]
                cols.append(val)
            rows.append(cols)
        grows = []
        for r in range(len(rows)):
            row = rows[r]
            grow = []
            for c in range(len(row)):
                value = rows[r][c]
                index = r * ncols + c
                cell = Square(r, c, index, value)
                grow.append(cell)
            grows.append(grow)
        return GridModel(grows)

    def until_dead_across(self, row: int, col: int) -> List[Square]:
        return self.until_dead(row, col, 0, 1)

    def until_dead_down(self, row: int, col: int) -> List[Square]:
        return self.until_dead(row, col, 1, 0)

    def until_dead(self, row: int, col: int, row_delta: int, col_delta: int) -> List[Square]:
        assert row_delta != 0 or col_delta != 0
        squares = []
        dead = False
        while not dead:
            try:
                square = self.rows[row][col]
                squares.append(square)
                row += row_delta
                col += col_delta
                dead = self.square(row, col).dark()
            except IndexError:
                dead = True
        return squares

    def entries(self) -> List[Entry]:
        number = 1
        entries = []
        for r, c in itertools.product(range(self.num_rows), range(self.num_cols)):
            either = False
            if self.is_across(r, c):
                squares = self.until_dead_across(r, c)
                entries.append(Entry(Location(_ACROSS, number, r, c), squares))
                either = True
            if self.is_down(r, c):
                squares = self.until_dead_down(r, c)
                entries.append(Entry(Location(_DOWN, number, r, c), squares))
                either = True
            if either:
                number += 1
        return entries

    def __str__(self):
        return "GridModel<{}x{}>".format(self.num_rows, self.num_cols)

