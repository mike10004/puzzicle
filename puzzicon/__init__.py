#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from collections import defaultdict
import fnmatch
import logging
from typing import List, Tuple, Dict, Callable, Set, Iterable
import unidecode

unicode_normalize = unidecode.unidecode

_log = logging.getLogger(__name__)

_IDENTITY = lambda x: x


def _create_constant_callable(retval):
    def _constant(*args, **kwargs):
        return retval

    return _constant


_CALLABLE_TRUE = _create_constant_callable(True)
_CALLABLE_FALSE = _create_constant_callable(False)
_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def _contains_nonalphabet(letters):
    for l in letters:
        if l not in _ALPHABET:
            return True
    return False


class Puzzeme(tuple):

    """Thing that might be an answer to a clue in a puzzle."""

    canonical, renderings = None, None

    def __new__(cls, rendering: str, *args):
        renderings = [rendering]
        if args:
            renderings += list(args)
        renderings = tuple(map(str.strip, renderings))
        canonical = None
        for rendering in renderings:
            assert rendering, "lexeme rendering must contain non-whitespace"
            normalized = Puzzeme.canonicalize(rendering)
            assert canonical is None or normalized == canonical, "all renderings must have same canonical form"
            canonical = normalized
        assert canonical is not None
        assert canonical, "canonical form of lexeme must contain non-whitespace: {}".format(repr(rendering)[:64])
        items = [canonical] + list(renderings)
        instance = super(Puzzeme, cls).__new__(cls, items)
        instance.canonical = canonical
        instance.renderings = renderings
        return instance

    @staticmethod
    def canonicalize(rendering):
        if _contains_nonalphabet(rendering):
            rendering = unicode_normalize(rendering)
        canonical = re.sub('[^A-Za-z]', '', rendering).strip().upper()
        return canonical

    def stature(self):
        """Return the length of the canonical form of this instance."""
        return len(self.canonical)


class Filters(object):

    def __init__(self):
        raise NotImplementedError("this class provides static methods")

    @classmethod
    def stature(cls, int_predicate: Callable[[int], bool]):
        if isinstance(int_predicate, int):
            value = int_predicate
            int_predicate = lambda n: n == value
        return lambda p: int_predicate(p.stature())

    @classmethod
    def conjoin(cls, predicates: Iterable[Callable[[Puzzeme], bool]]):
        if not predicates:
            return _CALLABLE_TRUE

        def _and(puzzeme):
            for predicate in predicates:
                if not predicate(puzzeme):
                    return False
            return True

        return _and

    @classmethod
    def canonical(cls, predicate):
        if not callable(predicate):
            # assume we're looking for literal match
            literal = Puzzeme.canonicalize(predicate)
            predicate = lambda c: c == literal
        return lambda p: predicate(p.canonical)

    @classmethod
    def canonical_wildcard(cls, pattern):
        return Filters.canonical(lambda c: fnmatch.fnmatch(c, pattern))

    @classmethod
    def canonical_regex(cls, pattern):
        return Filters.canonical(lambda c: re.fullmatch(pattern, c) is not None)


class Puzzarian(object):
    """Librarian who can find the puzzemes you desire."""

    def __init__(self, puzzeme_set: Set[Puzzeme]):
        self.puzzemes = frozenset(puzzeme_set)
        self.puzzeme_dict = {}
        for p in self.puzzemes:
            self.puzzeme_dict[p.canonical] = p

    def search(self, predicates, offset=None, limit=None):
        xform = _IDENTITY if offset is None and limit is None else lambda f: (list(f))[offset:offset + limit]
        filtered = filter(Filters.conjoin(predicates), self.puzzemes)
        return xform(filtered)

    def has_canonical(self, word):
        """Check for an exact match."""
        return Puzzeme.canonicalize(word) in self.puzzeme_dict


def create_puzzeme_set(ifile: Iterable[str], intolerables=None):
    by_canonical = defaultdict(list)
    for rendering in ifile:
        try:
            p = Puzzeme(rendering)
            by_canonical[p.canonical].append(p)
        except Exception as e:
            if intolerables is not None:
                intolerables.append((rendering, e))
    if intolerables and len(intolerables):
        _log.info("%s items in input are intolerable", len(intolerables))
    items = []
    for variants in by_canonical.values():
        assert len(variants) == sum([len(v.renderings) for v in variants])
        renderings = [variant.renderings[0] for variant in variants]
        items.append(Puzzeme(*renderings))
    return frozenset(items)


def read_puzzeme_set(pathname):
    with open(pathname, 'r') as ifile:
        return create_puzzeme_set(ifile)


def load_default_puzzemes():
    return read_puzzeme_set('/usr/share/dict/words')
