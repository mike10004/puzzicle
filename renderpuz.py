import puz
from puzio import rendering
import argparse
import logging


_log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", metavar="PUZ", help=".puz input file")
    parser.add_argument("--log-level", choices=('INFO', 'DEBUG', 'WARNING', 'ERROR'), default='INFO', help="set log level")
    parser.add_argument("--render", metavar="FILE", help="render as HTML to FILE")
    parser.add_argument("--more-css", metavar="FILE", help="with --render, read additional styles from FILE")
    parser.add_argument("--output", metavar="FILE", default="/dev/stdout", help="set output file")
    args = parser.parse_args()
    puzzle = puz.read(args.input_file)
    model = rendering.RenderModel.build(puzzle)
    more_css = []
    if args.more_css:
        with open(args.more_css, 'r') as ifile:
            more_css.append(ifile.read())
    with open(args.render, 'w') as ofile:
        renderer = rendering.PuzzleRenderer(more_css=more_css)
        renderer.render(model, ofile)
    _log.debug("html written to %s", args.render)
    return 0
