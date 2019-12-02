#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import io
import sys
import logging
import unittest
import puzzicon
from puzzicon import Puzzeme, Puzzarian
import tests

tests.configure_logging()

_DEFAULT_PUZZEME_SET = puzzicon.load_default_puzzemes()
_SIMPLE_PUZZEME_SET = puzzicon.create_puzzeme_set(['foo', 'bar', 'baz', 'gaw'])


class TestModuleMethods(unittest.TestCase):

    def test_create_puzzeme_set_multiple_renderings(self):
        wordlist = """\
apple
cant
can't
one
on e
pumpkin"""
        wordlist_entries = wordlist.split("\n")
        puzzemes = puzzicon.create_puzzeme_set(wordlist_entries)
        self.assertIn(Puzzeme('apple'), puzzemes)
        self.assertIn(Puzzeme('cant', 'can\'t'), puzzemes)
        self.assertIn(Puzzeme('one', 'on e'), puzzemes)
        self.assertIn(Puzzeme('pumpkin'), puzzemes)
        self.assertEqual(4, len(puzzemes))

    def test_read_default(self):
        self.assertNotEqual(0, len(_DEFAULT_PUZZEME_SET), "no puzzemes in default set")

    def test_create_puzzeme_set_filelike(self):
        wordlist = """apples
peaches
pumpkin"""
        ifile = io.StringIO(wordlist)
        puzzemes = puzzicon.create_puzzeme_set(ifile)
        self.assertSetEqual({Puzzeme('apples'), Puzzeme('peaches'), Puzzeme('pumpkin')}, puzzemes)

    def test_alphabet(self):
        self.assertEqual(26 * 2, len(puzzicon._ALPHABET))
        self.assertEqual(26 * 2, len(set(puzzicon._ALPHABET)))


class TestPuzzeme(unittest.TestCase):

    def test_canonicalize(self):
        c = Puzzeme.canonicalize("puzzle's\n")
        self.assertEqual('PUZZLES', c)

    def test_canonicalize_diacritics(self):
        c = Puzzeme.canonicalize(u'Málaga')
        self.assertEqual('MALAGA', c)

    def test_create(self):
        p = Puzzeme('a')
        self.assertEqual('A', p.canonical)
        self.assertEqual(('a',), p.renderings)

    def test_create_diacritics(self):
        p = Puzzeme(u'café')
        self.assertEqual('CAFE', p.canonical)

    def test_equals_tuple(self):
        self.assertEqual(('ABC', 'abc'), Puzzeme('abc'))
        self.assertEqual(('ABC', 'abc', 'ab c'), Puzzeme('abc', 'ab c'))

    def test_multiple_renderings(self):
        p = Puzzeme("itis", "it is")
        self.assertEqual("ITIS", p.canonical)
        self.assertTupleEqual(('itis', 'it is'), p.renderings)

    def test_equals(self):
        p = Puzzeme('abc')
        q = Puzzeme('abc')
        r = Puzzeme('def')
        self.assertEqual(p, q)
        self.assertNotEqual(q, r)



class TestPuzzerarian(unittest.TestCase):

    def test_search_many(self):
        p = Puzzarian(_DEFAULT_PUZZEME_SET)
        results = p.search([lambda p: p.canonical.startswith('PUZZ')])
        results = list(results)
        self.assertEqual(10, len(results))

    def test_search_one(self):
        p = Puzzarian(_DEFAULT_PUZZEME_SET)
        results = p.search([puzzicon.Filters.canonical('puzzle')], 0, 1)
        self.assertIsInstance(results, list)
        self.assertEqual(1, len(results))
        self.assertTupleEqual(('puzzle',), results[0].renderings)

    def test_has_canonical(self):
        p = Puzzarian(_SIMPLE_PUZZEME_SET)
        self.assertTrue(p.has_canonical('baz'))
        self.assertTrue(p.has_canonical('Foo'))
        self.assertFalse(p.has_canonical('oranges'))


class TestFilters(unittest.TestCase):

    def test_canonical_literal(self):
        f = puzzicon.Filters.canonical('foo')
        self.assertTrue(f(Puzzeme('Foo')))

    def test_canonical_regex(self):
        f = puzzicon.Filters.canonical_regex(r'PU.ZLE')
        self.assertTrue(f(Puzzeme('puzzle')))
        self.assertFalse(f(Puzzeme('puzzles')))
        self.assertTrue(f(Puzzeme('pubzle')))

    def test_canonical_wildcard_q(self):
        f = puzzicon.Filters.canonical_wildcard('PU?ZLE')
        self.assertTrue(f(Puzzeme('puzzle')))
        self.assertFalse(f(Puzzeme('puzle')))
        self.assertFalse(f(Puzzeme('puzzles')))
        self.assertTrue(f(Puzzeme('pubzle')))

    def test_canonical_regex_star(self):
        f = puzzicon.Filters.canonical_wildcard('PU*ZLE')
        self.assertTrue(f(Puzzeme('puzzle')))
        self.assertTrue(f(Puzzeme('puzle')))
        self.assertFalse(f(Puzzeme('puzzles')))
        self.assertTrue(f(Puzzeme('pubzle')))
        self.assertTrue(f(Puzzeme('puabczle')))

