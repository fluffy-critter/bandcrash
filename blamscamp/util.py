""" Common functions """
import logging
import os
import os.path
import re
import typing

import chardet
from slugify import Slugify  # type:ignore

LOGGER = logging.getLogger(__name__)


def is_newer(src: str, dest: str) -> bool:
    """ Returns whether the source file is newer than the destination file """
    if not os.path.isfile(dest):
        return True
    return os.stat(src).st_mtime > os.stat(dest).st_mtime


def slugify_filename(fname: str) -> str:
    """ Generate a safe filename """
    fier = Slugify()
    fier.separator = '-'
    fier.safe_chars = ' ._'
    fier.max_length = 64
    return fier(fname)


def guess_track_title(fname: str) -> typing.Tuple[int, str]:
    """ Get the track number and title from a filename """
    basename, _ = os.path.splitext(fname)
    if match := re.match(r'([0-9]+)([^0-9]*)$', basename):
        return int(match.group(1)), match.group(2).strip().title()
    return 0, basename.title()


def read_lines(fname: str) -> typing.List[str]:
    """ Read a text file into a list of strings, with encoding detection """
    try:
        with open(fname, 'r', encoding='utf-8') as file:
            return [line.rstrip() for line in file]
    except UnicodeDecodeError:
        LOGGER.debug("File %s wasn't valid utf-8; detecting encoding", fname)
        with open(fname, 'rb') as rawfile:
            data = rawfile.read()
        encoding = chardet.detect(data)['encoding']
        LOGGER.debug("%s appears to be %s", fname, encoding)
        with open(fname, 'r', encoding=encoding) as file:
            return [line.rstrip() for line in file]
