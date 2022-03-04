""" Generate preview and sale versions of albums for itchio et al """
# pylint:disable=too-many-arguments,import-outside-toplevel

import argparse
import functools
import json
import os
import os.path
import subprocess
import typing

import jinja2

from . import __version__, images
from .util import slugify_filename


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

    parser.add_argument('--preview-encoder-args', type=str,
                        help="MP3 lameenc arguments for the web-based preview player",
                        default='-b 32 -V 5 -q 5 -m j')
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


def encode_mp3(in_path, out_path, idx, album, track, encode_args, cover_art=None):
    """ Encode a track as mp3 """
    import mutagen
    from mutagen import id3

    subprocess.run(['lame', *encode_args.split(),
                    in_path, out_path], check=True)

    try:
        tags = id3.ID3(out_path)
    except id3.ID3NoHeaderError:
        tags = id3.ID3()

    frames = {
        id3.TYER: str(album['year']) if 'year' in album else None,
        id3.TALB: album.get('title'),

        id3.TPE1: track.get('artist', album.get('artist')),
        id3.TPE2: album.get('artist'),

        id3.TRCK: str(idx),

        id3.USLT: '\n'.join(track['lyrics']) if 'lyrics' in track else None,
    }

    for frame, val in frames.items():
        if val:
            tags.setall(frame.__name__, [frame(text=val)])
    print(tags)

    if cover_art and 'artwork_path' in track:
        img_data = images.generate_blob(track['artwork_path'], cover_art)
        tags.setall(
            'APIC', [id3.APIC(data=img_data)])

    tags.save(out_path, v2_version=3)


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


def make_web_preview(output_dir, album):
    """ Generate the embedded preview player """
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(os.path.join(
            os.path.dirname(__file__),       'jinja_templates')))

    for tmpl in ('index.html', 'player.js', 'player.css'):
        template = env.get_template(tmpl)
        with open(os.path.join(output_dir, tmpl), 'w', encoding='utf8') as outfile:
            outfile.write(template.render(album=album))


def main():
    """ Main entry point """
    options = parse_args()

    json_path = os.path.join(options.input_dir, options.json)
    with open(json_path, 'r', encoding='utf8') as json_file:
        album = json.load(json_file)

    for subdir in ('preview', 'mp3', 'ogg', 'flac'):
        os.makedirs(os.path.join(options.output_dir, subdir), exist_ok=True)

    @functools.lru_cache()
    def gen_art_preview(in_path: str) -> typing.Tuple[str, str]:
        """ Generate web preview art for the given file

        :param str in_path: Input path of the source file
        :param str out_dir: Output directory

        :returns: tuple of the 1x and 2x renditions of the artwork
        """
        out_dir = os.path.join(options.output_dir, 'preview')
        return (images.generate_rendition(in_path, out_dir, 150),
                images.generate_rendition(in_path, out_dir, 300))

    if 'artwork' in album:
        album['artwork_preview'] = gen_art_preview(
            os.path.join(options.input_dir, album['artwork']))

    for idx, track in enumerate(album['tracks'], start=1):
        title = track.get('title', f'track {idx}')

        base_filename = f'{idx:02d} '
        if 'artist' in track:
            base_filename += f"{track['artist']} - "
        base_filename += title
        base_filename = slugify_filename(base_filename)

        def out_path(fmt, ext=None):
            # pylint:disable=cell-var-from-loop
            return os.path.join(options.output_dir, fmt, f'{base_filename}.{ext or fmt}')

        input_filename = os.path.join(options.input_dir, track['filename'])

        track_art = track.get('artwork', album.get('artwork'))
        if track_art:
            track_art = os.path.join(options.input_dir, track_art)
            track['artwork_path'] = track_art

        if 'lyrics' in track and isinstance(track['lyrics'], str):
            with open(os.path.join(options.input_dir, track['lyrics']), 'r') as lyricfile:
                track['lyrics'] = [line.rstrip() for line in lyricfile]

        # generate preview track, if desired
        if not track.get('hidden') and track.get('preview', True):
            if 'artwork' in track:
                track['preview_artwork'] = gen_art_preview(
                    os.path.join(options.input_dir, track['artwork']))
            track['preview_mp3'] = f'{base_filename}.mp3'
            encode_mp3(input_filename,
                       out_path('preview', 'mp3'),
                       idx, album, track, options.preview_encoder_args,
                       cover_art=300)

        encode_mp3(input_filename,
                   out_path('mp3'),
                   idx, album, track, options.mp3_encoder_args, cover_art=1500)

        encode_ogg(input_filename,
                   out_path('ogg'),
                   idx, album, track, options.ogg_encoder_args)

        encode_flac(input_filename,
                    out_path('flac'),
                    idx, album, track)

    make_web_preview(os.path.join(options.output_dir, 'preview'), album)


if __name__ == '__main__':
    main()
