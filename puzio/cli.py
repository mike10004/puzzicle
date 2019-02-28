import argparse
import puz
from .. import puzio

def main():
    parser = argparse.ArgumentParser()
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
    args = parser.parse_args()
    return 0


