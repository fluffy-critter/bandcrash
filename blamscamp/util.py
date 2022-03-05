""" Common functions """
from slugify import Slugify  # type:ignore


def slugify_filename(fname: str) -> str:
    """ Generate a safe filename """
    fier = Slugify()
    fier.separator = '-'
    fier.safe_chars = ' ._'
    fier.max_length = 64
    return fier(fname)
