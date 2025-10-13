""" bin/cue generator """

import logging
import os
import os.path
import re
import struct

from . import util

try:
    from .__version__ import __version__
except ImportError:
    __version__ = '(unknown)'

LOGGER = logging.getLogger(__name__)

BYTES_PER_SAMPLE = 4
SAMPLES_PER_SECOND = 44100
FRAMES_PER_SECOND = 75
LEAD_IN = 0x0
LEAD_OUT = 0xAA


def cue_quote(text):
    """ Quote a string for a cue file """

    # normalize whitespace
    text = ' '.join(text.split())

    # replace " with '' because some tools are really silly
    text = text.replace('"', "''")

    # remove nonprintable characters
    text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)

    return f'"{text}"'


def get_position(samples):
    """ Convert a sample count to minutes/seconds/frames """
    frames = int(samples*FRAMES_PER_SECOND/SAMPLES_PER_SECOND)
    seconds, frames = divmod(frames, FRAMES_PER_SECOND)
    minutes, seconds = divmod(seconds, 60)
    return minutes, seconds, frames


class CDWriter:
    """ class for building the .bin and .cue file """
    # pylint:disable=too-many-instance-attributes

    def __init__(self, input_dir, output_dir, basename, album, protections):
        # pylint:disable=too-many-positional-arguments,too-many-arguments
        self.protections = protections

        bin_filename = f'{basename}.bin'
        cue_filename = f'{basename}.cue'
        bcue_filename = f'{basename}.kunaki.cue'
        protections.add(bin_filename)
        protections.add(cue_filename)
        protections.add(bcue_filename)

        self.bin_path = os.path.join(output_dir, bin_filename)
        self.cue_path = os.path.join(output_dir, cue_filename)
        self.bcue_path = os.path.join(output_dir, bcue_filename)

        self.input_dir = input_dir
        self.output_dir = output_dir
        self.timecode = 0   # current timecode, in samples
        self.artist = None

        LOGGER.info("bin=%s", self.bin_path)
        LOGGER.info("cue=%s", self.cue_path)

        # create the empty files
        with open(self.cue_path, 'w', encoding='iso-8859-1') as cue:
            if 'artist' in album:
                cue.write(f'PERFORMER {cue_quote(album["artist"])}\n')
                self.artist = album['artist']
            if 'title' in album:
                cue.write(f'TITLE {cue_quote(album["title"])}\n')
            if 'genre' in album:
                cue.write(f"REM GENRE {album['genre']}\n")
            if 'year' in album:
                cue.write(f"REM DATE {album['year']}\n")
            cue.write(f'REM COMMENT "Authored by Bandcrash {__version__}"\n')
            cue.write(f'FILE "{basename}.bin" BINARY\n')

        with open(self.bin_path, 'wb') as binfile:
            pass

        # track, idx, minutes, seconds, frames, pregap
        self.tracks = []

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

            if not self.timecode:
                # Generate a pregap rather than baking it in
                cue.write('    PREGAP 00:02:00\n')
                self.tracks.append((LEAD_IN, 0, 0, 0, 0))
                self.tracks.append((1, 0, 0, 0, 0))
                self.timecode = 2 * SAMPLES_PER_SECOND

            minutes, seconds, frames = get_position(self.timecode)

            cue.write(f'    INDEX 01 {minutes:02}:{seconds:02}:{frames:02}\n')
            self.tracks.append((idx, 1, minutes, seconds, frames))

            # convert and append the data
            if track.get('filename'):
                infile = os.path.join(self.input_dir, track['filename'])
                target = os.path.join(self.output_dir, f'track-{idx}.tmp.pcm')
                LOGGER.debug("Converting %s to %s as raw", infile, target)
                try:
                    util.run_encoder(infile, target, [
                                     '-f', 's16le', '-acodec', 'pcm_s16le'])
                    with self.bin as binfile:
                        with open(target, 'rb') as tempdata:
                            while chunk := tempdata.read(16384):
                                binfile.write(chunk)
                                self.timecode += len(chunk) // BYTES_PER_SAMPLE
                finally:
                    os.remove(target)

    def commit(self):
        """ Close the session """

        # add a 5-second lead-out to the last track
        minutes, seconds, frames = get_position(self.timecode)
        self.tracks.append((LEAD_OUT, 1, minutes, seconds, frames))

        with self.cue as cue:
            cue.write(f"REM LEAD-OUT {minutes:02}:{seconds:02}:{frames:02}\n")
        with self.bin as binfile:
            binfile.write(bytearray(5 * SAMPLES_PER_SECOND * BYTES_PER_SAMPLE))

        # Kunaki's proprietary CUE format semi-documented at
        # https://gist.github.com/LoneRabbit/36f2a74c27a7d6a3b443b44d27fd2702
        # from which this code is adapted
        #
        # <ctrl><adr> <tt> <ii> <xx> 00 <mm> <ss> <ff>
        # where ctrl is 4 bits: quad 0 copy-allowed pre-emphasis
        # adr = 1 for track info, 3 for EOF marker
        # xx = lead in/out? generated pregap maybe?
        # mm/ss/ff: timecode in minutes/seconds/frames (75 frames per second)
        #
        # In Kunaki's generated cuefiles, ctrl|adr is always 01 for tracks, 03 for EOF
        # and xx is 1 for lead-in and lead-out, 0 otherwise
        #
        # Puzzlingly, track 1 index 0 indicates 2 seconds of lead-in on the track
        # but there is no corresponding blank data in the binfile.
        #
        # Someday it would be nice to add pregap-hidden audio and index markers
        # but that will have to wait until Kunaki actually documents their format,
        # which doesn't seem likely to happen any time soon.
        with open(self.bcue_path, 'wb') as bcue:
            for track, index, minutes, seconds, frames in self.tracks:
                ctrl = 0
                adr = 1
                if track in (LEAD_IN, LEAD_OUT):
                    xx = 1
                else:
                    xx = 0

                LOGGER.debug("ctrl=%d adr=%d track=%d idx=%d xx=%d m=%d s=%d f=%d",
                             ctrl, adr, track, index, xx, minutes, seconds, frames)

                bcue.write(struct.pack('BBBBBBBB',
                                       1, track, index, xx,
                                       0, minutes, seconds, frames))

            # EOF marker
            bcue.write(struct.pack('B', 3))


def encode(album, input_dir, output_dir, protections):
    """ Run the bincue output process """
    processor = CDWriter(input_dir, output_dir, 'album', album, protections)
    for idx, track in enumerate(album['tracks'], start=1):
        processor.add_track(idx, track)
    processor.commit()
