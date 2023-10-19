""" Common functions """
import functools
import logging
import os
import os.path
import re
import string
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
    basename, _ = os.path.splitext(os.path.basename(fname))
    if match := re.match(r'([0-9]+)([^0-9]*)$', basename):
        return int(match.group(1)), string.capwords(match.group(2).strip())
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


def make_absolute_path(base_file):
    """
    Returns a function to provide an absolute path for the specified
    filename based on a base path
    """
    if os.path.isdir(base_file):
        dirname = base_file
    else:
        dirname = os.path.dirname(base_file)

    return lambda path: (path if os.path.isabs(path)
                         else os.path.normpath(os.path.join(dirname, path)))


def make_relative_path(base_file):
    """
    Returns a function to provide a path relative to the specified filename
    or directory
    """

    if os.path.isdir(base_file):
        dirname = base_file
    else:
        dirname = os.path.dirname(base_file)

    def normalize(path):
        abspath = path if os.path.isabs(
            path) else os.path.normpath(os.path.join(dirname, path))
        return os.path.relpath(abspath, dirname)
    return normalize


def populate_album(input_dir: str, album: typing.Optional[dict] = None):
    """ Attempt to populate the JSON file, creating a new one if it doesn't exist """
    # pylint:disable=too-many-locals,too-many-branches

    if album is None:
        album = {
            'title': 'ALBUM TITLE',
            'artist': 'ALBUM ARTIST',
            'tracks': []
        }
    elif 'tracks' not in album:
        album['tracks'] = []

    tracks: typing.List[typing.Dict[str, typing.Any]] = album['tracks']

    # already-known tracks
    known_audio = {track['filename']
                   for track in tracks if 'filename' in track}

    # newly-discovered tracks
    discovered = []
    art = set()
    for file in os.scandir(input_dir):
        _, ext = os.path.splitext(file.name)
        if file.name not in known_audio and ext.lower() in ('.wav', '.aif', '.aiff', '.flac'):
            discovered.append(file.name)
        if ext.lower() in ('.jpg', '.jpeg', '.png'):
            art.add(file.name)

    # sort the tracks by any discovered numerical prefix
    discovered.sort(key=guess_track_title)

    for newtrack in discovered:
        tracks.append({'filename': newtrack})

    # Attempt to derive information that's missing
    for track in tracks:
        if 'filename' in track:
            # Get the title from the track
            if 'title' not in track:
                track['title'] = guess_track_title(
                    track['filename'])[1].title()

            # Check for any matching lyric .txt files
            if 'lyrics' not in track:
                basename, _ = os.path.splitext(track['filename'])
                lyrics_txt = f'{basename}.txt'
                if os.path.isfile(lyrics_txt):
                    track['lyrics'] = lyrics_txt

            # Check for any matching track artwork
            if 'artwork' not in track:
                for art_file in art.copy():
                    art_basename, _ = os.path.splitext(art_file)
                    if basename.lower() == art_basename.lower():
                        track['artwork'] = art_file
                        art.remove(art_file)
                        break

    # Try to guess some album art
    if 'artwork' not in album:
        for art_file in art.copy():
            basename, _ = os.path.splitext(art_file)
            name_heuristic = False
            for check in ('cover', 'album', 'artwork'):
                if check in basename.lower():
                    name_heuristic = True
            if name_heuristic:
                album['artwork'] = art_file

    return album


@functools.lru_cache()
def ffmpeg_path():
    """ Get the path to the bundled FFMPEG binary """
    import pyffmpeg
    ffmpeg = pyffmpeg.FFmpeg().get_ffmpeg_bin()
    LOGGER.debug("Got ffmpeg binary: %s", ffmpeg)
    return ffmpeg
