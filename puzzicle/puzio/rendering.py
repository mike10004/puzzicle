#!/usr/bin/env python3

import contextlib
import io
import itertools
import os
import json
import collections.abc
import copy
import math
import sys
from pathlib import Path
from typing import Optional

import puz
import pdfkit
import logging
import tempfile
from argparse import ArgumentParser, Namespace
from typing import Dict, List, Tuple, Iterable, Any, Iterator, TextIO, Sequence, Union
from collections import defaultdict

from puzzicle.puzio.reading import PuzzleReader

_log = logging.getLogger(__name__)


_DARK = '.'
_GRID_CELL_WIDTH = 28
_GRID_CELL_HEIGHT = 30
_GRID_CELL_PAD_VERT = 1
_GRID_CELL_PAD_HORZ = 2
_NUM_GRID_ROWS = 15

_DEFAULT_CSS_MODEL = {
    'body': {
        'width': '7.5in',
    },
    'clue': {
        'margin-top': '4px',
        'font': {
            'size': '10pt',
        },
    },
    'column': {
        'width': '160px',
    },
    'grid': {
        'cell': {
            'width': f'{_GRID_CELL_WIDTH}px',
            'height': f'{_GRID_CELL_HEIGHT}px',
            'padding': f'{_GRID_CELL_PAD_VERT}px {_GRID_CELL_PAD_HORZ}px',
        },
        'total-height': str(_NUM_GRID_ROWS * (_GRID_CELL_HEIGHT + _GRID_CELL_PAD_VERT + 2) + 10) + 'px'
    },
    'heading': {
        'display': 'block',
        'margin-bottom': '8px',
        'title': {
            'font-size': '16pt',
            'font-weight': 'bold',
            'font-style': 'normal',
        },
        'author': {
            'font-size': '12pt',
            'font-weight': 'normal',
            'font-style': 'italic',
        },
        'info': {
            'font-size': '10pt',
            'font-weight': 'normal',
            'font-style': 'normal',
        },
        'copyright': {
            'font-size': '12pt',
            'font-weight': 'normal',
            'font-style': 'italic',
        },
    },
}

_CSS_TEMPLATE = """
body {{
    margin-left: auto;
    margin-right: auto;
    width: {body[width]};
}}

.playground {{
    position: relative;
}}

.clues {{
    z-index: 0;
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
}}

.clues-column {{
    float: left;
    padding-top: {grid[total-height]};
    padding-left: 25px;
    width: {column[width]};
}}

.clues-column.first {{
    padding-top: 0;
    padding-left: 0;
}}

.direction {{
    display: block;
    font-weight: bold;
    text-transform: uppercase;
    margin-bottom: 6px;
    margin-left: 24px;
}}

.direction.down {{
    margin-top: 14px;
}}

.clue-container {{
    display: block;
}}

.clue {{
    margin-top: {clue[margin-top]};
    display: table;
    font-size: {clue[font][size]};
}}

.clue > * {{
    display: table-row;
}}

.clue > * > * {{
    display: table-cell;
}}

.clue > * > .number {{
    width: 16px;
    font-weight: bold;
    text-align: right;
    padding-right: 10px; 
}}

.clue > * > .value {{
}}

.grid {{
    z-index: 100;
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
}}

.grid table {{
    border-collapse: collapse;
    margin-left: auto;
    margin-right: 15px;
}}

.grid tr {{
}}

.grid td {{
    border: 1px solid black;
    vertical-align: top;
    width: {grid[cell][width]};
    height: {grid[cell][height]};
    padding: {grid[cell][padding]};
    position: relative;
}}

.cell .number {{
    font-size: 7pt;
    position: absolute;
    top: 2px;
    right: 0;
    bottom: 0;
    left: 2px;
}}

.cell .value {{
    font-size: 14pt;
    font-family: sans-serif;
    position: absolute;
    top: 4px;
    right: 0;
    bottom: 0;
    left: 12px;
}}

.dark {{
    background-color: black;
    color: lightgray;
}}

.heading {{
    display: {heading[display]};
    margin-bottom: {heading[margin-bottom]};
}}

.heading .title {{
    font-weight: {heading[title][font-weight]};
    font-size: {heading[title][font-size]};
    font-style: {heading[title][font-style]};
    display: inline-block;
}}

.heading .author {{
    font-weight: {heading[author][font-weight]};
    font-size: {heading[author][font-size]};
    font-style: {heading[author][font-style]};
    display: inline-block;
}}

.heading .info {{
    font-size: {heading[info][font-size]};
    font-weight: {heading[info][font-weight]};
    font-style: {heading[info][font-style]};
}}

.heading .copyright {{
    font-size: {heading[copyright][font-size]};
    font-weight: {heading[copyright][font-weight]};
    font-style: {heading[copyright][font-style]};
}}

"""

