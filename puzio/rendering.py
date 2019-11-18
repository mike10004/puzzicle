import io
import os
import json
import collections.abc
import copy
import math
import puz
import pdfkit
import logging
import tempfile
from argparse import ArgumentParser, Namespace
from typing import Dict, List, Tuple, Iterable, Any, Iterator, TextIO, Sequence
from collections import defaultdict


_log = logging.getLogger(__name__)


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
            'font-size': '7pt',
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
    font-size: {grid[cell][font-size]};
    vertical-align: top;
    width: {grid[cell][width]};
    height: {grid[cell][height]};
    padding: {grid[cell][padding]};
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


class Cell(object):

    def __init__(self, row: int, column: int, value: str, number: int=None, across: bool=False, down: bool=False):
        self.value = value
        self.row = row
        self.column = column
        self.number = number
        self.across = across
        self.down = down

    def get_class(self):
        return 'dark' if self.value == '.' else 'light'


def _is_across(grid, r, c):
    my_val = grid[r][c]
    if my_val == '.':
        return False
    if c == 0:
        return True
    left_val = grid[r][c - 1]
    try:
        right_val = grid[r][c + 1]
    except IndexError:
        right_val = '.'
    return left_val == '.' and right_val != '.'


def _is_down(grid, r, c):
    my_val = grid[r][c]
    if my_val == '.':
        return False
    if r == 0:
        return True
    up_val = grid[r - 1][c]
    try:
        down_val = grid[r + 1][c]
    except IndexError:
        down_val = '.'
    return up_val == '.' and down_val != '.'


def try_clue(clues, index):
    try:
        return clues[index]
    except IndexError:
        _log.info("clue not found at index %s", index)
        return 'ABSENT'


class RenderModel(object):

    def __init__(self, rows: List[List[Cell]], clues: Dict[str, List[Tuple[int, str]]], info: Dict[str, str]):
        self.rows = rows
        for row in rows:
            for cell in row:
                assert isinstance(cell, Cell), "rows contains non-cell elements"
        self.clues = clues
        self.info = defaultdict(lambda: None)
        self.info.update(info or {})

    def cells(self):
        for r, row in enumerate(self.rows):
            for c, cell in enumerate(row):
                yield cell

    @classmethod
    def build(cls, puzzle: puz.Puzzle) -> 'RenderModel':
        nrows, ncols = puzzle.height, puzzle.width
        rows = []
        for r in range(nrows):
            cols = []
            for c in range(ncols):
                val = puzzle.solution[r * ncols + c]
                cols.append('.' if val == '.' else '')
            rows.append(cols)
        grows = []
        clues = {
            'Across': [],
            'Down': [],
        }
        clue_numbering = puzzle.clue_numbering()
        for direction in ('Across', 'Down'):
            clue_list = clue_numbering.__dict__[direction.lower()]
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
            for clue_info in clue_numbering.__dict__[direction]:
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
                content = '&nbsp;' if cell.number is None else f"<span>{cell.number}</span>"
                css_class = cell.get_class()
                fprint(f"    <td id=\"cell-{cell_index}\" class=\"{css_class} column-{col_index}\">{content}</td>")
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


def _do_render(model, config, more_css, ofile):
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

def main(args: Sequence[str]=None):
    parser = ArgumentParser()
    parser.add_argument("input_file", metavar="PUZ", help=".puz input file")
    parser.add_argument("--log-level", metavar="LEVEL", choices=('INFO', 'DEBUG', 'WARNING', 'ERROR'), default='INFO', help="set log level")
    parser.add_argument("--more-css", metavar="FILE", help="read additional styles from FILE")
    parser.add_argument("--config", metavar="FILE", help="specify FILE with config settings in JSON")
    parser.add_argument("--output", metavar="FILE", default="/dev/stdout", help="set output file")
    parser.add_argument("--tmpdir", metavar="DIR", help="use DIR for temp files")
    args = parser.parse_args(args)
    puzzle = puz.read(args.input_file)
    model = RenderModel.build(puzzle)
    more_css = []
    config = get_default_config()
    if args.config:
        with open(args.config, 'r') as ifile:
            merge_dict(config, json.load(ifile))
    if args.more_css:
        with open(args.more_css, 'r') as ifile:
            more_css.append(ifile.read())
    html_file = args.output
    pdf_file = args.output if args.output.lower().endswith('.pdf') else None
    if pdf_file:
        fd, html_file = tempfile.mkstemp(".html", "temporary", dir=args.tmpdir)
        os.close(fd)
    try:
        with open(html_file, 'w') as ofile:
            _do_render(model, config, more_css, ofile)
        if pdf_file:
            pdfkit.from_file(html_file, pdf_file, options=make_pdf_options(args))
        _log.debug("wrote %s", args.output)
    finally:
        if pdf_file:
            try:
                os.remove(html_file)
            except IOError as e:
                _log.info("caught error deleting temp file %s: %s", html_file, e)
    return 0
