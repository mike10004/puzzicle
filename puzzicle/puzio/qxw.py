#!/usr/bin/env python3

"""Tools for handling qxw data."""
import csv
import io
import os
import re
import sys
from argparse import ArgumentParser
from enum import Enum
from typing import List, NamedTuple, TextIO

from puzzicle import puzio


class QxwModel(object):

    def __init__(self, cells, width: int = 0, height: int = 0):
        self.cells = cells
        self.width = width
        self.height = height

    def to_puz_solution(self):
        values = self.cells
        return ''.join(values)



class QxwParser(object):

    def parse(self, ifile: TextIO) -> QxwModel:
        all_lines = puzio.read_lines(ifile)
        sq_lines = [line[3:] for line in all_lines if line.startswith("SQ ")]
        nonsq_lines = [line for line in all_lines if not line.startswith("SQ ")]
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
        gp_line = next(filter(lambda line: line.startswith("GP "), nonsq_lines), None)
        width, height = 0, 0
        if gp_line is not None:
            gp_parts = gp_line.split()
            width, height = int(gp_parts[3]), int(gp_parts[2])   # actually not sure about rows/cols ordering here
        return QxwModel(cells, width, height)


class Direction(Enum):

    ACROSS = "A"
    DOWN = "D"


class Entry(NamedTuple):

    numeral: int
    direction: Direction
    answer: str


class AnswersExportCleaner(object):

    def __init__(self):
        self.raw = False

    def clean(self, text: str) -> List[Entry]:
        head, tail = text.split("\nDown\n", maxsplit=1)
        def _is_ok(line_: str) -> bool:
            line_ = line_.strip()
            if not line_:
                return False
            if line_ in {"Across", "Down"}:
                return False
            if line_.startswith("#"):
                return False
            return True
        def _to_lines(part: str) -> List[str]:
            return [line.rstrip("\r\n") for line in io.StringIO(part) if _is_ok(line)]
        across_lines = _to_lines(head)
        down_lines = _to_lines(tail)
        across_entries = [self.clean_line(line, Direction.ACROSS) for line in across_lines]
        down_entries = [self.clean_line(line, Direction.DOWN) for line in down_lines]
        return across_entries + down_entries

    @staticmethod
    def clean_double(answer_: str):
        double_match = re.fullmatch(r'^\s*(.+), (.+)\s*$', answer_)  # there's some way to do this with just a regex
        if double_match:
            a, b = double_match.group(1), double_match.group(2)
            a, b = a.strip(), b.strip()
            if a.lower() == b.lower():  # not sure if edge case contemplated here is at all possible
                answer_ = a
        return answer_.strip().upper()

    def clean_line(self, line: str, direction: Direction) -> Entry:
        if self.raw:
            raise NotImplementedError("raw format not implemented yet")
        match = re.fullmatch(r'^(\d+)\s*(.*)\s*\(\d+\)\s*$', line)
        if not match:
            raise ValueError(f"line has unexpected format: {repr(line)}")
        num_str, answer = match.group(1), match.group(2)
        answer = self.clean_double(answer)
        return Entry(int(num_str), direction, answer)


def print_entries(entries: List[Entry], fmt: str = "markdown", ofile: TextIO = sys.stdout):
    max_answer_length = max([len(entry.answer) for entry in entries])
    if fmt == "markdown":
        for entry in entries:
            line = f"| {entry.numeral:3}{entry.direction.value} | {entry.answer:<{max_answer_length}} | "
            print(line, file=ofile)
    elif fmt == "tsv":
        csv_writer = csv.writer(ofile, delimiter="\t")
        for entry in entries:
            row = [entry.numeral, entry.direction.value, entry.answer]
            csv_writer.writerow(row)
    else:
        raise NotImplementedError("format not supported")


def _command_clues(file: str, fmt: str = "markdown", ofile: TextIO = sys.stdout) -> int:
    with open(file, "r") as ifile:
        text = ifile.read()
    entries = AnswersExportCleaner().clean(text)
    return print_entries(entries, fmt, ofile)


def main(argv1: List[str] = None, getenv = os.getenv) -> int:
    parser = ArgumentParser(description="Manipulate QXW data.")
    parser.add_argument("command", choices=("clues",), help="command to execute")
    parser.add_argument("file", help="input file")
    parser.add_argument("--format", choices=("markdown", "tsv"), default="markdown", help="set format")
    args = parser.parse_args(argv1)
    if args.command == "clues":
        return _command_clues(args.file, fmt=args.format, ofile=sys.stdout)
    else:
        raise NotImplementedError()


if __name__ == '__main__':
    exit(main())