_DEFAULT_CONFIG = {
    'columns': 4,
    'css': _DEFAULT_CSS_MODEL
}

# https://stackoverflow.com/a/3233356/2657036
def merge_dict(d, u):
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            d[k] = merge_dict(d.get(k, {}), v)
        else:
            d[k] = v
    return d


def get_default_config():
    return copy.deepcopy(_DEFAULT_CONFIG)


def try_clue(clues, index):
    try:
        return clues[index]
    except IndexError:
        _log.info("clue not found at index %s", index)
        return 'ABSENT'


class Cell(object):

    def __init__(self, row: int, column: int, value: str, number: int=None, across: bool=False, down: bool=False):
        self.value = value
        self.row = row
        self.column = column
        self.number = number
        self.across = across
        self.down = down

    def get_class(self):
        cssclass = 'dark' if self.value == _DARK else 'light'
        return cssclass

    def to_char(self) -> str:
        return self.value or ' '

    def __str__(self):
        return f"Cell(row={self.row},col={self.column},value={repr(self.value)},number={self.number})"


class RenderModel(object):

    def __init__(self, rows: List[List[Cell]], clues: Dict[str, List[Tuple[int, str]]], info: Dict[str, str]):
        self.rows = rows
        for row in rows:
            for cell in row:
                assert isinstance(cell, Cell), "rows contains non-cell elements"
        self.clues = clues
        self.info: Dict[str, Optional[str]] = defaultdict(lambda: None)
        self.info.update(info or {})

    def cells(self):
        for r, row in enumerate(self.rows):
            for c, cell in enumerate(row):
                yield cell

    @classmethod
    def build(cls, puzzle: puz.Puzzle, filled: bool = False) -> 'RenderModel':
        nrows, ncols = puzzle.height, puzzle.width
        rows = []
        for r in range(nrows):
            cols = []
            for c in range(ncols):
                val = puzzle.solution[r * ncols + c]
                cols.append(val if val == '.' or filled else '')
            rows.append(cols)
        grows = []
        clues = {
            'Across': [],
            'Down': [],
        }
        clue_numbering = puzzle.clue_numbering()
        for direction in ('Across', 'Down'):
            clue_list = getattr(clue_numbering, direction.lower())
            for i in range(len(clue_list)):
                clue_info = clue_list[i]
                clue_tuple = (clue_info['num'], clue_info['clue'])
                clues[direction].append(clue_tuple)
        cell_list = []
        for r in range(len(rows)):
            row = rows[r]
            grow = []
            for c in range(len(row)):
                value = rows[r][c]
                cell = Cell(r, c, value)
                cell_list.append(cell)
                grow.append(cell)
            grows.append(grow)
        for direction in ('across', 'down'):
            for clue_info in getattr(clue_numbering, direction):
                cell_num, cell_index = clue_info['num'], clue_info['cell']
                cell_list[cell_index].number = cell_num
                cell_list[cell_index].across = (direction == 'across')
                cell_list[cell_index].down = (direction == 'down')
        info = {}
        for attrib in ('title', 'author', 'copyright', 'notes'):
            value = puzzle.__dict__[attrib]
            if value:
                info[attrib] = value
        return RenderModel(grows, clues, info)


