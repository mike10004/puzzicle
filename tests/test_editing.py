import tempfile
from puzio import editing
import io
import puz
from puzio.editing import PuzzleCreator, ClueParser, Clue, GridParser, QxwParser
from unittest import TestCase
import argparse
import os.path
import logging
import tests


tests.configure_logging()
_log = logging.getLogger(__name__)


def namespace(**kwargs) -> argparse.Namespace:
    parser = editing.create_arg_parser()
    ns = parser.parse_args([])
    for k, v in kwargs.items():
        ns.__setattr__(k, v)
    return ns


class TestPuzzleCreator(TestCase):

    def test_create_empty(self):
        with tempfile.TemporaryDirectory() as tempdir:
            creator = PuzzleCreator(tempdir)
            creator.allow_shapeless_grid = True
            output_pathname, puzzle = creator.create(namespace())
            self.assertIs(True, output_pathname and True)
            _log.debug("file length: %s", os.path.getsize(output_pathname))
            self.assertTrue(os.path.isfile(output_pathname))

    def test_determine_shape(self):
        # grid, shape_arg, result
        test_cases = [
            (None, 'square', None),
            (None, '3x9', (3, 9)),
            ('ABCDEFGHI', 'square', (3, 3)),
        ]
        creator = PuzzleCreator()
        creator.allow_shapeless_grid = True
        for grid, shape_arg, expected in test_cases:
            with self.subTest():
                actual = creator.determine_shape(grid, shape_arg)
                self.assertEqual(expected, actual, f"({grid}, {shape_arg}) -> {actual} (expected {expected})")

    def test_create_ok(self):
        solution_text = "AB.C\nD.EF\n.GHI\nJKL."
        clues_text = """Across
1. alfa
3. bravo
4. charlie
5. delta

Down
1. avocado
2. bagel
3. cheeto
4. dog
"""
        with tempfile.TemporaryDirectory() as tempdir:
            solution_file = os.path.join(tempdir, 'solution.txt')
            clues_file = os.path.join(tempdir, 'clues.txt')
            with open(solution_file, 'w') as ofile:
                ofile.write(solution_text)
            with open(clues_file, 'w') as ofile:
                ofile.write(clues_text)
            creator = PuzzleCreator(tempdir)
            args = namespace(clues=clues_file, solution=solution_file)
            output_pathname, puzzle = creator.create(args)
            self.assertEqual(8, len(puzzle.clues), "num clues")
            self.assertEqual('AB.CD.EF.GHIJKL.', puzzle.solution, "solution")
            self.assertEqual(4, puzzle.width, "width")
            self.assertEqual(4, puzzle.height, "height")
            puz.read(output_pathname)

    def test_create_from_qxw(self):
        with tempfile.TemporaryDirectory() as tempdir:
            qxw_file = tests.get_testdata_file('normal.qxw')
            clues_file = tests.get_testdata_file('normal-clues.txt')
            creator = PuzzleCreator(tempdir)
            args = namespace(clues=clues_file, input=qxw_file)
            output_pathname, puzzle = creator.create(args)
            expected_clues = 'alfa golf hotel bravo india charlie delta echo juliet foxtrot'.split()
            self.assertListEqual(expected_clues, puzzle.clues, "clues")
            self.assertEqual('ABC...DEF.GH.IJ.KLM...NOP', puzzle.solution, "converted solution")
            self.assertEqual(5, puzzle.width, "width")
            self.assertEqual(5, puzzle.height, "height")
            puz.read(output_pathname)

    def test_create_unches(self):
        with tempfile.TemporaryDirectory() as tempdir:
            qxw_file = tests.get_testdata_file('unches.qxw')
            clues_file = tests.get_testdata_file('unches-clues.txt')
            creator = PuzzleCreator(tempdir)
            args = namespace(clues=clues_file, input=qxw_file)
            output_pathname, puzzle = creator.create(args)
            expected_clues = 'ADILQ BFJNR CHKPS DEFGH LMNOP'.split()
            self.assertListEqual(expected_clues, puzzle.clues, "clues")
            #self.assertEqual('ABC...DEF.GH.IJ.KLM...NOP', puzzle.solution, "converted solution")
            self.assertEqual(5, puzzle.width, "width")
            self.assertEqual(5, puzzle.height, "height")
            puzzle = puz.read(output_pathname)
            clue_numbering = puzzle.clue_numbering()
            _log.debug("clue_numbering", vars(clue_numbering))

