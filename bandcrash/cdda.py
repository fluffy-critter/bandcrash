""" bin/cue generator """

import concurrent.futures
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


def cue_quote(text, force_quote=False):
    """ Quote a string for a cue file """

    # normalize whitespace
    text = ' '.join(str(text).split())

    # replace " with '' because some tools are really silly
    text = text.replace('"', "''")

    # remove nonprintable characters
    text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)

    # quote values with spaces
    if force_quote or ' ' in text:
        text = f'"{text}"'

    return text


def parse_time(samples):
    """ Convert a sample count to minutes/seconds/frames """
    frames = int(samples*FRAMES_PER_SECOND/SAMPLES_PER_SECOND)
    seconds, frames = divmod(frames, FRAMES_PER_SECOND)
    minutes, seconds = divmod(seconds, 60)
    return minutes, seconds, frames


def format_time(samples):
    """ format a timecode in MM:SS:FF """
    mm, ss, ff = parse_time(samples)
    return f'{mm:02}:{ss:02}:{ff:02}'


class CDWriter:
    """ class for building the .bin and .cue file """
    # pylint:disable=too-many-instance-attributes

    def __init__(self, input_dir, output_dir, album, protections, fname='album.bin'):
        # pylint:disable=too-many-positional-arguments,too-many-arguments
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.album = album
        self.protections = protections

        # array of (track_dict, offset, duration)
        self.tracks = []

        self.timecode = 0   # current timecode, in samples

        self.protections.add(fname)
        self.bin_fname = fname
        self.bin_path = os.path.join(self.output_dir, fname)

        # create the empty binfile
        with open(self.bin_path, 'wb') as _:
            pass

    def add_track(self, track):
        """ Add a track to the bin and cue """

        idx = len(self.tracks) + 1
        LOGGER.info("Encoding track %d - %s", idx,
                    track.get('title', '(no title)'))

        start_timecode = self.timecode
        track_duration = 0

        if track.get('filename'):
            infile = os.path.join(self.input_dir, track['filename'])
            target = os.path.join(self.output_dir, f'track-{idx}.tmp.pcm')
            LOGGER.debug("Converting %s to %s as raw", infile, target)
            try:
                util.run_encoder(infile, target, [
                                 '-f', 's16le', '-acodec', 'pcm_s16le', '-ar', '44100'])
                with open(self.bin_path, 'ab') as binfile:
                    with open(target, 'rb') as tempdata:
                        size = 0
                        while chunk := tempdata.read(16384):
                            binfile.write(chunk)
                            size += len(chunk)
                        if size % BYTES_PER_SAMPLE != 0:
                            raise RuntimeError(
                                f"{size} bytes is not a multiple of {BYTES_PER_SAMPLE}")
                        self.timecode += size // BYTES_PER_SAMPLE
                        track_duration = int(
                            size/(BYTES_PER_SAMPLE*SAMPLES_PER_SECOND) + 0.5)
            finally:
                os.remove(target)

        self.tracks.append((track, start_timecode, track_duration))

    def commit(self, leadout=2*SAMPLES_PER_SECOND):
        """ commit the .bin, with a specified leadout size """
        with open(self.bin_path, 'ab') as binfile:
            binfile.write(bytearray(leadout * BYTES_PER_SAMPLE))

    def write_cue(self, fname='album.cue'):
        """ write the text cuefile """
        LOGGER.info("Writing text-format cue file to %s", fname)

        with open(os.path.join(self.output_dir, fname), 'w',
                  encoding='iso-8859-1', errors='replace', newline='\r\n') as cue:
            def writeln(line):
                print(line, file=cue)

            def write_props(props, indent=''):
                """ write an array of properties, formatted as key, value, force_quote """
                for key, value, force_quote in props:
                    if value is not None:
                        writeln(
                            f'{indent}{key} {cue_quote(value, force_quote)}')

            write_props([
                ('PERFORMER', self.album.get('artist'), True),
                ('SONGWRITER', self.album.get('composer'), True),
                ('TITLE', self.album.get('title'), True),
                ('CATALOG', self.album.get('upc'), False),
                ('REM GENRE', self.album.get('genre'), True),
                ('REM DATE', self.album.get('year'), False),
                ('REM COMMENT', f'Authored by Bandcrash {__version__}', True),
            ])

            writeln(f'FILE "{self.bin_fname}" BINARY')

            def get_prop(track, key, fallback=False):
                if not track:
                    return None
                return track.get(key, self.album.get(key) if fallback else None)

            for idx, (track, offset, _) in enumerate(self.tracks, start=1):
                writeln(f"  TRACK {idx:02} AUDIO")
                write_props([
                    ('TITLE', get_prop(track, 'title'), True),
                    ('PERFORMER', get_prop(track, 'artist', True), True),
                    ('SONGWRITER', get_prop(track, 'composer', True), True),
                    ('REM GENRE', get_prop(track, 'genre'), True),
                    ('ISRC', get_prop(track, 'isrc'), False),
                    ('INDEX 01', format_time(offset), False)
                ], indent='    ')

            writeln(f"REM LEAD-OUT {format_time(self.timecode)}")

        self.protections.add(fname)

    def write_kunaki_cue(self, fname='kunaki.cue'):
        """ write the kunaki-format cuefile """
        LOGGER.info("Writing Kunaki-format cue file to %s", fname)

        # Kunaki's proprietary CUE format is semi-documented at
        # https://gist.github.com/LoneRabbit/36f2a74c27a7d6a3b443b44d27fd2702
        # from which this code is adapted. It appears to be a subset of the
        # raw data stored in a CD's TOC.
        #
        # Each track record looks like:
        #
        # <ctrl><adr> <tt> <ii> <xx> 00 <mm> <ss> <ff>
        #
        # where ctrl is 4 bits: quad 0 copy-allowed pre-emphasis
        # adr = 1 for track info, 3 for EOF marker
        # xx = lead in/out? generated pregap maybe?
        # mm/ss/ff: timecode in minutes/seconds/frames (75 frames per second)
        #
        # In Kunaki's generated cuefiles, ctrl|adr is always 01 for tracks, 03 for EOF
        # and xx is 1 for lead-in and lead-out, 0 otherwise
        #
        # The puzzling thing is that their TOC shows the actual track starts
        # as offset by the pregap size, but there is no corresponding pregap
        # within the .bin file (which Kunaki erroneously calls an "iso").
        # Baking in a pregap as one would expect causes the tracks to be offset
        # by that amount. So there seems to be some magic pregap logic happening
        # on Kunaki's side.

        pregap = 2*SAMPLES_PER_SECOND

        with open(os.path.join(self.output_dir, fname), 'wb') as cue:
            def write_item(adr, track, index, xx, timecode):
                mm, ss, ff = parse_time(timecode)
                cue.write(struct.pack('B'*8,
                                      adr, track, index, xx, 0, mm, ss, ff))

            # pregap
            write_item(1, 0, 0, 1, 0)
            write_item(1, 1, 0, 0, 0)

            # each track, offset by the pregap size
            for tnum, (_, offset, _) in enumerate(self.tracks, start=1):
                write_item(1, tnum, 1, 0, offset + pregap)

            # lead-out
            write_item(1, 0xAA, 1, 1, self.timecode + pregap)

            # EOF marker
            cue.write(struct.pack('B', 3))

        self.protections.add(fname)

    def write_tsv(self, fname='tracklist.tsv'):
        """ Write out an easily-parsed track listing file """
        LOGGER.info("Writing TSV file to %s", fname)

        with open(os.path.join(self.output_dir, fname), 'w', encoding='utf-8') as tsv:
            print('Index\tTitle\tDuration\tStart Time\tPerformer\tComposer', file=tsv)

            def get_prop(track, key):
                return ' '.join(track.get(key, self.album.get(key, '')).split())
            for idx, (track, offset, duration) in enumerate(self.tracks, start=1):
                minutes, seconds = divmod(duration, 60)
                print('\t'.join([
                    str(idx),
                    get_prop(track, 'title'),
                    f'{int(minutes)}:{int(seconds+0.5):02}',
                    format_time(offset),
                    get_prop(track, 'artist'),
                    get_prop(track, 'composer')
                ]), file=tsv)

        self.protections.add(fname)


def encode(album, input_dir, output_dir, protections, pool):
    """ Run the bincue output process """
    processor = CDWriter(input_dir, output_dir, album, protections)
    futures: list[concurrent.futures.Future] = []

    def task(wait_for, func, *args):
        if wait_for:
            wait_for.result()
        func(*args)

    def submit(wait_for, func, *args):
        future = pool.submit(task, wait_for, func, *args)
        futures.append(future)
        return future

    last_step = None

    for track in album['tracks']:
        last_step = submit(last_step, processor.add_track, track)

    last_step = submit(last_step, processor.commit)

    # these can all run in parallel, so they don't need to update last_step
    for step in (processor.write_cue,
                 processor.write_kunaki_cue,
                 processor.write_tsv):
        submit(last_step, step)

    return futures
