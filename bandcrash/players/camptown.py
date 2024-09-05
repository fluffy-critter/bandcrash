""" Player engine for Camptown """

import copy
import logging
import os.path
import shutil
import typing

import camptown

LOGGER = logging.getLogger(__name__)


class Player:
    """ A player using `Camptown <https://github.com/fluffy-critter/camptown>`_. """

    def __init__(self, art_size=200, fullsize_art_size=65536):
        self.art_size = art_size
        self.fullsize_art_size = fullsize_art_size

    @property
    def name(self):
        return 'camptown'

    @property
    def art_rendition_sizes(self):
        return (
            ("1x", self.art_size),
            ("2x", self.art_size*2),
            ("fullsize", self.fullsize_art_size)
        )

    def convert(self, input_dir, output_dir, album, protections, **vars):
        """ Convert a Bandcrash album spec to a Camptown player """
        info: dict[str, typing.Any] = {'tracks': []}

        for key, tgt in (
            ('title', 'title'),
            ('artist', 'artist'),
            ('artwork_preview', 'artwork'),
            ('artist_url', 'artist_url'),
            ('album_url', 'album_url'),
        ):
            if key in album:
                info[tgt] = album[key]

        for track in album['tracks']:
            out: dict[str, typing.Any] = {}
            for key, tgt in (
                ('preview_mp3', 'filename'),
                ('artist', 'artist'),
                ('title', 'title'),
                ('explicit', 'explicit'),
                ('artwork_preview', 'artwork'),
                ('lyrics', 'lyrics'),
                ('about', 'about'),
                ('duration', 'duration'),
            ):
                if key in track:
                    out[tgt] = track[key]
            if track.get('group'):
                out['title'] = f"{track['group']}: {track.get('title', '(no title)')}"
            info['tracks'].append(out)

        theme = album.get('theme', {})
        info['theme'] = copy.deepcopy(theme)

        if 'user_css' in theme:
            shutil.copy(os.path.join(input_dir, info['theme']['user_css']),
                        os.path.join(output_dir, 'user.css'))
            info['theme']['user_css'] = 'user.css'
            protections.add('user.css')

        files = camptown.process(info, output_dir,
                                 footer_urls=[
                                     ('https://fluffy.itch.io/bandcrash', 'Bandcrash')],
                                 file_callback=lambda path: os.path.join(input_dir, path))

        protections |= files
