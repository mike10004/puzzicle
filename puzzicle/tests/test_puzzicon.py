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

SIMPLE_PUZZEME_SET = None
DEFAULT_PUZZEME_SET = None

def default_puzzemes():
    global DEFAULT_PUZZEME_SET
    if DEFAULT_PUZZEME_SET is None:
        DEFAULT_PUZZEME_SET = puzzicon.load_default_puzzemes()
    return DEFAULT_PUZZEME_SET

def simple_puzzemes():
    global SIMPLE_PUZZEME_SET
    if SIMPLE_PUZZEME_SET is None:
        SIMPLE_PUZZEME_SET = puzzicon.create_puzzeme_set(['foo', 'bar', 'baz', 'gaw'])
    return SIMPLE_PUZZEME_SET

class ModuleMethodsTest(unittest.TestCase):

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
        self.assertIn(Puzzeme.create('apple'), puzzemes)
        self.assertIn(Puzzeme.create('cant', 'can\'t'), puzzemes)
        self.assertIn(Puzzeme.create('one', 'on e'), puzzemes)
        self.assertIn(Puzzeme.create('pumpkin'), puzzemes)
        self.assertEqual(4, len(puzzemes))

    def test_read_default(self):
        self.assertNotEqual(0, len(default_puzzemes()), "no puzzemes in default set")

    def test_create_puzzeme_set_filelike(self):
        wordlist = """apples
peaches
pumpkin"""
        ifile = io.StringIO(wordlist)
        puzzemes = puzzicon.create_puzzeme_set(ifile)
        self.assertSetEqual({Puzzeme.create('apples'), Puzzeme.create('peaches'), Puzzeme.create('pumpkin')}, puzzemes)

    def test_alphabet(self):
        self.assertEqual(26 * 2, len(puzzicon._ALPHABET_ALPHA))
        self.assertEqual(26 * 2, len(set(puzzicon._ALPHABET_ALPHA)))

    def test_read_clean(self):
        puzzemes = puzzicon.read_puzzeme_set('/usr/share/dict/words')
        self.assertNotIn(Puzzeme.create('BURNSS'), puzzemes)


class PuzzemeTest(unittest.TestCase):

    def test_create_alphanumeric(self):
        p = Puzzeme.create('a1', allowed='alphanumeric')
        self.assertEqual('A1', p.canonical)

    def test_canonicalize(self):
        c = Puzzeme.canonicalize("puzzle's\n")
        self.assertEqual('PUZZLES', c)

    def test_canonicalize_diacritics(self):
        c = Puzzeme.canonicalize(u'Málaga')
        self.assertEqual('MALAGA', c)

    def test_create(self):
        p = Puzzeme.create('a')
        self.assertEqual('A', p.canonical)
        self.assertSetEqual({'a'}, p.renderings)

    def test_create_diacritics(self):
        p = Puzzeme.create(u'café')
        self.assertEqual('CAFE', p.canonical)

    def test_equals_tuple(self):
        self.assertTupleEqual(('ABC', frozenset({'abc'})), Puzzeme.create('abc'))
        self.assertTupleEqual(('ABC', frozenset({'abc', 'ab c'})), Puzzeme.create('abc', 'ab c'))

    def test_multiple_renderings(self):
        p = Puzzeme.create("itis", "it is")
        self.assertEqual("ITIS", p.canonical)
        self.assertSetEqual({'itis', 'it is'}, p.renderings)

    def test_equals(self):
        p = Puzzeme.create('abc')
        q = Puzzeme.create('abc')
        r = Puzzeme.create('def')
        self.assertEqual(p, q)
        self.assertNotEqual(q, r)



class PuzzarianTest(unittest.TestCase):

    def test_search_many(self):
        p = Puzzarian(default_puzzemes())
        results = p.search([lambda z: z.canonical.startswith('PUZZ')])
        results = list(results)
        self.assertEqual(7, len(results), "expected number of PUZZ* matches; check dict file to confirm")

    def test_search_one(self):
        p = Puzzarian(default_puzzemes())
        results = p.search([puzzicon.Filters.canonical('puzzle')], 0, 1)
        self.assertIsInstance(results, list)
        self.assertEqual(1, len(results))
        self.assertSetEqual({'puzzle'}, results[0].renderings)

    def test_has_canonical(self):
        p = Puzzarian(simple_puzzemes())
        self.assertTrue(p.has_canonical('baz'))
        self.assertTrue(p.has_canonical('Foo'))
        self.assertFalse(p.has_canonical('oranges'))


class TestFilters(unittest.TestCase):

    def test_canonical_literal(self):
        f = puzzicon.Filters.canonical('foo')
        self.assertTrue(f(Puzzeme.create('Foo')))

    def test_canonical_regex(self):
        f = puzzicon.Filters.canonical_regex(r'PU.ZLE')
        self.assertTrue(f(Puzzeme.create('puzzle')))
        self.assertFalse(f(Puzzeme.create('puzzles')))
        self.assertTrue(f(Puzzeme.create('pubzle')))

    def test_canonical_wildcard_q(self):
        f = puzzicon.Filters.canonical_wildcard('PU?ZLE')
        self.assertTrue(f(Puzzeme.create('puzzle')))
        self.assertFalse(f(Puzzeme.create('puzle')))
        self.assertFalse(f(Puzzeme.create('puzzles')))
        self.assertTrue(f(Puzzeme.create('pubzle')))

    def test_canonical_regex_star(self):
        f = puzzicon.Filters.canonical_wildcard('PU*ZLE')
        self.assertTrue(f(Puzzeme.create('puzzle')))
        self.assertTrue(f(Puzzeme.create('puzle')))
        self.assertFalse(f(Puzzeme.create('puzzles')))
        self.assertTrue(f(Puzzeme.create('pubzle')))
        self.assertTrue(f(Puzzeme.create('puabczle')))

