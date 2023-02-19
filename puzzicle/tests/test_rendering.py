#!/usr/bin/env python3

from unittest import TestCase

from puzzicle.puzio.reading import PuzzleReader
from puzzicle.puzio.rendering import RenderModel, ClueRenderer
from puzzicle import tests
import puz
import os
from puzzicle.puzio import rendering
import base64
import logging
import tempfile
from collections import defaultdict
from puzzicle.tests import sample_puzzle

_log = logging.getLogger(__name__)


class RendererTest(TestCase):

    def test_render(self):
        renderer = rendering.PuzzleRenderer()
        puz_base64 = """70NBQ1JPU1MmRE9XTgAAjkkXpJfPlgYuMS4zAAAAAAAAAAAAAAAAAAAAAAAFBQoAAQAAAEFCQy4u
LkRFRi5HSC5JSi5LTE0uLi5OT1AtLS0uLi4tLS0uLS0uLS0uLS0tLi4uLS0tAAAAYWxmYQBnb2xm
AGhvdGVsAGJyYXZvAGluZGlhAGNoYXJsaWUAZGVsdGEAZWNobwBqdWxpZXQAZm94dHJvdAAA
"""
        puz_data = base64.b64decode(puz_base64)
        puzzle = puz.load(puz_data)
        model = RenderModel.build(puzzle)
        html = renderer.render(model)
        _log.debug(html)
        self.assertIsNotNone(html)
        output_file = os.getenv('RENDER_TEST_OUTPUT')
        if output_file:
            with open(output_file, 'w') as ofile:
                print(html, file=ofile)
            _log.info("wrote %s", output_file)

    def test_render_solution(self):
        puzzle = PuzzleReader().read(tests._Data().get_file("mini-5x4.qxw"))
        if not puzzle.clues:
            puzzle.clues.extend([f"c_{i}" for i in range(puzzle.width * puzzle.height)])
        if not puzzle.fill:
            puzzle.fill = puzzle.solution
        model = RenderModel.build(puzzle, filled=True)
        html = rendering.PuzzleRenderer().render(model)
        # noinspection PyUnresolvedReferences,PyPackageRequirements
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        # LAPS.
        # IRATE
        # LAPEL
        # .BAWL
        for row, col, cssclass, number, value in [
            (3, 1, "light", 7, "L"),
            (3, 4, "light", None, "E"),
            (3, 5, "light", None, "L"),
            (1, 1, "light", 1, "L"),
            (1, 3, "light", 3, "P"),
            (2, 5, "light", 6, "E"),
            (1, 5, "dark", None, "\xa0"),
        ]:
            with self.subTest(row=row, col=col):
                cell = soup.select(f"#row-{row} .column-{col}")[0]
                classes = cell.get("class")
                self.assertIn(cssclass, classes)
                if number is None:
                    self.assertEqual(0, len(list(cell.select(".number"))), f"expect cell not numbered: {cell}")
                else:
                    try:
                        number_span = cell.select(".number")[0]
                    except IndexError:
                        self.fail(f"cell has no '.number' child: {cell}")
                    self.assertEqual(str(number), number_span.text)
                value_span = cell.select(".value")[0]
                self.assertEqual(value, value_span.text)

class RenderModelTest(TestCase):

    def test_info(self):
        puzzle = sample_puzzle()
        model = RenderModel.build(puzzle)
        self.assertIsInstance(model.info, defaultdict)
        self.assertEqual(puzzle.title, model.info['title'])
        self.assertEqual(puzzle.author, model.info['author'])
        puz_copyright = model.info['copyright']
        self.assertTrue(puz_copyright is None or puz_copyright == '')


    def test_build_unched(self):
        puzzle = puz.Puzzle()
        puzzle.width, puzzle.height = 5, 5
        puzzle.fill = '-.-.-------.-.-------.-.-'
        puzzle.clues = ['ADILQ', 'BFJNR', 'CHKPS', 'DEFGH', 'LMNOP']
        puzzle.solution = 'A.B.CDEFGHI.J.KLMNOPQ.R.S'
        model = RenderModel.build(puzzle)
        self.assertEqual(puzzle.width, len(model.rows))
        self.assertEqual(puzzle.height, len(model.rows[0]))
        num_clues = 0
        for cell in model.cells():
            if cell.across:
                num_clues += 1
            if cell.down:
                num_clues += 1
        self.assertEqual(len(puzzle.clues), num_clues)


class ClueRendererTest(TestCase):

    def test_get_breaks(self):
        r = ClueRenderer()
        breaks = r.get_breaks(74)
        self.assertListEqual([30, 45, 60], breaks)


class ModuleTest(TestCase):

    def test_merge_dict(self):
        d = {
            'a': [1, 2, 3],
            'b': {
                'c': 4,
                'd': 5,
            }
        }
        u = {
            'b': {
                'c': 6,
                'e': 7,
            }
        }
        d_ = rendering.merge_dict(d, u)
        self.assertIs(d, d_)
        expected = {
            'a': [1, 2, 3],
            'b': {
                'c': 6,
                'd': 5,
                'e': 7,
            }
        }
        self.assertDictEqual(expected, d)

    def test_main_pdf(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            puz_file = tests.data.get_file("normal.puz")
            output_file = os.path.join(tmpdir, "output.pdf")
            exit_code = rendering.main(["--output", output_file, "--tmpdir", tmpdir, puz_file])
            self.assertEqual(0, exit_code)
            self.assertTrue(os.path.isfile(output_file))