""" Generate preview and sale versions of albums for itchio et al """
# pylint:disable=too-many-arguments,import-outside-toplevel

import argparse
import base64
import collections
import functools
import json
import logging
import os
import os.path
import shutil
import subprocess
import typing

import jinja2

from . import __version__, images, util

logging.basicConfig(level=logging.INFO, format='%(message)s')
LOGGER = logging.getLogger("__name__")


def check_executable(name):
    """ Check to see if an executable is available """
    try:
        subprocess.run([name], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except FileNotFoundError:
        LOGGER.warning("Warning: encoder binary %s not found", name)
        return False


def parse_args(post_init):
    """ Parse the command line arguments """
    parser = argparse.ArgumentParser(
        description="Generate purchasable albums for independent storefronts")

    parser.add_argument('--version', action='version',
                        version="%(prog)s " + __version__.__version__)

    parser.add_argument('--init', action='store_true',
                        help="Attempt to populate the JSON file automatically")

    parser.add_argument('input_dir', type=str,
                        help="Directory with the source files")
    parser.add_argument('output_dir', type=str, nargs=None if post_init else '?',
                        help="Directory to store the output files into")

    parser.add_argument('--json', '-j', type=str,
                        help="Name of the album JSON file, relative to input_dir",
                        default='album.json')

    def add_encoder(name, executable, info, args):
        """ Add a feature group to the CLI """
        feature = parser.add_mutually_exclusive_group(required=False)
        fname = f'do_{name}'
        feature.add_argument(f'--{name}', dest=fname, action='store_true',
                             help=f"Generate {info}")
        feature.add_argument(f'--no-{name}', dest=fname, action='store_false',
                             help=f"Don't generate {info}")
        feature.set_defaults(**{fname: check_executable(executable)})

        # parser.add_argument(f'--{name}-encoder', type=str,
        #                     help=f"Encoder to use for {info}",
        #                     default=executable)

        parser.add_argument(f'--{name}-encoder-args', type=str,
                            help=f"Arguments to pass to the {info} encoder",
                            default=args)

    add_encoder('preview', 'lame', 'web preview', '-b 32 -V 5 -q 5 -m j')
    add_encoder('mp3', 'lame', 'mp3 album', '-V 0 -q 0 -m j')
    add_encoder('ogg', 'oggenc', 'ogg album', '')
    add_encoder('flac', 'flac', 'flac album', '')

    feature = parser.add_mutually_exclusive_group(required=False)
    feature.add_argument('--cleanup', dest='clean_extra', action='store_true',
                         help="Clean up extra files in the destination directory")
    feature.add_argument('--no-cleanup', dest='clean_extra', action='store_false',
                         help="Keep stale files")
    feature.set_defaults(clean_extra=True)

    parser.add_argument('--butler-target', '-b', type=str,
                        help="Butler push target prefix",
                        default='')

    parser.add_argument('--channel-prefix', '-p', type=str,
                        help="Prefix for the Butler channel name",
                        default='')

    return parser.parse_args()


def run_encoder(outfile, args):
    """ Run an encoder; if the encode process fails, delete the file

    :param str outfile: The output file path
    :param list args: The entire arglist (including output file path)
    """
    try:
        subprocess.run(args, check=True)
    except Exception as err:
        LOGGER.error("Got error encoding %s: %s", outfile, err)
        os.remove(outfile)
        raise
    except KeyboardInterrupt:
        LOGGER.error("User aborted while encoding %s", outfile)
        os.remove(outfile)
        raise


def encode_mp3(in_path, out_path, idx, album, track, encode_args, cover_art=None):
    """ Encode a track as mp3 """
    from mutagen import id3

    if util.is_newer(in_path, out_path):
        run_encoder(out_path, ['lame', *encode_args.split(),
                               in_path, out_path])

    try:
        tags = id3.ID3(out_path)
    except id3.ID3NoHeaderError:
        tags = id3.ID3()

    frames = {
        id3.TYER: str(album['year']) if 'year' in album else None,
        id3.TALB: album.get('title'),

        id3.TPE1: track.get('artist', album.get('artist')),
        id3.TPE2: album.get('artist'),
        id3.TOPE: track.get('cover_of', album.get('cover_of')),

        id3.TRCK: str(idx),
        id3.TIT1: track.get('title'),

        id3.TCON: track.get('genre', album.get('genre')),
        id3.USLT: '\n'.join(track['lyrics']) if 'lyrics' in track else None,

        id3.COMM: track.get('about'),
    }

    for frame, val in frames.items():
        if val:
            tags.setall(frame.__name__, [frame(text=val)])

    if cover_art and 'artwork_path' in track:
        img_data = images.generate_blob(track['artwork_path'], cover_art)
        tags.setall(
            'APIC', [id3.APIC(data=img_data)])

    tags.save(out_path, v2_version=3)
    LOGGER.info("Finished writing %s", out_path)


def tag_vorbis(tags, idx, album, track):
    """ Add a vorbis comment section to an ogg/flac file """
    frames = {
        'ARTIST': track.get('artist', album.get('artist')),
        'ALBUM': album.get('title'),
        'TITLE': track.get('title'),
        'TRACKNUMBER': str(idx),
        'GENRE': track.get('genre', album.get('genre')),
        'LYRICS': '\n'.join(track['lyrics']) if 'lyrics' in track else None,
        'DESCRIPTION': track.get('about'),
    }
    if track.get('cover_of', album.get('cover_of')):
        # Covers are handled weirdly in Vorbiscomment; see https://dogphilosophy.net/?page_id=66
        frames.update({
            'ARTIST': track.get('cover_of', album.get('cover_of')),
            'PERFORMER': track.get('artist', album.get('artist'))
        })

    for frame, val in frames.items():
        if val:
            tags[frame] = val


def get_flac_picture(artwork_path, size):
    """ Generate a FLAC picture frame """
    from mutagen import flac, id3
    img = images.generate_image(artwork_path, size)

    pic = flac.Picture()
    pic.type = id3.PictureType.COVER_FRONT
    pic.width = img.width
    pic.height = img.height
    pic.mime = "image/jpeg"
    pic.data = images.generate_blob(artwork_path, size, ext='jpeg')

    return pic


def encode_ogg(in_path, out_path, idx, album, track, encode_args, cover_art=None):
    """ Encode a track as ogg vorbis """
    from mutagen import oggvorbis

    if util.is_newer(in_path, out_path):
        run_encoder(out_path, ['oggenc', *encode_args.split(),
                               in_path, '-o', out_path])

    tags = oggvorbis.OggVorbis(out_path)
    tag_vorbis(tags, idx, album, track)

    if cover_art and 'artwork_path' in track:
        picture_data = get_flac_picture(
            track['artwork_path'], cover_art).write()
        tags['metadata_block_picture'] = [
            base64.b64encode(picture_data).decode("ascii")]

    tags.save(out_path)
    LOGGER.info("Finished writing %s", out_path)


def encode_flac(in_path, out_path, idx, album, track, encode_args, cover_art=None):
    """ Encode a track as ogg vorbis """
    from mutagen import flac

    if util.is_newer(in_path, out_path):
        run_encoder(out_path, ['flac', *encode_args.split(),
                               in_path, '-f', '-o', out_path])

    tags = flac.FLAC(out_path)
    tag_vorbis(tags.tags, idx, album, track)

    if cover_art and 'artwork_path' in track:
        tags.add_picture(get_flac_picture(track['artwork_path'], cover_art))

    tags.save(out_path)
    LOGGER.info("Finished writing %s", out_path)


def make_web_preview(output_dir, album, protections):
    """ Generate the embedded preview player """
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(os.path.join(
            os.path.dirname(__file__),       'jinja_templates')))

    for tmpl in ('index.html', 'player.js', 'player.css'):
        template = env.get_template(tmpl)
        with open(os.path.join(output_dir, tmpl), 'w', encoding='utf8') as outfile:
            outfile.write(template.render(album=album))
            protections.add(tmpl)

    LOGGER.info("Finished generating web preview at %s", output_dir)


