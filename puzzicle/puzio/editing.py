#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import os.path
import puz
import csv
import math
from argparse import Namespace, ArgumentParser
from puzzicle import puzio
import typing
from typing import List, Tuple, Optional
from typing import TextIO
import logging


_log = logging.getLogger(__name__)


def _generate_filename(directory):
    stamp = puzio.timestamp()
    return os.path.join(directory, f"p{stamp}.puz")


def create_arg_parser() -> ArgumentParser:
    parser = ArgumentParser(description="""\
Create a .puz file from various input files.
""", epilog="""\
If --clues-pipes is not present, each line of clues text file must match the regex "([0-9]+)([AD])\.? (\S.*)\s*". 
""")
    parser.add_argument("output_pathname", nargs='?', metavar="FILE", help="output pathname; defaults to timestamped filename in $PWD")
    parser.add_argument("--input", metavar="FILE", help="input file in .puz or .qxw format")
    parser.add_argument("--clues", metavar="FILE", help="define clues source (text file)")
    parser.add_argument("-p", "--clues-pipes", action='store_true', help="specify that clues source is pipe-delimited")
    parser.add_argument("--solution", help="define solution; use '.' char for dark cells")
    parser.add_argument("--grid", help="define grid; use '.' for dark cells, anything for light")
    parser.add_argument("--title", metavar="STR", help="set title")
    parser.add_argument("--author", metavar="STR", help="set author")
    parser.add_argument("--shape", metavar="SPEC", default='square', help="set shape; value can be 'ROWSxCOLS' or 'square'")
    parser.add_argument("--copyright", metavar="STR", help="set copyright")
    parser.add_argument("--notes", metavar="STR", help="set notes")
    parser.add_argument("--log-level", choices=('INFO', 'DEBUG', 'WARNING', 'ERROR'), default='INFO', help="set log level")
    return parser


def _read_lines(ifile: TextIO, include_whitespace_only: bool=False, comment_leader: str=None):
    lines = []
    lines_with_endings = [line for line in ifile]
    for i, line in enumerate(lines_with_endings):
        if line[-1] == os.linesep:
            line = line[:-1]
        if comment_leader is not None and line.lstrip().startswith(comment_leader):
            continue
        if include_whitespace_only or line.strip():
            lines.append(line)
    return lines


class GridParser(object):

    def parse(self, ifile: TextIO) -> str:
        lines = _read_lines(ifile)
        # make all lines the same length
        max_len = max(map(len, lines))
        for i in range(len(lines)):
            line = lines[i]
            if len(line) < max_len:
                line = line + ''.join([' '] * (max_len - len(line)))
                lines[i] = line
        return ''.join(lines)


def _solution_to_grid(solution):
    return ''.join(['.' if ch == '.' else '-' for ch in solution])


# noinspection PyMethodMayBeStatic
class PuzzleCreator(object):

    allow_shapeless_grid = False

    def __init__(self, output_dir=None):
        self.output_dir = output_dir or os.getcwd()

    def determine_shape(self, grid: str, shape_arg: str) -> Optional[Tuple[int, int]]:
        shape_tokens = re.fullmatch(r'^(\d+)x(\d+)', shape_arg)
        if shape_tokens:
            return int(shape_tokens.group(1)), int(shape_tokens.group(2))
        if shape_arg != 'square':
            raise ValueError("invalid shape specification")
        if not grid:
            if not self.allow_shapeless_grid:
                _log.warning("could not determine grid shape")
            return None
        root = int(math.ceil(math.sqrt(len(grid))))
        return root, root

    def parse_input(self, input_arg: str) -> puz.Puzzle:
        if input_arg:
            if input_arg.lower().endswith('.qxw'):
                with open(input_arg, 'r') as ifile:
                    qxw_model = QxwParser().parse(ifile)
                puzzle = puz.Puzzle()
                puzzle.preamble = b''
                puzzle.solution = qxw_model.to_puz_solution()
                puzzle.scrambled_cksum = 0
            else:
                puzzle = puz.read(input_arg)
        else:
            puzzle = puz.Puzzle()
            puzzle.preamble = b''
        return puzzle

    def create(self, args: Namespace) -> Tuple[str, puz.Puzzle]:
        puzzle = self.parse_input(args.input)
        if args.clues:
            with open(args.clues, 'r') as ifile:
                clue_parser = ClueParser()
                puzzle.clues = [c.text for c in sorted(clue_parser.parse(ifile, args.clues))]
        grid = None
        if args.solution:
            with open(args.solution, 'r') as ifile:
                puzzle.solution = GridParser().parse(ifile)
        if puzzle.solution:
            grid = _solution_to_grid(puzzle.solution)
        if args.grid:
            with open(args.grid, 'r') as ifile:
                puzzle.fill = GridParser().parse(ifile)
                grid = puzzle.fill
        elif puzzle.solution:
            puzzle.fill = _solution_to_grid(puzzle.solution)
        if grid is not None and puzzle.solution:
            grid_darks = [i for i, ch in enumerate(grid) if ch == '.']
            soln_darks = [i for i, ch in enumerate(puzzle.solution) if ch == '.']
            if grid_darks != soln_darks:
                _log.warning("grid is incongruent with solution: %s and %s", grid_darks, soln_darks)
        shape = self.determine_shape(grid, args.shape)
        if shape is not None:
            puzzle.height, puzzle.width = shape
        for attrib in ('title', 'author', 'copyright', 'notes'):
            value = args.__dict__[attrib]
            if value is not None:
                puzzle.__setattr__(attrib, value)
        output_pathname = args.output_pathname or _generate_filename(self.output_dir)
        puzzle.save(output_pathname)
        return output_pathname, puzzle


