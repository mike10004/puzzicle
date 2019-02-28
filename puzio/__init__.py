import puz
from argparse import Namespace

def create(args: Namespace) -> str:
    if args.input_file:
        puzzle = puz.read(args.input_file)
    else:
        puzzle = puz.Puzzle()
