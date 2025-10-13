""" Common functions """
import functools
import hashlib
import logging
import os
import os.path
import re
import string
import subprocess
import typing

import chardet
from unidecode import unidecode

LOGGER = logging.getLogger(__name__)


def is_newer(src: str, dest: str) -> bool:
    """ Returns whether the source file is newer than the destination file """
    if not os.path.isfile(dest):
        return True
    return os.stat(src).st_mtime > os.stat(dest).st_mtime


def slugify_filename(fname: str) -> str:
    """ Generate a safe filename """

    # remove control characters
    fname = fname.translate(dict.fromkeys(range(32)))

    # translate unicode to ascii
    fname = unidecode(fname)

    # collapse/convert whitespace
    fname = ' '.join(fname.split())

    # convert runs of problematic characters to -
    fname = re.sub(r'[\-\$/\\:\<\>\*\"\|&]+', '-', fname)

    return fname


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

    if not base_file:
        # We don't have a reference path so we can't really do anything
        return lambda path: path

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

    if not base_file:
        # We don't have a reference path so we can't really do anything
        return lambda path: path

    if os.path.isdir(base_file):
        dirname = base_file
    else:
        dirname = os.path.dirname(base_file)

    def normalize(path):
        abspath = os.path.realpath(path) if os.path.isabs(
            path) else os.path.realpath(os.path.join(dirname, path))
        try:
            relpath = os.path.relpath(abspath, dirname)
        except ValueError:
            # path couldn't be made relative
            return abspath

        # See if we're escaping all the way back out to root, in which case
        # there's no reasont to use a relative path.
        if os.path.commonpath([abspath, base_file]) == os.path.sep:
            return abspath

        return relpath
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


def get_audio_duration(path):
    """ Abuse `ffmpeg -i` to get the audio duration, in seconds

    Would normally use pyffmpeg.FFprobe but see
    https://github.com/deuteronomy-works/pyffmpeg/issues/667
    """
    output = subprocess.run([ffmpeg_path(),
                            '-hide_banner',
                             '-i', path], check=False,
                            capture_output=True,
                            creationflags=getattr(
        subprocess, 'CREATE_NO_WINDOW', 0),
    )

    text = output.stderr.decode().splitlines()
    for line in text:
        if match := re.search(r'Duration: *([0-9.:]+)', line):
            total = 0.0
            for chunk in match.group(1).split(':'):
                total = total*60 + float(chunk)
            return total
    return 0


def text_to_lines(text):
    """ Convert a string or a list of strings into a single string, newline-separated """
    if isinstance(text, list):
        return '\n'.join(text)
    return text


def file_md5(fname):
    """ Get the md5sum of a file """
    md5 = hashlib.md5()
    with open(fname, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            md5.update(chunk)
    return md5.hexdigest()


def run_encoder(infile, outfile, args):
    """ Run an encoder; if the encode process fails, delete the file

    :param str outfile: The output file path
    :param list args: The entire arglist (including output file path)
    """

    if not os.path.isfile(infile):
        raise FileNotFoundError(f"Can't encode {outfile}: {infile} not found")

    if is_newer(infile, outfile):
        try:
            subprocess.run([ffmpeg_path(),
                            '-hide_banner', '-loglevel', 'error',
                            '-i', infile,
                            *args,
                            '-y', outfile], check=True,
                           capture_output=True,
                           creationflags=getattr(
                               subprocess, 'CREATE_NO_WINDOW', 0),
                           )
        except subprocess.CalledProcessError as err:
            os.remove(outfile)
            raise RuntimeError(
                f'Error {err.returncode} encoding {outfile}: {err.output}') from err
        except KeyboardInterrupt as err:
            os.remove(outfile)
            raise RuntimeError(
                f'User aborted while encoding {outfile}') from err
