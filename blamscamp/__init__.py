""" Generate preview and sale versions of albums for itchio et al """
# pylint:disable=too-many-arguments

import argparse
import json
import os
import os.path
import subprocess

import jinja2
from slugify import Slugify

from . import __version__

slugify_filename = Slugify()
slugify_filename.separator = '-'
slugify_filename.safe_chars = ' .-'
slugify_filename.max_length = 64


def parse_args(*args):
    """ Parse the command line arguments """
    parser = argparse.ArgumentParser(
        description="Generate purchasable albums for independent storefronts")

    parser.add_argument('--version', action='version',
                        version="%(prog)s " + __version__.__version__)

    parser.add_argument('input_dir', type=str,
                        help="Directory with the source files")
    parser.add_argument('output_dir', type=str,
                        help="Directory to store the output files into")

    parser.add_argument('--json', '-j', type=str,
                        help="Name of the album JSON file, relative to input_dir",
                        default='album.json')

    parser.add_argument('--player-encoder-args', type=str,
                        help="MP3 lameenc arguments for the web-based player",
                        default='-V 5 -q 5 -m j')
    parser.add_argument('--mp3-encoder-args', type=str,
                        help="MP3 lameenc arguments for the purchased mp3 version",
                        default='-V 0 -q 0 -m j')
    parser.add_argument('--ogg-encoder-args', type=str,
                        help="oggenc arguments for the purchased ogg version",
                        default='')

    parser.add_argument('--butler-target', '-b', type=str,
                        help="Butler push target prefix",
                        default='')

    return parser.parse_args(*args)


def encode_mp3(in_path, out_path, idx, album, track, encode_args):
    """ Encode a track as mp3 """
    from mutagen import id3

    subprocess.run(['lame', *encode_args.split(),
                    in_path, out_path,
                   '--tn', str(idx)], check=True)

    tags = id3.ID3(out_path, v2_version=3)

    frames = {
        id3.TYER: str(album['year']) if 'year' in album else None,
        id3.TALB: album.get('title'),

        id3.TPE1: track.get('artist', album.get('artist')),
        id3.TPE2: album.get('artist'),

        id3.USLT: '\n'.join(track['lyrics']) if 'lyrics' in track else None,
    }

    for frame, val in frames.items():
        if val:
            tags.setall(frame.__name__, [frame(text=val)])

    tags.save()


def encode_ogg(in_path, out_path, idx, album, track, encode_args):
    """ Encode a track as ogg vorbis """
    from mutagen import ogg

    subprocess.run(['oggenc', *encode_args.split(),
        in_path, '-o', out_path,
        '-N', str(idx)], check=True)

    # TODO: add tags

def encode_flac(in_path, out_path, idx, album, track):
    """ Encode a track as ogg vorbis """

    # TODO


def make_player(output_dir, album):
    """ Generate the embedded preview player """
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(os.path.join(
            os.path.dirname(__file__),       'jinja_templates')))

    for tmpl in ('index.html', 'player.js', 'player.css'):
        template = env.get_template(tmpl)
        with open(os.path.join(output_dir, tmpl), 'w', encoding='utf8') as outfile:
            outfile.write(template.render(album=album))


def main():
    options = parse_args()

    json_path = os.path.join(options.input_dir, options.json)
    with open(json_path, 'r', encoding='utf8') as json_file:
        album = json.load(json_file)

    for subdir in ('player', 'mp3', 'ogg', 'flac'):
        os.makedirs(os.path.join(options.output_dir, subdir), exist_ok=True)

    album_artist = album.get('artist')
    album_title = album.get('title')

    for idx, track in enumerate(album['tracks'], start=1):
        title = track.get('title', f'track {idx}')

        base_filename = f'{idx:02d} '
        if 'artist' in track:
            base_filename += f"{track['artist']} - "
        base_filename += title
        base_filename = slugify_filename(base_filename)

        def out_path(fmt, ext=None):
            return os.path.join(options.output_dir, fmt, f'{base_filename}.{ext or fmt}')

        input_filename = os.path.join(options.input_dir, track['filename'])

        # generate preview track, if desired
        if not track.get('hidden') and track.get('preview', True):
            track['preview_mp3'] = f'{base_filename}.mp3'
            encode_mp3(input_filename,
                       out_path('player', 'mp3'),
                       idx, album, track, options.player_encoder_args)

        encode_mp3(input_filename,
                   out_path('mp3'),
                   idx, album, track, options.mp3_encoder_args)

        encode_ogg(input_filename,
                   out_path('ogg'),
                   idx, album, track, options.ogg_encoder_args)

        encode_flac(input_filename,
                    out_path('flac'),
                    idx, album, track)

    make_player(os.path.join(options.output_dir, 'player'), album)

if __name__ == '__main__':
    main()
