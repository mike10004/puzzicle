#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
import os
from typing import TextIO


def timestamp(dt=None):
    dt = dt or datetime.datetime.now()
    dt_str = dt.isoformat(timespec='seconds')
    dt_str = dt_str.replace(':', '')
    dt_str = dt_str.replace('-', '')
    return dt_str


def read_lines(ifile: TextIO, include_whitespace_only: bool=False, comment_leader: str=None):
    lines = []
    lines_with_endings = [line for line in ifile]
    for i, line in enumerate(lines_with_endings):
        if line[-1] == os.linesep:
            line = line[:-1]
        if comment_leader is not None and line.lstrip().startswith(comment_leader):
            continue
        if include_whitespace_only or line.strip():
            lines.append(line)
    return lines


