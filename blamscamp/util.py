""" Common functions """


def slugify_filename(fname: str) -> str:
    """ Generate a safe filename """
    from slugify import Slugify  # type:ignore
    fier = Slugify()
    fier.separator = '-'
    fier.safe_chars = ' ._'
    fier.max_length = 64
    return fier(fname)
