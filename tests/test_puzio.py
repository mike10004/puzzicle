import tempfile
import puzio
import puzio.rendering
import io
import puz
from puzio import PuzzleCreator, ClueParser, Clue, GridParser, QxwParser
from unittest import TestCase
import argparse
import os.path
import logging
import tests
import base64

tests.configure_logging()
_log = logging.getLogger(__name__)


def namespace(**kwargs) -> argparse.Namespace:
    parser = puzio.create_arg_parser()
    ns = parser.parse_args([])
    for k, v in kwargs.items():
        ns.__setattr__(k, v)
    return ns


class TestPuzzleCreator(TestCase):

    def test_create_empty(self):
        with tempfile.TemporaryDirectory() as tempdir:
            creator = PuzzleCreator(tempdir)
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
        with tempfile.TemporaryDirectory() as tempdir:
            qxw_text = base64.b64decode(''.join(_QXW_FILE_BASE64.split())).decode('utf8')
            qxw_file = os.path.join(tempdir, 'hello.qxw')
            clues_file = os.path.join(tempdir, 'clues.txt')
            with open(qxw_file, 'w') as ofile:
                ofile.write(qxw_text)
            with open(clues_file, 'w') as ofile:
                ofile.write(clues_text)
            creator = PuzzleCreator(tempdir)
            args = namespace(clues=clues_file, input=qxw_file)
            output_pathname, puzzle = creator.create(args)
            expected_clues = 'alfa golf hotel bravo india charlie delta echo juliet foxtrot'.split()
            self.assertListEqual(expected_clues, puzzle.clues, "clues")
            self.assertEqual('ABC...DEF.GH.IJ.KLM...NOP', puzzle.solution, "converted solution")
            self.assertEqual(5, puzzle.width, "width")
            self.assertEqual(5, puzzle.height, "height")
            puz.read(output_pathname)


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


