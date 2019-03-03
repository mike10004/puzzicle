import os
import re
import os.path
import puz
import csv
import math
from argparse import Namespace, ArgumentParser
import common
import typing
from typing import List, Tuple, Optional
from typing import TextIO
import logging
from . import rendering


_log = logging.getLogger(__name__)


def _generate_filename(directory):
    stamp = common.timestamp()
    return os.path.join(directory, f"p{stamp}.puz")


def create_arg_parser() -> ArgumentParser:
    parser = ArgumentParser()
    parser.add_argument("output_pathname", nargs='?', metavar="FILE", help="output pathname; defaults to timestamped filename in $PWD")
    parser.add_argument("--input", metavar="FILE", help="input file in .puz format")
    parser.add_argument("--clues", help="define clues source")
    parser.add_argument("--solution", help="define solution; use '.' char for dark cells")
    parser.add_argument("--grid", help="define grid; use '.' for dark cells, anything for light")
    parser.add_argument("--title", metavar="STR", help="set title")
    parser.add_argument("--author", metavar="STR", help="set author")
    parser.add_argument("--shape", metavar="SPEC", default='square', help="set shape; value can be 'ROWSxCOLS' or 'square'")
    parser.add_argument("--copyright", metavar="STR", help="set copyright")
    parser.add_argument("--notes", metavar="STR", help="set notes")
    parser.add_argument("--log-level", choices=('INFO', 'DEBUG', 'WARNING', 'ERROR'), default='INFO', help="set log level")
    parser.add_argument("--render", metavar="FILE", help="render as HTML to FILE")
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

    def __init__(self, output_dir=None):
        self.output_dir = output_dir or os.getcwd()

    def determine_shape(self, grid: str, shape_arg: str) -> Optional[Tuple[int, int]]:
        shape_tokens = re.fullmatch(r'^(\d+)x(\d+)', shape_arg)
        if shape_tokens:
            return int(shape_tokens.group(1)), int(shape_tokens.group(2))
        if shape_arg != 'square':
            raise ValueError("invalid shape specification")
        if not grid:
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
        render_model = rendering.RenderModel.build(puzzle)
        clue_locations = render_model.clue_locations()
        if len(clue_locations) != len(puzzle.clues):
            _log.warning("list of %d clues is not compatible with expected clue locations (%d)", len(puzzle.clues), len(clue_locations))
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

    def parse(self, ifile: TextIO, filename: str=None) -> List[Clue]:
        if filename is not None and filename.lower().endswith('.csv'):
            return self._parse_csv(csv.reader(ifile))
        return self._parse_text(ifile)

    def _parse_text(self, ifile: TextIO) -> List[Clue]:
        lines = _read_lines(ifile, comment_leader=self.comment_leader)
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
        if len(numbering) == 1:
            direction = numbering[0][-1]
            number = numbering[0][:-1]
        elif len(numbering) == 2:
            number, direction = numbering
        else:
            raise ValueError("unexpected number of numbering cells: " + str(len(numbering)))
        return number, direction

    def _parse_csv(self, reader: typing.Iterator[List[str]]) -> List[Clue]:
        clues = []
        for row in reader:
            clue = row[-1]
            number, direction = self._parse_numbering_cells(row[:-1])
            clues.append(Clue(number, direction, clue))
        return clues


class QxwModel(object):

    def __init__(self, grid_entries: List[Tuple[int, int, int, str]]):
        self.grid_entries = grid_entries

    def to_puz_solution(self):
        values = [entry[-1] for entry in sorted(self.grid_entries)]
        return ''.join(values)


class QxwParser(object):

    def parse(self, ifile: TextIO) -> QxwModel:
        sqct_lines = [line for line in _read_lines(ifile) if line.startswith("SQCT")]
        grid_entries = []
        for line in sqct_lines:
            _, x, y, z, value = line.strip().split()
            grid_entries.append((int(y), int(x), int(z), value))
        return QxwModel(grid_entries)


def main():
    parser = create_arg_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.__dict__[args.log_level])
    if args.render:
        puzzle = puz.read(args.input or args.output_pathname)
        model = rendering.RenderModel.build(puzzle)
        with open(args.render, 'w') as ofile:
            rendering.PuzzleRenderer().render(model, ofile)
        _log.debug("html written to %s", args.render)
        return 0
    creator = PuzzleCreator()
    output_pathname, puzzle = creator.create(args)
    if args.output_pathname is None:
        print(output_pathname)
    return 0


