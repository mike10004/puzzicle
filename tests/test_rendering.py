from unittest import TestCase
from puzio.rendering import RenderModel
import puz
import puzio.rendering
import base64
import logging
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
