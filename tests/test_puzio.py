import tempfile
import puzio
from puzio import PuzzleCreator
from unittest import TestCase
import argparse
import os.path
import logging
import tests


tests.configure_logging()
_log = logging.getLogger(__name__)


def namespace(**kwargs) -> argparse.Namespace:
    parser = puzio.create_arg_parser()
    ns = parser.parse_args([])
    for k, v in kwargs.items():
        ns.__setattr__(k, v)
    return ns


class TestPuzzleCreator(TestCase):

    def test_create(self):
        with tempfile.TemporaryDirectory() as tempdir:
            creator = PuzzleCreator(tempdir)
            output_pathname = creator.create(namespace())
            self.assertIs(True, output_pathname and True)
            _log.debug("file length: %s", os.path.getsize(output_pathname))
            self.assertTrue(os.path.isfile(output_pathname))
