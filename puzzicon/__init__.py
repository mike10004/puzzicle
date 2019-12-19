#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from collections import defaultdict
import fnmatch
import logging
from typing import List, Tuple, Dict, Callable, Set, Iterable, NamedTuple, FrozenSet
import unidecode

unicode_normalize = unidecode.unidecode

_log = logging.getLogger(__name__)

_IDENTITY = lambda x: x


def _create_constant_callable(retval):
    def _constant(*args, **kwargs):
        return retval

    return _constant


_EMPTY_SET = frozenset()
_CALLABLE_TRUE = _create_constant_callable(True)
_CALLABLE_FALSE = _create_constant_callable(False)
_ALPHABET_ALPHA = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
_ALPHABET_NUMERIC = "0123456789"
_ALPHABET_ALPHANUMERIC = _ALPHABET_ALPHA + _ALPHABET_NUMERIC
_REGEX_NONCHARMATCH = {
    'alpha': '[^A-Za-z]',
    'numeric': '[^0-9]',
    'alphanumeric': '[^A-Za-z0-9]',
}


def get_alphabet(allowed: str) -> str:
    if allowed == 'alpha':
        return _ALPHABET_ALPHA
    elif allowed == 'numeric':
        return _ALPHABET_NUMERIC
    elif allowed == 'alphanumeric':
        return _ALPHABET_ALPHANUMERIC
    raise ValueError(str(allowed))


def get_regex_noncharmatch(allowed: str) -> str:
    return _REGEX_NONCHARMATCH[allowed]


def _contains_nonalphabet(letters, allowed):
    for l in letters:
        if l not in get_alphabet(allowed):
            return True
    return False


class InvalidPuzzemeException(Exception):
    pass

class Puzzeme(NamedTuple):

    """Thing that might be an answer to a clue in a puzzle."""

    canonical: str
    renderings: FrozenSet[str]

    @staticmethod
    def create(rendering: str, *args, **kwargs):
        renderings = [rendering]
        if args:
            renderings += list(args)
        renderings = tuple(map(str.strip, renderings))
        canonical = None
        allowed = kwargs.get('allowed', 'alpha')
        for rendering in renderings:
            assert rendering, "lexeme rendering must contain non-whitespace"
            normalized = Puzzeme.canonicalize(rendering, allowed=allowed)
            assert canonical is None or normalized == canonical, "all renderings must have same canonical form"
            canonical = normalized
        if not canonical:
            raise InvalidPuzzemeException("canonical form of lexeme must contain non-whitespace: {}".format(repr(rendering)[:64]))
        return Puzzeme(canonical, frozenset(renderings))

    @staticmethod
    def canonicalize(rendering: str, allowed: str='alpha', preserve: Set[str]=_EMPTY_SET) -> str:
        if _contains_nonalphabet(rendering, allowed):
            rendering = unicode_normalize(rendering)
        canonical = re.sub(get_regex_noncharmatch(allowed), '', rendering).strip()
        if 'case' not in preserve:
            canonical = canonical.upper()
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
    by_canonical: Dict[str, List[Puzzeme]] = defaultdict(list)
    for rendering in ifile:
        try:
            p = Puzzeme.create(rendering)
            by_canonical[p.canonical].append(p)
        except Exception as e:
            if intolerables is not None:
                intolerables.append((rendering, e))
    if intolerables and len(intolerables):
        _log.info("%s items in input are intolerable", len(intolerables))
    items = []
    for variants in by_canonical.values():
        assert len(variants) == sum([len(v.renderings) for v in variants])
        for variant in variants:
            assert len(variant.renderings) == 1
        renderings = [list(variant.renderings)[0] for variant in variants]
        items.append(Puzzeme.create(*renderings))
    return frozenset(items)


def _standard_cleaner(line: str) -> str:
    line = line.strip()
    if line.lower().endswith("'s"):
        line = line[:-2]
    return line


def read_puzzeme_set(pathname: str, cleaner: Callable[[str], str]=None):
    if cleaner is None:
        cleaner = _standard_cleaner
    if cleaner == 'identity':
        cleaner = lambda x: x
    with open(pathname, 'r') as ifile:
        cleaned = map(cleaner, ifile)
        return create_puzzeme_set(cleaned)


def load_default_puzzemes():
    return read_puzzeme_set('/usr/share/dict/words')
