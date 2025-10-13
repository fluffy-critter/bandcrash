""" bin/cue generator """

import logging
import os
import os.path
import re

from . import util

try:
    from .__version__ import __version__
except ImportError:
    __version__ = '(unknown)'

LOGGER = logging.getLogger(__name__)

BYTES_PER_SAMPLE = 4
SAMPLES_PER_SECOND = 44100
FRAMES_PER_SECOND = 75


def cue_quote(text):
    """ Quote a string for a cue file """

    # normalize whitespace
    text = ' '.join(text.split())

    # replace " with '' because some tools are really silly
    text = text.replace('"', "''")

    # remove nonprintable characters
    text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)

    return f'"{text}"'


class CDWriter:
    """ class for building the .bin and .cue file """

    def __init__(self, input_dir, output_dir, basename, album, protections):
        # pylint:disable=too-many-positional-arguments,too-many-arguments
        bin_filename = f'{basename}.bin'
        cue_filename = f'{basename}.cue'
        protections.add(bin_filename)
        protections.add(cue_filename)

        self.bin_path = os.path.join(output_dir, bin_filename)
        self.cue_path = os.path.join(output_dir, cue_filename)
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.length = 0   # current .bin length in samples
        self.artist = None

        LOGGER.info("bin=%s", self.bin_path)
        LOGGER.info("cue=%s", self.cue_path)

        # create the empty files
        with open(self.cue_path, 'w', encoding='iso-8859-1') as _:
            pass

        with self.cue as cue:
            if 'genre' in album:
                cue.write(f"REM GENRE {album['genre']}\n")
            if 'year' in album:
                cue.write(f"REM DATE {album['year']}\n")
            cue.write(f'REM COMMENT "Bandcrash {__version__}"\n')
            if 'artist' in album:
                cue.write(f'PERFORMER {cue_quote(album["artist"])}\n')
                self.artist = album['artist']
            if 'title' in album:
                cue.write(f'TITLE {cue_quote(album["title"])}\n')
            cue.write(f'FILE "{basename}.bin" BINARY\n')

    @property
    def cue(self):
        """ returns a handle for the cuefile """
        return open(self.cue_path, 'a',
                    encoding='iso-8859-1',
                    errors='replace',
                    newline='\r\n')

    @property
    def bin(self):
        """ returns a handle for the binfile """
        return open(self.bin_path, 'ab')

    def add_track(self, idx, track):
        """ Add a track to the bin and cue """

        LOGGER.info("Encoding track %d - %s", idx,
                    track.get('title', '(no title)'))

        with self.cue as cue:
            cue.write(f"  TRACK {idx:02} AUDIO\n")

            if 'title' in track:
                cue.write(f'    TITLE {cue_quote(track.get('title'))}\n')

            if self.artist or 'artist' in track:
                cue.write(
                    f'    PERFORMER {cue_quote(track.get("artist", self.artist))}\n')

            if not self.length:
                # create the binfile with the 2-second pregap
                self.length = 2 * SAMPLES_PER_SECOND
                with open(self.bin_path, 'wb') as binfile:
                    binfile.write(bytearray(self.length * BYTES_PER_SAMPLE))

                cue.write('    INDEX 00 00:00:00\n')

            frames = int(self.length*FRAMES_PER_SECOND/SAMPLES_PER_SECOND)
            seconds, frames = divmod(frames, FRAMES_PER_SECOND)
            minutes, seconds = divmod(seconds, 60)

            cue.write(f'    INDEX 01 {minutes:02}:{seconds:02}:{frames:02}\n')

            # convert and append the data
            if track.get('filename'):
                infile = os.path.join(self.input_dir, track['filename'])
                target = os.path.join(self.output_dir, f'track-{idx}.tmp.pcm')
                LOGGER.debug("Converting %s to %s as raw", infile, target)
                try:
                    util.run_encoder(infile, target, [
                                     '-f', 's16be', '-acodec', 'pcm_s16be'])
                    with self.bin as binfile:
                        with open(target, 'rb') as tempdata:
                            while chunk := tempdata.read(16384):
                                binfile.write(chunk)
                                self.length += len(chunk) // BYTES_PER_SAMPLE
                finally:
                    os.remove(target)


def encode(album, input_dir, output_dir, protections):
    """ Run the bincue output process """
    processor = CDWriter(input_dir, output_dir, 'album', album, protections)
    for idx, track in enumerate(album['tracks'], start=1):
        processor.add_track(idx, track)