def populate_json_file(input_dir: str, json_path: str):
    """ Attempt to populate the JSON file, creating a new one if it doesn't exist """
    # pylint:disable=too-many-locals,too-many-branches
    try:
        with open(json_path, 'r', encoding='utf8') as stream:
            album = json.load(stream)
            LOGGER.info("Loaded existing %s with %d tracks",
                        json_path, len(album['tracks']))
    except FileNotFoundError:
        LOGGER.info("%s not found, initializing empty file", json_path)
        album = {
            'title': 'ALBUM TITLE',
            'artist': 'ALBUM ARTIST',
            'tracks': []
        }

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
    discovered.sort(key=util.guess_track_title)

    for newtrack in discovered:
        tracks.append({'filename': newtrack})

    # Attempt to derive information that's missing
    for track in tracks:
        if 'filename' in track:
            # Get the title from the track
            if 'title' not in track:
                track['title'] = util.guess_track_title(
                    track['filename'])[1].title()

            # Check for any matching lyric .txt files
            if 'lyrics' not in track:
                basename, _ = os.path.splitext(track['filename'])
                lyrics_txt = f'{basename}.txt'
                if os.path.isfile(lyrics_txt):
                    track['lyrics'] = lyrics_txt

            # Check for any matching track artwork
            if 'artwork' not in track:
                for art_file in art:
                    art_basename, _ = os.path.splitext(art_file)
                    if basename.lower() == art_basename.lower():
                        track['artwork'] = art_file
                        art.remove(art_file)
                        break

    # Try to guess some album art
    if 'artwork' not in album:
        for art_file in art:
            basename, _ = os.path.splitext(art_file)
            name_heuristic = False
            for check in ('cover', 'album', 'artwork'):
                if check in basename.lower():
                    name_heuristic = True
            if name_heuristic:
                album['artwork'] = art_file
                art.remove(art_file)
                break
    if 'artwork' not in album and len(art) == 1:
        (album['artwork'],) = art

    with open(json_path, 'w', encoding='utf8') as output:
        json.dump(album, output, indent=4)

    return album


