from unittest import TestCase
import puzio
import re

class TestModule(TestCase):

    def test_timestamp(self):
        t = puzio.timestamp()
        patt = r'\d{8}T\d{6}'
        self.assertTrue(re.fullmatch(patt, t), f"timestamp {t} does not match pattern {patt}")
