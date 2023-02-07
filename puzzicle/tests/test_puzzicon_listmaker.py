#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import io
import sys
import logging
import unittest
from unittest import TestCase
import puzzicon
from puzzicon import Puzzeme, Puzzarian
import tests
from puzzicon.listmaker import ListMaker, make_cleaner
tests.configure_logging()


class ListMakerTest(TestCase):

    def test_preserve_case(self):
        actual = ListMaker(clean=None, preserve_case=True).transliterate('101st Airborne Division')
        self.assertEqual('101stAirborneDivision', actual)

    def test_transliterate(self):
        clean_ranked = '^([^@]+)(@\d+)?\s*$'
        cases = [
            # line, clean_expr, expected
            ('punch a clock@51', clean_ranked, 'PUNCHACLOCK'),
            ('101st Airborne Division', clean_ranked, '101STAIRBORNEDIVISION'),
        ]
        for line, clean_expr, expected in cases:
            with self.subTest():
                clean = make_cleaner(clean_expr)
                listmaker = ListMaker(clean)
                actual = listmaker.transliterate(line)
                self.assertEqual(expected, actual, "from {} using clean expression {}".format(line, clean_expr))