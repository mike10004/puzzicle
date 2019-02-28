import os
import os.path
import puz
from argparse import Namespace, ArgumentParser
import common


def _generate_filename(directory):
    stamp = common.timestamp()
    return os.path.join(directory, f"p{stamp}.puz")


class PuzzleCreator(object):

    def __init__(self, output_dir=None):
        self.output_dir = output_dir or os.getcwd()

    def create(self, args: Namespace) -> str:
        if args.input:
            puzzle = puz.read(args.input)
        else:
            puzzle = puz.Puzzle()
            puzzle.preamble = b''
        output_pathname = args.output_pathname or _generate_filename(self.output_dir)
        puzzle.save(output_pathname)
        return output_pathname


def create_arg_parser() -> ArgumentParser:
    parser = ArgumentParser()
    parser.add_argument("output_pathname", nargs='?', metavar="FILE", help="output pathname; defaults to timestamped filename in $PWD")
    parser.add_argument("--input", metavar="FILE", help="input file in .puz format")
    parser.add_argument("--clues", help="define clues source")
    parser.add_argument("--solution", help="define solution; use . char for dark cells")
    parser.add_argument("--grid", help="define grid; use '.' for dark cells, '-' for light")
    parser.add_argument("--title", help="set title")
    parser.add_argument("--author", help="set author")
    parser.add_argument("--shape", metavar="SPEC", help="set shape; value can be 'ROWSxCOLS' or 'square'")
    parser.add_argument("--copyright")
    parser.add_argument("--notes")
    return parser


def main():
    parser = create_arg_parser()
    args = parser.parse_args()
    creator = PuzzleCreator()
    output_pathname = creator.create(args)
    if args.output_pathname is None:
        print(output_pathname)
    return 0


