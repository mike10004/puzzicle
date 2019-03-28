from unittest import TestCase
from puzio.rendering import RenderModel, ClueRenderer
import tests
import puz
import os
import puzio.rendering
import base64
import logging
import tempfile
from collections import defaultdict


_log = logging.getLogger(__name__)


class RendererTest(TestCase):

    def test_render(self):
        renderer = puzio.rendering.PuzzleRenderer()
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


class RenderModelTest(TestCase):

    def test_info(self):
        puzzle = puz.Puzzle()
        puzzle.width, puzzle.height = 5, 5
        puzzle.fill = '-.-.-------.-.-------.-.-'
        puzzle.clues = ['ADILQ', 'BFJNR', 'CHKPS', 'DEFGH', 'LMNOP']
        puzzle.solution = 'A.B.CDEFGHI.J.KLMNOPQ.R.S'
        puzzle.title = "Foo"
        puzzle.author = "Bar"
        model = RenderModel.build(puzzle)
        self.assertIsInstance(model.info, defaultdict)
        self.assertEqual(puzzle.title, model.info['title'])
        self.assertEqual(puzzle.author, model.info['author'])
        copyright = model.info['copyright']
        self.assertTrue(copyright is None or copyright == '')

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
        d_ = puzio.rendering.merge_dict(d, u)
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
            puz_file = tests.get_testdata_file("normal.puz")
            output_file = os.path.join(tmpdir, "output.pdf")
            exit_code = puzio.rendering.main(["--output", output_file, "--tmpdir", tmpdir, puz_file])
            self.assertEqual(0, exit_code)
            self.assertTrue(os.path.isfile(output_file))