#!/usr/bin/env python3

"""Tools for handling qxw data."""

import io
import os
import re
import sys
from argparse import ArgumentParser
from enum import Enum
from typing import List, NamedTuple, TextIO


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
    if fmt != "markdown":
        raise NotImplementedError("non-markdown format not supported")
    for entry in entries:
        line = f"| {entry.numeral:3}{entry.direction.value} | {entry.answer:<{max_answer_length}} |"
        print(line, file=ofile)
    return 0


def _command_clues(file: str, fmt: str = "markdown", ofile: TextIO = sys.stdout) -> int:
    with open(file, "r") as ifile:
        text = ifile.read()
    entries = AnswersExportCleaner().clean(text)
    return print_entries(entries, fmt, ofile)


def main(argv1: List[str] = None, getenv = os.getenv) -> int:
    parser = ArgumentParser(description="Manipulate QXW data.")
    parser.add_argument("command", choices=("clues",), help="command to execute")
    parser.add_argument("file", help="input file")
    args = parser.parse_args(argv1)
    if args.command == "clues":
        return _command_clues(args.file, ofile=sys.stdout)
    return 0


if __name__ == '__main__':
    exit(main())

