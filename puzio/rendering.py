import io
from typing import TextIO
from typing import Dict, List, Tuple
import puz
import logging

_log = logging.getLogger(__name__)

_CSS = """


body {
    margin: 0.75in; 
}

.clues {
    margin-bottom: 15px;
}

.direction {
    display: block;
    font-weight: bold;
    text-transform: uppercase;
    margin-top: 15px;
}

.clue {
    display: block;
}

.clue .number {
    display: inline-block;
    font-weight: bold;
    width: 32px;
    text-align: right;
    margin-right: 8px;
}

.clue .text {
    display: inline-block;
}

.clue .number:after {

}

.grid {
    
}

.grid table {
    border-collapse: collapse;
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

    def __init__(self, rows: List[List[Cell]], clues: Dict[str, List[Tuple[int, str]]]):
        self.rows = rows
        for row in rows:
            for cell in row:
                assert isinstance(cell, Cell), "rows contains non-cell elements"
        self.clues = clues

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
        return RenderModel(grows, clues)


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
            fprint(f"<span class=\"direction\">{direction}</span>")
            for clue in some_clues:
                fprint(f"<span class=\"clue\"><span class=\"number\">{clue[0]}</span><span class=\"text\">{clue[1]}</span></span>")


class PuzzleRenderer(object):

    def __init__(self):
        self.grid_renderer = GridRenderer()
        self.clue_renderer = ClueRenderer()
        self.css = _CSS

    def render(self, model: RenderModel, ofile=None):
        return_str = ofile is None
        if return_str:
            ofile = io.StringIO()
        self._render(model, ofile)
        if return_str:
            return ofile.getvalue()

    def _render(self, model: RenderModel, of: TextIO):
        def fprint(text):
            print(text, sep="", file=of)
        fprint("<!DOCTYPE html>\n<html>")
        fprint(f"<style>{self.css}</style>")
        fprint("  <body>")
        fprint("    <div class=\"clues\">")
        self.clue_renderer.render(model.clues, of, indent=6)
        fprint("    </div>")
        fprint("    <div class=\"grid\">")
        self.grid_renderer.render(model.rows, of, indent=6)
        fprint("    </div>")
        fprint("  </body>")
        fprint("</html>")