# noinspection PyMethodMayBeStatic
class GridRenderer(object):

    def __init__(self, config: Dict[str, Any]):
        self.config = config or get_default_config()

    def render(self, gridrows: List[List[Cell]], ofile, indent=0):
        def fprint(text):
            for i in range(indent):
                print(' ', end="", file=ofile)
            print(text, sep="", file=ofile)
        row_index, cell_index = 0, 0
        fprint("<table>")
        for row in gridrows:
            row_index += 1
            fprint(f"  <tr class=\"row\" id=\"row-{row_index}\">")
            col_index = 0
            for cell in row:
                assert isinstance(cell, Cell), f"not a cell {cell}"
                cell_index += 1
                col_index += 1
                content = ""
                if cell.number is not None:
                    content += f"""<span class="number">{cell.number}</span>"""
                value = "&nbsp;" if not cell.value or cell.value == _DARK else cell.value
                content += f"""<span class="value">{value}</span>"""
                css_class = cell.get_class()
                fprint(f"    <td id=\"cell-{cell_index}\" class=\"cell {css_class} column-{col_index}\">{content}</td>")
            fprint("  </td>")
        fprint("</table>")



class ClueRenderer(object):

    def __init__(self, config: Dict[str, Any]=None):
        self.config = config or get_default_config()

    def element_iterator(self, clues: Dict[str, List[Tuple[int, str]]]) -> Iterator[str]:
        for direction in ['Across', 'Down']:
            some_clues = clues[direction]
            direction_class = direction.lower()
            yield f"<div class=\"direction {direction_class}\">{direction}</div>"
            for number, prompt in some_clues:
                clue_element = f"""\
<div class=\"clue-container\">
  <div class=\"clue\">
    <div>
      <div class=\"number\">{number}</div>
      <div class=\"text\">{prompt}</div>
    </div>
  </div>
</div>
"""
                yield clue_element

    def get_breaks(self, num_elements) -> List[int]:
        try:
            # noinspection PyTypeChecker
            return self.config['breaks']
        except KeyError:
            pass
        num_columns = self.config['columns']
        division_len = int(math.ceil(num_elements / (num_columns + 1)))
        return [division_len * 2] + [division_len * 2 + division_len * i for i in range(1, num_columns - 1)]

    def render(self, clues: Dict[str, List[Tuple[int, str]]], ofile, indent=0):
        def fprint(text):
            lines = text.split(os.linesep)
            for line in lines:
                for _ in range(indent):
                    print(' ', end="", file=ofile)
                print(line, file=ofile)
        elements = list(self.element_iterator(clues))
        element_breaks = self.get_breaks(len(elements))
        fprint("<div class=\"clues-column first\">")
        for i in range(len(elements)):
            element = elements[i]
            fprint(element)
            if i in element_breaks and (i != (len(elements) - 1)):
                fprint("</div> <!-- end clue-column -->")
                fprint("<div class=\"clues-column\">")
        fprint("</div> <!-- end clue-column -->")


class PuzzleRenderer(object):

    def __init__(self, config: Dict[str, Any]=None, more_css: Iterable[str]=None):
        self.config = config or get_default_config()
        self.grid_renderer = GridRenderer(self.config)
        self.clue_renderer = ClueRenderer(self.config)
        self.more_css = more_css or tuple()

    def render(self, model: RenderModel, ofile=None):
        return_str = ofile is None
        if return_str:
            ofile = io.StringIO()
        self._render(model, ofile)
        if return_str:
            return ofile.getvalue()

    def _render(self, model: RenderModel, of: TextIO):
        def fprint(text, indent=0):
            for i in range(indent):
                print(' ', sep="", end="", file=of)
            print(text, sep="", file=of)
        title, author = (model.info['title'] or ''), (model.info['author'] or '')
        fprint("<!DOCTYPE html>")
        fprint("<html>")
        fprint("<head>")
        if title and author:
            fprint(f"  <title>{title} by {author}</title>")
        elif title:
            fprint(f"  <title>{title}</title>")
        base_css = _CSS_TEMPLATE.format(**(self.config['css']))
        all_css = [base_css] + list(self.more_css)
        for style_markup in all_css:
            fprint(f"<style>{style_markup}</style>")
        fprint("</head>")
        fprint("  <body>")
        fprint("    <div class=\"heading\">")
        fprint("      <div class=\"main\">")
        fprint("        <div class=\"title\">")
        fprint(model.info['title'] or '', indent=10)
        fprint("        </div>")
        fprint("        <div class=\"author\">")
        fprint('' if not model.info['author'] else ('by ' + str(model.info['author'])), indent=10)
        fprint("        </div>")
        fprint("      </div>")
        fprint("      <div class=\"info\">")
        fprint("        <div class=\"copyright\">")
        fprint(model.info['copyright'] or '', indent=10)
        fprint("        </div>")
        fprint("        <div class=\"notes\">")
        fprint(model.info['notes'] or '', indent=10)
        fprint("        </div>")
        fprint("      </div>")
        fprint("    </div>")
        fprint("    <div class=\"playground\">")
        fprint("      <div class=\"grid\">")
        self.grid_renderer.render(model.rows, of, indent=6)
        fprint("      </div>")
        fprint("      <div class=\"clues\">")
        self.clue_renderer.render(model.clues, of, indent=6)
        fprint("      </div>")
        fprint("    </div>")
        fprint("  </body>")
        fprint("</html>")


