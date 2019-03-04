import io
from typing import TextIO
from typing import Dict, List, Tuple, Iterable
from collections import defaultdict
import puz
import logging

_log = logging.getLogger(__name__)

_CSS = """


body {
    margin-left: auto;
    margin-right: auto;
    width: 7in;
}

.clues {
    margin-top: 32px;
    column-count: 4;
}

.direction {
    display: block;
    font-weight: bold;
    text-transform: uppercase;
    margin-bottom: 6px;
    margin-left: 24px;
}

.direction.down {
    margin-top: 14px;
}

.clue-container {
    display: inline-block;
}

.clue {
    margin-top: 6px;
    display: table;
}

.clue > * {
    display: table-row;
}

.clue > * > * {
    display: table-cell;
}

.clue > * > .number {
    width: 24px;
    font-weight: bold;
}

.grid {
}

.grid table {
    border-collapse: collapse;
    margin-left: auto;
    margin-right: auto;
}

.grid tr {
}

.grid td {
    border: 1px solid black;
    font-size: 8pt;
    vertical-align: top;
    width: 28px;
    height: 28px;
    padding: 2px;
}

.dark {
    background-color: black;
    color: lightgray;
}

.heading {
    margin-bottom: 15px;
}

.heading .title {
    font-weight: bold;
    font-size: 16pt;
    display: inline-block;
}

.heading .author {
    font-size: 12pt;
    display: inline-block;
}

.heading .info {
    font-size: 10pt;
}

.heading .copyright {
    font-style: italic;
}

"""


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

    def render(self, gridrows: List[List[Cell]], ofile, indent=0):
        def fprint(text):
            for i in range(indent):
                print(' ', end="", file=ofile)
            print(text, sep="", file=ofile)
        fprint("<table>")
        for row in gridrows:
            fprint("  <tr>")
            for cell in row:
                assert isinstance(cell, Cell), f"not a cell {cell}"
                content = '&nbsp;' if cell.number is None else str(cell.number)
                css_class = cell.get_class()
                fprint(f"    <td class=\"{css_class}\">{content}</td>")
            fprint("  </td>")
        fprint("</table>")



class ClueRenderer(object):

    def render(self, clues: Dict[str, List[Tuple[int, str]]], ofile, indent=0):
        def fprint(text):
            for i in range(indent):
                print(' ', end="", file=ofile)
            print(text, sep="", file=ofile)
        for direction in ['Across', 'Down']:
            some_clues = clues[direction]
            direction_class = direction.lower()
            fprint(f"<div class=\"direction {direction_class}\">{direction}</div>")
            fprint(f"<div class=\"list-container {direction_class}\">")
            for clue in some_clues:
                fprint("<div class=\"clue-container\">")
                fprint("<div class=\"clue\">")
                fprint("  <div>")
                fprint(f"    <div class=\"number\">{clue[0]}</div>")
                fprint(f"    <div class=\"text\">{clue[1]}</div>")
                fprint("  </div>")
                fprint("</div>")
                fprint("</div>")
            fprint("</div>")

class PuzzleRenderer(object):

    def __init__(self, css: str=_CSS, more_css: Iterable[str]=()):
        self.grid_renderer = GridRenderer()
        self.clue_renderer = ClueRenderer()
        self.css = css
        self.more_css = tuple(more_css)

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
        fprint("<!DOCTYPE html>\n<html>")
        if self.css:
            fprint(f"<style>{self.css}</style>")
        for style_markup in self.more_css:
            fprint(f"<style>{style_markup}</style>")
        fprint("  <body>")
        fprint("    <div class=\"heading\">")
        fprint("      <div class=\"main\">")
        fprint("        <div class=\"title\">")
        fprint(model.info['title'] or '', indent=10)
        fprint("        </div>")
        fprint("        <div class=\"author\">")
        fprint(model.info['author'] or '', indent=10)
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
        fprint("    <div class=\"grid\">")
        self.grid_renderer.render(model.rows, of, indent=6)
        fprint("    </div>")
        fprint("    <div class=\"clues\">")
        self.clue_renderer.render(model.clues, of, indent=6)
        fprint("    </div>")
        fprint("  </body>")
        fprint("</html>")