def clean_subdir(path: str, allowed: typing.Set[str]):
    """ Clean up a subdirectory of extraneous files """
    LOGGER.debug("Allowed in %s: %s", path, allowed)
    for file in os.scandir(path):
        if file.name not in allowed:
            LOGGER.info("Removing extraneous file %s", file.path)
            if file.is_dir():
                shutil.rmtree(file)
            else:
                os.remove(file)


def main():
    """ Main entry point """
    # pylint:disable=too-many-branches,too-many-statements,too-many-locals
    options = parse_args(False)

    json_path = os.path.join(options.input_dir, options.json)

    protections: typing.Dict[str, typing.Set[str]
                             ] = collections.defaultdict(set)

    if options.init:
        album = populate_json_file(options.input_dir, json_path)
        if not options.output_dir:
            return

    options = parse_args(True)
    with open(json_path, 'r', encoding='utf8') as json_file:
        album = json.load(json_file)

    formats = set()
    for subdir in ('preview', 'mp3', 'ogg', 'flac'):
        if getattr(options, f'do_{subdir}'):
            formats.add(subdir)
            os.makedirs(os.path.join(
                options.output_dir, subdir), exist_ok=True)

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
        protections['preview'] |= set(album['artwork_preview'])

    for idx, track in enumerate(album['tracks'], start=1):
        title = track.get('title', f'track {idx}')
        track['title'] = title

        base_filename = f'{idx:02d} '
        if 'artist' in track:
            base_filename += f"{track['artist']} - "
        base_filename += title
        base_filename = util.slugify_filename(base_filename)

        def out_path(fmt, ext=None):
            # pylint:disable=cell-var-from-loop
            protections[fmt].add(f'{base_filename}.{ext or fmt}')
            return os.path.join(options.output_dir, fmt, f'{base_filename}.{ext or fmt}')

        input_filename = os.path.join(options.input_dir, track['filename'])

        track_art = track.get('artwork', album.get('artwork'))
        if track_art:
            track_art = os.path.join(options.input_dir, track_art)
            track['artwork_path'] = track_art

        if 'lyrics' in track and isinstance(track['lyrics'], str):
            track['lyrics'] = util.read_lines(
                os.path.join(options.input_dir, track['lyrics']))

        # generate preview track, if desired
        if options.do_preview and not track.get('hidden') and track.get('preview', True):
            if 'artwork' in track:
                track['artwork_preview'] = gen_art_preview(
                    os.path.join(options.input_dir, track['artwork']))
                protections['preview'] |= set(track['artwork_preview'])
            track['preview_mp3'] = f'{base_filename}.mp3'
            encode_mp3(input_filename,
                       out_path('preview', 'mp3'),
                       idx, album, track, options.preview_encoder_args,
                       cover_art=300)

        if options.do_mp3:
            encode_mp3(input_filename,
                       out_path('mp3'),
                       idx, album, track, options.mp3_encoder_args, cover_art=1500)

        if options.do_ogg:
            encode_ogg(input_filename,
                       out_path('ogg'),
                       idx, album, track, options.ogg_encoder_args, cover_art=1500)

        if options.do_flac:
            encode_flac(input_filename,
                        out_path('flac'),
                        idx, album, track, options.flac_encoder_args, cover_art=1500)

    if options.do_preview:
        make_web_preview(os.path.join(options.output_dir,
                         'preview'), album, protections['preview'])

    if options.clean_extra:
        for target in formats:
            clean_subdir(os.path.join(options.output_dir, target),
                         protections[target])

    if options.butler_target:
        for target in formats:
            channel = f'{options.channel_prefix}{target}'
            subprocess.run(['butler', 'push', os.path.join(
                options.output_dir, target), f'{options.butler_target}:{channel}'],
                check=True)

    LOGGER.info("Done")


if __name__ == '__main__':
    main()
