#!/usr/bin/env python3

import io
from puzzicle.puzio import showing
from unittest import TestCase

from puzzicle.tests import sample_puzzle

class ShowingTest(TestCase):

    def test_render_text(self):
        puzzle = sample_puzzle()
        buffer = io.StringIO()
        showing.render_text(puzzle, buffer)
        text = buffer.getvalue()
        self.assertEqual("""\
A.B.C
DEFGH
I.J.K
LMNOP
Q.R.S
""", text, f"from {puzzle.solution}")

    def test_show_grid(self):
        from puzzicle.tests import _Data
        pathname = _Data().get_file("autofill-9x9.qxw")
        args = [pathname, "--show", "grid"]
        buffer = io.StringIO()
        ret = showing.main(args, stdout=buffer)
        text = buffer.getvalue()
        self.assertTrue(True if text.strip() else False)
        self.assertEqual(0, ret)