def render_html(model, config, more_css, ofile):
    renderer = PuzzleRenderer(config, more_css=more_css)
    renderer.render(model, ofile)

def make_pdf_options(args: Namespace):
    return {
        'quiet': '',
        'page-size': 'Letter',
        'margin-top': '0.25in',
        'margin-right': '0.0in',
        'margin-bottom': '0.25in',
        'margin-left': '0.0in',
        'encoding': "UTF-8",
     }

@contextlib.contextmanager
def open_output(pathname: Union[Path, str] = None, mode: str = 'w') -> TextIO:
    if pathname is None or pathname == '-':
        yield sys.stdout
    else:
        with open(pathname, mode) as ofile:
            yield ofile


def main(args: Sequence[str]=None):
    parser = ArgumentParser()
    parser.add_argument("input_file", metavar="FILE", help=".puz or .qxw input file")
    parser.add_argument("--log-level", metavar="LEVEL", choices=('INFO', 'DEBUG', 'WARNING', 'ERROR'), default='INFO', help="set log level")
    parser.add_argument("--more-css", metavar="FILE", help="read additional styles from FILE")
    parser.add_argument("--config", metavar="FILE", help="specify FILE with config settings in JSON")
    parser.add_argument("--output", metavar="FILE", help="set output file; deafult is stdout")
    parser.add_argument("--tmpdir", metavar="DIR", help="use DIR for temp files")
    parser.add_argument("--solution", action='store_true', help="include solution")
    _FORMAT_CHOICES = ("text", "html", "pdf")
    parser.add_argument("--format", metavar="FORMAT", choices=("html", "pdf"), default="html", help=f"one of {_FORMAT_CHOICES}")
    args = parser.parse_args(args)
    puzzle = PuzzleReader().read(args.input_file)
    if args.solution:
        if not puzzle.clues:
            puzzle.clues.extend([f"u_{r}_{c}" for r, c in itertools.product(range(puzzle.height), range(puzzle.width))])
        if not puzzle.fill:
            puzzle.fill = puzzle.solution
    model = RenderModel.build(puzzle, filled=args.solution)
    more_css = []
    config = get_default_config()
    if args.config:
        with open(args.config, 'r') as ifile:
            merge_dict(config, json.load(ifile))
    if args.more_css:
        with open(args.more_css, 'r') as ifile:
            more_css.append(ifile.read())
    with tempfile.TemporaryDirectory(prefix="puzrender_", dir=args.tmpdir) as tempdir:
        if args.format in {'html', 'pdf'}:
            html_file = os.path.join(tempdir, "puzzle.html")
            with open(html_file, 'w') as ofile:
                render_html(model, config, more_css, ofile)
            final_file = html_file
            mode_suffix = ''
            if args.format == 'pdf':
                mode_suffix = 'b'
                pdf_file = os.path.join(tempdir, "puzzle.pdf")
                pdfkit.from_file(html_file, pdf_file, options=make_pdf_options(args))
                final_file = pdf_file
        else:
            raise NotImplementedError("output format not supported")
        with open_output(args.output, mode=f"w{mode_suffix}") as ofile:
            if args.format == 'pdf' and ofile.isatty():
                _log.error("not writing pdf on standard output in console")
                return 1
            with open(final_file, mode=f"r{mode_suffix}") as ifile:
                ofile.write(ifile.read())
        _log.debug("wrote to file %s", args.output)
    return 0
