from unittest import TestCase
from puzzicon.grid import Location, Entry, GridModel, Square
# noinspection PyProtectedMember
from puzzicon.grid import _ACROSS, _DOWN, _DARK

class SquareTest(TestCase):

    def test_dark(self):
        s = Square(0, 0)
        self.assertFalse(s.dark())
        t = Square(0, 1, _DARK)
        self.assertTrue(t.dark())

    def test_equals(self):
        self.assertEqual(Square(0, 0, '_'), Square(0, 0, '_'))
        self.assertNotEqual(Square(1, 0, '_'), Square(0, 0, '_'))
        self.assertNotEqual(Square(1, 1, '_'), Square(1, 1, '.'))
        self.assertEqual(Square(2, 2), Square(2, 2))
        self.assertNotEqual(Square(3, 3), Square(3, 4))

    def test___str__(self):
        self.assertEqual("(0, 0, '_')", str(Square(0, 0, '_')))

    def test_list_equals(self):
        self.assertListEqual([Square(0, 0)], [Square(0, 0)])


class LocationTest(TestCase):

    def test_equals(self):
        x = Location('across', 1, 0, 0)
        t = ('across', 1, 0, 0)
        self.assertTupleEqual(t, x)
        self.assertEqual(t, x)

    def test_across(self):
        a = Location(_ACROSS, 1, 2, 3)
        b = Location.across(1, 2, 3)
        self.assertEqual(a, b)

    def test_down(self):
        a = Location(_DOWN, 1, 2, 3)
        b = Location.down(1, 2, 3)
        self.assertEqual(a, b)

class GridModelTest(TestCase):

    def test_build(self):
        g = GridModel.build("__.___.__")
        self.assertEqual(3, g.num_rows)
        self.assertEqual(3, g.num_cols)
        self.assertEqual(Square(0, 1, '_'), g.square(0, 1))
        self.assertEqual(Square(0, 2, '.'), g.square(0, 2))
        self.assertEqual('_', g.value(0, 0))
        one_across = g.until_dead_across(0, 0)
        self.assertListEqual([Square(0, 0, '_'), Square(0, 1, '_')], one_across)
        one_down = g.until_dead_down(0, 0)
        self.assertListEqual([Square(0, 0, '_'), Square(1, 0, '_')], one_down)
        two_down = g.until_dead_down(0, 1)
        self.assertListEqual([Square(0, 1, '_'), Square(1, 1, '_'), Square(2, 1, '_')], two_down)

    def test_entries_3x3_1(self):
        g = GridModel.build("__.___.__")
        e = g.entries()
        self.assertEqual(6, len(e))
        self.assertEqual(('across', 1, 0, 0), e[0].location)
        self.assertEqual(('down', 1, 0, 0), e[1].location)
        self.assertEqual(('down', 2, 0, 1), e[2].location)
        self.assertEqual(('across', 3, 1, 0), e[3].location)
        self.assertEqual(('down', 4, 1, 2), e[4].location)
        self.assertEqual(('across', 5, 2, 1), e[5].location)
        self.assertListEqual([Square(0, 1, '_'), Square(1, 1, '_'), Square(2, 1, '_')], e[2].squares)