class TestClueParser(TestCase):

    def test__parse_text(self):
        text = """Across
1. apples
4. peaches

Down
1. pumpkin
2. pie
3. whoever's
4. not
"""
        cp = ClueParser()
        clues = cp._parse_text(io.StringIO(text))
        expected = {
            Clue(1, 'A', 'apples'),
            Clue(4, 'A', 'peaches'),
            Clue(1, 'D', 'pumpkin'),
            Clue(2, 'D', 'pie'),
            Clue(3, 'D', 'whoever\'s'),
            Clue(4, 'D', 'not'),
        }
        self.assertSetEqual(expected, set(clues))

    def test__parse_text_again(self):
        clues_text = """Across
1. alfa
3. bravo
4. charlie
5. delta

Down
1. avocado
2. bagel
3. cheeto
4. dog
"""
        clues = ClueParser()._parse_text(io.StringIO(clues_text))
        expected_clue_texts = ['alfa', 'bravo', 'charlie', 'delta', 'avocado', 'bagel', 'cheeto', 'dog']
        actual_clue_texts = [clue.text for clue in clues]
        self.assertSetEqual(set(expected_clue_texts), set(actual_clue_texts))

    def test__parse_text_10clues(self):
        clues_text = """Across
1. alfa
4. bravo
6. charlie
7. delta
8. echo
10. foxtrot

Down
2. golf
3. hotel
5. india
9. juliet
"""
        actual_clues = ClueParser().parse(io.StringIO(clues_text))
        actual_clue_texts = [c.text for c in sorted(actual_clues)]
        expected_clue_texts = 'alfa golf hotel bravo india charlie delta echo juliet foxtrot'.split()
        self.assertListEqual(expected_clue_texts, actual_clue_texts, "clues")

    def test__parse_text_numberwithdirection(self):
        clues_text = """1A. foo
4A. bar
1D. alfa
2D. bravo
3D. charlie
4D. delta
5D. echo
6D. foxtrot"""
        actual_clues = ClueParser()._parse_text(io.StringIO(clues_text))
        expected_clues = {
            Clue(1, 'A', 'foo'),
            Clue(4, 'A', 'bar'),
            Clue(1, 'D', 'alfa'),
            Clue(2, 'D', 'bravo'),
            Clue(3, 'D', 'charlie'),
            Clue(4, 'D', 'delta'),
            Clue(5, 'D', 'echo'),
            Clue(6, 'D', 'foxtrot'),
        }
        self.assertSetEqual(expected_clues, set(actual_clues))


class TestGridParser(TestCase):

    def test_parse(self):
        text = "AB.C\nD.EF\n.GHI\n"
        actual = GridParser().parse(io.StringIO(text))
        self.assertEqual("AB.CD.EF.GHI", actual)

    def test_parse_file(self):
        solution_text = "AB.C\nD.EF\n.GHI\nJKL."
        with tempfile.TemporaryDirectory() as tempdir:
            pn = os.path.join(tempdir, 'solution.txt')
            with open(pn, 'w') as ofile:
                ofile.write(solution_text)
            with open(pn, 'r') as ifile:
                actual = GridParser().parse(ifile)
            self.assertEqual("AB.CD.EF.GHIJKL.", actual)


class QxwParserTest(TestCase):

    def test_parse(self):
        text = tests.load_testdata('normal.qxw', 'r')
        model = QxwParser().parse(io.StringIO(text))
        solution = model.to_puz_solution()
        self.assertEqual('ABC...DEF.GH.IJ.KLM...NOP', solution, "converted solution")

    def test_parse_a1x1(self):
        with tests.open_testdata_file('a-1x1.qxw', 'r') as ifile:
            model = QxwParser().parse(ifile)
        solution = model.to_puz_solution()
        self.assertEqual('A', solution, "converted solution")

    def test_parse_blank1x1(self):
        with tests.open_testdata_file('blank-1x1.qxw', 'r') as ifile:
            model = QxwParser().parse(ifile)
        solution = model.to_puz_solution()
        self.assertEqual('_', solution, "converted solution")

    def test_parse_adark1x1(self):
        with tests.open_testdata_file('a-dark-1x1.qxw', 'r') as ifile:
            model = QxwParser().parse(ifile)
        solution = model.to_puz_solution()
        self.assertEqual('.', solution, "converted solution")

    def test_parse_basic2x2(self):
        text = tests.load_testdata('basic-2x2.qxw', 'r')
        model = QxwParser().parse(io.StringIO(text))
        solution = model.to_puz_solution()
        self.assertEqual('_.._', solution, "converted solution")

    def test_parse_letter_in_dark_2x2(self):
        with tests.open_testdata_file('letter-in-dark.qxw', 'r') as ifile:
            qxw = QxwParser().parse(ifile)
        sol = qxw.to_puz_solution()
        self.assertEqual('A..D', sol, "solution")