_QXW_FILE_BASE64 = """I1FYVzJ2MyBodHRwOi8vd3d3LnF1aW5hcGFsdXMuY29tCkdQIDAgNSA1IDIgMCAwClRUTAorCkFV
VAorCkdMUCAxIDEgMCAwIDAKR1NQIGZmZmZmZiAwMDAwMDAgMCAwIDAgMCAwMDAwMDAKR1NQTUsg
MAorXCMKR1NQTUsgMQorCkdTUE1LIDIKKwpHU1BNSyAzCisKR1NQTUsgNAorCkdTUE1LIDUKKwpU
TSAwIDAgMCAwIDAKKwpUTVNHIDAgMAorClRNU0cgMCAxCisKREZOIDAKKy91c3Ivc2hhcmUvZGlj
dC93b3JkcwpERk4gMQorCkRGTiAyCisKREZOIDMKKwpERk4gNAorCkRGTiA1CisKREZOIDYKKwpE
Rk4gNworCkRGTiA4CisKRFNGIDAKK14uKisoPzwhJ3MpCkRTRiAxCisKRFNGIDIKKwpEU0YgMwor
CkRTRiA0CisKRFNGIDUKKwpEU0YgNgorCkRTRiA3CisKRFNGIDgKKwpEQUYgMAorCkRBRiAxCisK
REFGIDIKKwpEQUYgMworCkRBRiA0CisKREFGIDUKKwpEQUYgNgorCkRBRiA3CisKREFGIDgKKwpT
USAwIDAgMCAwIDAgQQpTUSAxIDAgMCAwIDAgQgpTUSAyIDAgMCAwIDAgQwpTUSAzIDAgMCAwIDEg
IApTUSA0IDAgMCAwIDEgIApTUSAwIDEgMCAwIDEgIApTUSAxIDEgMCAwIDAgRApTUSAyIDEgMCAw
IDAgRQpTUSAzIDEgMCAwIDAgRgpTUSA0IDEgMCAwIDEgIApTUSAwIDIgMCAwIDAgRwpTUSAxIDIg
MCAwIDAgSApTUSAyIDIgMCAwIDEgIApTUSAzIDIgMCAwIDAgSQpTUSA0IDIgMCAwIDAgSgpTUSAw
IDMgMCAwIDEgIApTUSAxIDMgMCAwIDAgSwpTUSAyIDMgMCAwIDAgTApTUSAzIDMgMCAwIDAgTQpT
USA0IDMgMCAwIDEgIApTUSAwIDQgMCAwIDEgIApTUSAxIDQgMCAwIDEgIApTUSAyIDQgMCAwIDAg
TgpTUSAzIDQgMCAwIDAgTwpTUSA0IDQgMCAwIDAgUApTUVNQIDAgMCBmZmZmZmYgMDAwMDAwIDAg
MCAwIDAgMDAwMDAwClNRU1AgMSAwIGZmZmZmZiAwMDAwMDAgMCAwIDAgMCAwMDAwMDAKU1FTUCAy
IDAgZmZmZmZmIDAwMDAwMCAwIDAgMCAwIDAwMDAwMApTUVNQIDMgMCBmZmZmZmYgMDAwMDAwIDAg
MCAwIDAgMDAwMDAwClNRU1AgNCAwIGZmZmZmZiAwMDAwMDAgMCAwIDAgMCAwMDAwMDAKU1FTUCAw
IDEgZmZmZmZmIDAwMDAwMCAwIDAgMCAwIDAwMDAwMApTUVNQIDEgMSBmZmZmZmYgMDAwMDAwIDAg
MCAwIDAgMDAwMDAwClNRU1AgMiAxIGZmZmZmZiAwMDAwMDAgMCAwIDAgMCAwMDAwMDAKU1FTUCAz
IDEgZmZmZmZmIDAwMDAwMCAwIDAgMCAwIDAwMDAwMApTUVNQIDQgMSBmZmZmZmYgMDAwMDAwIDAg
MCAwIDAgMDAwMDAwClNRU1AgMCAyIGZmZmZmZiAwMDAwMDAgMCAwIDAgMCAwMDAwMDAKU1FTUCAx
IDIgZmZmZmZmIDAwMDAwMCAwIDAgMCAwIDAwMDAwMApTUVNQIDIgMiBmZmZmZmYgMDAwMDAwIDAg
MCAwIDAgMDAwMDAwClNRU1AgMyAyIGZmZmZmZiAwMDAwMDAgMCAwIDAgMCAwMDAwMDAKU1FTUCA0
IDIgZmZmZmZmIDAwMDAwMCAwIDAgMCAwIDAwMDAwMApTUVNQIDAgMyBmZmZmZmYgMDAwMDAwIDAg
MCAwIDAgMDAwMDAwClNRU1AgMSAzIGZmZmZmZiAwMDAwMDAgMCAwIDAgMCAwMDAwMDAKU1FTUCAy
IDMgZmZmZmZmIDAwMDAwMCAwIDAgMCAwIDAwMDAwMApTUVNQIDMgMyBmZmZmZmYgMDAwMDAwIDAg
MCAwIDAgMDAwMDAwClNRU1AgNCAzIGZmZmZmZiAwMDAwMDAgMCAwIDAgMCAwMDAwMDAKU1FTUCAw
IDQgZmZmZmZmIDAwMDAwMCAwIDAgMCAwIDAwMDAwMApTUVNQIDEgNCBmZmZmZmYgMDAwMDAwIDAg
MCAwIDAgMDAwMDAwClNRU1AgMiA0IGZmZmZmZiAwMDAwMDAgMCAwIDAgMCAwMDAwMDAKU1FTUCAz
IDQgZmZmZmZmIDAwMDAwMCAwIDAgMCAwIDAwMDAwMApTUVNQIDQgNCBmZmZmZmYgMDAwMDAwIDAg
MCAwIDAgMDAwMDAwClNRU1BNSyAwIDAgMAorXCMKU1FTUE1LIDAgMCAxCisKU1FTUE1LIDAgMCAy
CisKU1FTUE1LIDAgMCAzCisKU1FTUE1LIDAgMCA0CisKU1FTUE1LIDAgMCA1CisKU1FTUE1LIDEg
MCAwCitcIwpTUVNQTUsgMSAwIDEKKwpTUVNQTUsgMSAwIDIKKwpTUVNQTUsgMSAwIDMKKwpTUVNQ
TUsgMSAwIDQKKwpTUVNQTUsgMSAwIDUKKwpTUVNQTUsgMiAwIDAKK1wjClNRU1BNSyAyIDAgMQor
ClNRU1BNSyAyIDAgMgorClNRU1BNSyAyIDAgMworClNRU1BNSyAyIDAgNAorClNRU1BNSyAyIDAg
NQorClNRU1BNSyAzIDAgMAorXCMKU1FTUE1LIDMgMCAxCisKU1FTUE1LIDMgMCAyCisKU1FTUE1L
IDMgMCAzCisKU1FTUE1LIDMgMCA0CisKU1FTUE1LIDMgMCA1CisKU1FTUE1LIDQgMCAwCitcIwpT
UVNQTUsgNCAwIDEKKwpTUVNQTUsgNCAwIDIKKwpTUVNQTUsgNCAwIDMKKwpTUVNQTUsgNCAwIDQK
KwpTUVNQTUsgNCAwIDUKKwpTUVNQTUsgMCAxIDAKK1wjClNRU1BNSyAwIDEgMQorClNRU1BNSyAw
IDEgMgorClNRU1BNSyAwIDEgMworClNRU1BNSyAwIDEgNAorClNRU1BNSyAwIDEgNQorClNRU1BN
SyAxIDEgMAorXCMKU1FTUE1LIDEgMSAxCisKU1FTUE1LIDEgMSAyCisKU1FTUE1LIDEgMSAzCisK
U1FTUE1LIDEgMSA0CisKU1FTUE1LIDEgMSA1CisKU1FTUE1LIDIgMSAwCitcIwpTUVNQTUsgMiAx
IDEKKwpTUVNQTUsgMiAxIDIKKwpTUVNQTUsgMiAxIDMKKwpTUVNQTUsgMiAxIDQKKwpTUVNQTUsg
MiAxIDUKKwpTUVNQTUsgMyAxIDAKK1wjClNRU1BNSyAzIDEgMQorClNRU1BNSyAzIDEgMgorClNR
U1BNSyAzIDEgMworClNRU1BNSyAzIDEgNAorClNRU1BNSyAzIDEgNQorClNRU1BNSyA0IDEgMAor
XCMKU1FTUE1LIDQgMSAxCisKU1FTUE1LIDQgMSAyCisKU1FTUE1LIDQgMSAzCisKU1FTUE1LIDQg
MSA0CisKU1FTUE1LIDQgMSA1CisKU1FTUE1LIDAgMiAwCitcIwpTUVNQTUsgMCAyIDEKKwpTUVNQ
TUsgMCAyIDIKKwpTUVNQTUsgMCAyIDMKKwpTUVNQTUsgMCAyIDQKKwpTUVNQTUsgMCAyIDUKKwpT
UVNQTUsgMSAyIDAKK1wjClNRU1BNSyAxIDIgMQorClNRU1BNSyAxIDIgMgorClNRU1BNSyAxIDIg
MworClNRU1BNSyAxIDIgNAorClNRU1BNSyAxIDIgNQorClNRU1BNSyAyIDIgMAorXCMKU1FTUE1L
IDIgMiAxCisKU1FTUE1LIDIgMiAyCisKU1FTUE1LIDIgMiAzCisKU1FTUE1LIDIgMiA0CisKU1FT
UE1LIDIgMiA1CisKU1FTUE1LIDMgMiAwCitcIwpTUVNQTUsgMyAyIDEKKwpTUVNQTUsgMyAyIDIK
KwpTUVNQTUsgMyAyIDMKKwpTUVNQTUsgMyAyIDQKKwpTUVNQTUsgMyAyIDUKKwpTUVNQTUsgNCAy
IDAKK1wjClNRU1BNSyA0IDIgMQorClNRU1BNSyA0IDIgMgorClNRU1BNSyA0IDIgMworClNRU1BN
SyA0IDIgNAorClNRU1BNSyA0IDIgNQorClNRU1BNSyAwIDMgMAorXCMKU1FTUE1LIDAgMyAxCisK
U1FTUE1LIDAgMyAyCisKU1FTUE1LIDAgMyAzCisKU1FTUE1LIDAgMyA0CisKU1FTUE1LIDAgMyA1
CisKU1FTUE1LIDEgMyAwCitcIwpTUVNQTUsgMSAzIDEKKwpTUVNQTUsgMSAzIDIKKwpTUVNQTUsg
MSAzIDMKKwpTUVNQTUsgMSAzIDQKKwpTUVNQTUsgMSAzIDUKKwpTUVNQTUsgMiAzIDAKK1wjClNR
U1BNSyAyIDMgMQorClNRU1BNSyAyIDMgMgorClNRU1BNSyAyIDMgMworClNRU1BNSyAyIDMgNAor
ClNRU1BNSyAyIDMgNQorClNRU1BNSyAzIDMgMAorXCMKU1FTUE1LIDMgMyAxCisKU1FTUE1LIDMg
MyAyCisKU1FTUE1LIDMgMyAzCisKU1FTUE1LIDMgMyA0CisKU1FTUE1LIDMgMyA1CisKU1FTUE1L
IDQgMyAwCitcIwpTUVNQTUsgNCAzIDEKKwpTUVNQTUsgNCAzIDIKKwpTUVNQTUsgNCAzIDMKKwpT
UVNQTUsgNCAzIDQKKwpTUVNQTUsgNCAzIDUKKwpTUVNQTUsgMCA0IDAKK1wjClNRU1BNSyAwIDQg
MQorClNRU1BNSyAwIDQgMgorClNRU1BNSyAwIDQgMworClNRU1BNSyAwIDQgNAorClNRU1BNSyAw
IDQgNQorClNRU1BNSyAxIDQgMAorXCMKU1FTUE1LIDEgNCAxCisKU1FTUE1LIDEgNCAyCisKU1FT
UE1LIDEgNCAzCisKU1FTUE1LIDEgNCA0CisKU1FTUE1LIDEgNCA1CisKU1FTUE1LIDIgNCAwCitc
IwpTUVNQTUsgMiA0IDEKKwpTUVNQTUsgMiA0IDIKKwpTUVNQTUsgMiA0IDMKKwpTUVNQTUsgMiA0
IDQKKwpTUVNQTUsgMiA0IDUKKwpTUVNQTUsgMyA0IDAKK1wjClNRU1BNSyAzIDQgMQorClNRU1BN
SyAzIDQgMgorClNRU1BNSyAzIDQgMworClNRU1BNSyAzIDQgNAorClNRU1BNSyAzIDQgNQorClNR
U1BNSyA0IDQgMAorXCMKU1FTUE1LIDQgNCAxCisKU1FTUE1LIDQgNCAyCisKU1FTUE1LIDQgNCAz
CisKU1FTUE1LIDQgNCA0CisKU1FTUE1LIDQgNCA1CisKU1FMUCAwIDAgMCAxIDEgMCAwIDAKU1FM
UCAwIDAgMSAxIDEgMCAwIDAKU1FMUCAxIDAgMCAxIDEgMCAwIDAKU1FMUCAxIDAgMSAxIDEgMCAw
IDAKU1FMUCAyIDAgMCAxIDEgMCAwIDAKU1FMUCAyIDAgMSAxIDEgMCAwIDAKU1FMUCAzIDAgMCAx
IDEgMCAwIDAKU1FMUCAzIDAgMSAxIDEgMCAwIDAKU1FMUCA0IDAgMCAxIDEgMCAwIDAKU1FMUCA0
IDAgMSAxIDEgMCAwIDAKU1FMUCAwIDEgMCAxIDEgMCAwIDAKU1FMUCAwIDEgMSAxIDEgMCAwIDAK
U1FMUCAxIDEgMCAxIDEgMCAwIDAKU1FMUCAxIDEgMSAxIDEgMCAwIDAKU1FMUCAyIDEgMCAxIDEg
MCAwIDAKU1FMUCAyIDEgMSAxIDEgMCAwIDAKU1FMUCAzIDEgMCAxIDEgMCAwIDAKU1FMUCAzIDEg
MSAxIDEgMCAwIDAKU1FMUCA0IDEgMCAxIDEgMCAwIDAKU1FMUCA0IDEgMSAxIDEgMCAwIDAKU1FM
UCAwIDIgMCAxIDEgMCAwIDAKU1FMUCAwIDIgMSAxIDEgMCAwIDAKU1FMUCAxIDIgMCAxIDEgMCAw
IDAKU1FMUCAxIDIgMSAxIDEgMCAwIDAKU1FMUCAyIDIgMCAxIDEgMCAwIDAKU1FMUCAyIDIgMSAx
IDEgMCAwIDAKU1FMUCAzIDIgMCAxIDEgMCAwIDAKU1FMUCAzIDIgMSAxIDEgMCAwIDAKU1FMUCA0
IDIgMCAxIDEgMCAwIDAKU1FMUCA0IDIgMSAxIDEgMCAwIDAKU1FMUCAwIDMgMCAxIDEgMCAwIDAK
U1FMUCAwIDMgMSAxIDEgMCAwIDAKU1FMUCAxIDMgMCAxIDEgMCAwIDAKU1FMUCAxIDMgMSAxIDEg
MCAwIDAKU1FMUCAyIDMgMCAxIDEgMCAwIDAKU1FMUCAyIDMgMSAxIDEgMCAwIDAKU1FMUCAzIDMg
MCAxIDEgMCAwIDAKU1FMUCAzIDMgMSAxIDEgMCAwIDAKU1FMUCA0IDMgMCAxIDEgMCAwIDAKU1FM
UCA0IDMgMSAxIDEgMCAwIDAKU1FMUCAwIDQgMCAxIDEgMCAwIDAKU1FMUCAwIDQgMSAxIDEgMCAw
IDAKU1FMUCAxIDQgMCAxIDEgMCAwIDAKU1FMUCAxIDQgMSAxIDEgMCAwIDAKU1FMUCAyIDQgMCAx
IDEgMCAwIDAKU1FMUCAyIDQgMSAxIDEgMCAwIDAKU1FMUCAzIDQgMCAxIDEgMCAwIDAKU1FMUCAz
IDQgMSAxIDEgMCAwIDAKU1FMUCA0IDQgMCAxIDEgMCAwIDAKU1FMUCA0IDQgMSAxIDEgMCAwIDAK
U1FDVCAwIDAgMCBBClNRQ1QgMSAwIDAgQgpTUUNUIDIgMCAwIEMKU1FDVCAzIDAgMCAuClNRQ1Qg
NCAwIDAgLgpTUUNUIDAgMSAwIC4KU1FDVCAxIDEgMCBEClNRQ1QgMiAxIDAgRQpTUUNUIDMgMSAw
IEYKU1FDVCA0IDEgMCAuClNRQ1QgMCAyIDAgRwpTUUNUIDEgMiAwIEgKU1FDVCAyIDIgMCAuClNR
Q1QgMyAyIDAgSQpTUUNUIDQgMiAwIEoKU1FDVCAwIDMgMCAuClNRQ1QgMSAzIDAgSwpTUUNUIDIg
MyAwIEwKU1FDVCAzIDMgMCBNClNRQ1QgNCAzIDAgLgpTUUNUIDAgNCAwIC4KU1FDVCAxIDQgMCAu
ClNRQ1QgMiA0IDAgTgpTUUNUIDMgNCAwIE8KU1FDVCA0IDQgMCBQCkVORAo=
"""

class QxwParserTest(TestCase):

    def test_parse(self):
        text = base64.b64decode(''.join(_QXW_FILE_BASE64.split())).decode('utf8')
        model = QxwParser().parse(io.StringIO(text))
        solution = model.to_puz_solution()
        self.assertEqual('ABC...DEF.GH.IJ.KLM...NOP', solution, "converted solution")


class RendererTest(TestCase):

    def test_render(self):
        renderer = puzio.rendering.PuzzleRenderer()
        puz_base64 = """70NBQ1JPU1MmRE9XTgAAjkkXpJfPlgYuMS4zAAAAAAAAAAAAAAAAAAAAAAAFBQoAAQAAAEFCQy4u
LkRFRi5HSC5JSi5LTE0uLi5OT1AtLS0uLi4tLS0uLS0uLS0uLS0tLi4uLS0tAAAAYWxmYQBnb2xm
AGhvdGVsAGJyYXZvAGluZGlhAGNoYXJsaWUAZGVsdGEAZWNobwBqdWxpZXQAZm94dHJvdAAA
"""
        puz_data = base64.b64decode(puz_base64)
        puzzle = puz.load(puz_data)
        html = renderer.render(puzzle)
        print(html)