class Clue(tuple):

    number, direction, text = None, None, None

    def __new__(cls, number, direction, text):
        instance = tuple.__new__(Clue, (number, direction.upper(), text))
        instance.number = number
        instance.direction = direction
        instance.text = text
        return instance


# noinspection PyMethodMayBeStatic
class ClueParser(object):

    comment_leader = '#'

    def parse(self, ifile: TextIO, filename: str=None, pipes: bool = False) -> List[Clue]:
        if filename is not None and filename.lower().endswith('.csv'):
            return self._parse_csv(csv.reader(ifile))
        return self._parse_text(ifile, pipes=pipes)

    def _parse_text(self, ifile: TextIO, pipes: bool = False) -> List[Clue]:
        lines = _read_lines(ifile, comment_leader=self.comment_leader)
        if pipes:
            clues = []
            for parts in map(lambda line: line.split('|'), lines):
                parts = [part.strip() for part in parts if part]
                num_and_dir = parts[0]
                direction = num_and_dir[-1]
                numeral = int(num_and_dir[:-1])
                text = parts[-1]
                clues.append(Clue(numeral, direction, text))
            return clues
        if 'Across' in lines and 'Down' in lines:
            a_start = lines.index('Across')
            d_start = lines.index('Down')
            across_clues = self._parse_text_lines(lines[a_start+1:d_start], 'A')
            down_clues = self._parse_text_lines(lines[d_start+1:], 'D')
            return across_clues + down_clues
        else:  # Assume clues are written like "6A. blah blah" and "23D. blah blah"
            return [self._parse_text_line(line) for line in lines]

    def _parse_text_line(self, line: str, direction: str=None) -> Optional[Clue]:
        m = re.fullmatch(r'^(\d+)([ADad])?\.?\s*(.*)$', line)
        if m is None:
            _log.info("failed to parse clue line")
            return None
        return Clue(int(m.group(1)), direction or m.group(2).upper(), m.group(3))

    def _parse_text_lines(self, lines: List[str], direction: str=None) -> List[Clue]:
        clues = []
        for line in lines:
            clue = self._parse_text_line(line, direction)
            if clue is not None:
                clues.append(clue)
        return clues

    def _parse_numbering_cells(self, numbering: List[str]) -> Tuple[int, str]:
        col0 = re.fullmatch(r'^\s*(\d+)([AD]?)\s*$', numbering[0])
        if not col0:
            raise ValueError("row has unexpected format")
        numeral = col0.group(1)
        direction = col0.group(2)
        if not direction:
            direction = numbering[1].strip().upper()
        return numeral, direction

    def _parse_csv(self, reader: typing.Iterator[List[str]]) -> List[Clue]:
        clues = []
        reader = [row for row in reader if row]
        if not reader:
            return clues
        if not re.fullmatch(r'^\d+[AD]?$', reader[0][0], re.IGNORECASE):  # detect header row
            reader = reader[1:]
        for row in reader:
            clue = row[-1]
            number, direction = self._parse_numbering_cells(row[:-1])
            clues.append(Clue(int(number), direction, clue))
        return clues


class QxwModel(object):

    def __init__(self, cells):
        self.cells = cells

    def to_puz_solution(self):
        values = self.cells
        return ''.join(values)


class QxwParser(object):

    def parse(self, ifile: TextIO) -> QxwModel:
        sq_lines = [line[3:] for line in _read_lines(ifile) if line.startswith("SQ ")]
        cells = []
        for line in sq_lines:
            components = line.strip().split()
            if len(components) == 5:
                val = '_'
            else:
                val = components[5]
            if components[4] == '1':
                val = '.'
            cells.append(val)
        return QxwModel(cells)


def main():
    parser = create_arg_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.__dict__[args.log_level])
    creator = PuzzleCreator()
    output_pathname, puzzle = creator.create(args)
    if args.output_pathname is None:
        print(output_pathname)
    return 0


