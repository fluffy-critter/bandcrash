""" Generate preview and sale versions of albums for itchio et al """
# pylint:disable=too-many-arguments,import-outside-toplevel,too-many-positional-arguments

import argparse
import base64
import collections
import concurrent.futures
import copy
import functools
import itertools
import json
import logging
import os
import os.path
import shutil
import subprocess
import typing

from . import cdda, images, util

try:
    from .__version__ import __version__
except ImportError:
    __version__ = '(unknown)'

LOGGER = logging.getLogger(__name__)

DIST_TARGETS = ('mp3', 'ogg', 'flac', 'preview')
ALL_TARGETS = ('mp3', 'ogg', 'flac', 'preview', 'cdda')


def wait_futures(futures):
    """ Waits for some futures to complete. If any exceptions happen, they propagate up. """
    for task in concurrent.futures.as_completed(futures):
        task.result()


def generate_art_tags(album, track, size, make_tag_func):
    """ Generate a set of art tags for a track

    :param dict album: The album's data
    :param dict track: The track's data
    :param int size: The maximum rendition size
    :param make_tag_func: Function to create the tag from the rendition
    """
    from mutagen import id3
    art_tags = []
    for container, picture_type, desc in (
        (album, id3.PictureType.COVER_FRONT, 'Front Cover'),
        (track, id3.PictureType.OTHER, 'Song Cover')
    ):
        if 'artwork_path' in container:
            try:
                img = images.generate_image(container['artwork_path'], size)
                art_tags.append(make_tag_func(img, picture_type, desc))
            except Exception:  # pylint:disable=broad-exception-caught
                LOGGER.exception(
                    "Got an error converting image %s", container['artwork_path'])

    return art_tags


def encode_mp3(in_path, out_path, idx, album, track, encode_args, cover_art=None):
    """ Encode a track as mp3

    :param str in_path: Input file path
    :param str out_path: Output file path
    :param str idx: Track number
    :param dict album: Album metadata
    :param dict track: Track metadata
    :param str encode_args: Arguments to pass along to FFmpeg
    :param str cover_art: Artwork rendition size
    """
    from mutagen import id3

    util.run_encoder(in_path, out_path, encode_args + ['-c:a', 'libmp3lame'])

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

        id3.TRCK: str(idx) if idx is not None else None,
        id3.TIT1: track.get('group'),
        id3.TIT2: track_tag_title(track),

        id3.TCON: track.get('genre', album.get('genre')),
        id3.TCOM: track.get('composer', album.get('composer')),
        id3.USLT: util.text_to_lines(track.get('lyrics')),

        id3.COMM: track.get('comment'),
    }

    for frame, val in frames.items():
        if val:
            LOGGER.debug("%s: Setting %s to %s", out_path, frame.__name__, val)
            tags.setall(frame.__name__, [frame(text=val)])

    if cover_art:
        def make_apic(img, picture_type, desc):
            return id3.APIC(id3.Encoding.UTF8, 'image/jpeg',
                            picture_type, desc,
                            images.make_blob(img, ext='jpeg'))

        art_tags = generate_art_tags(album, track, cover_art, make_apic)
        if art_tags:
            LOGGER.debug("%s: Adding %d artworks", out_path, len(art_tags))
            tags.setall('APIC', art_tags)

    tags.save(out_path, v2_version=3)
    LOGGER.info("Finished writing %s", out_path)


def encode_preview_mp3(in_path, out_dir, filemap, track, encode_args, protections):
    """ encode a preview mp3, which also requires generating a filename from md5,
        and doesn't need any tags et al
        """
    if in_path in filemap:
        # We've already generated a preview for this file, so we can fast-exit
        LOGGER.info("Already generated %s -> %s", in_path, filemap[in_path])
        track['preview_mp3'] = filemap[in_path]
        return

    basename = util.file_md5(in_path)
    preview_fname = f'{basename}.mp3'
    filemap[in_path] = preview_fname

    LOGGER.info("Encoding preview %s -> %s", in_path, preview_fname)

    track['preview_mp3'] = preview_fname
    protections.add(preview_fname)

    outfile = os.path.join(out_dir, preview_fname)

    util.run_encoder(in_path, outfile, encode_args + ['-c:a', 'libmp3lame'])


def track_tag_title(track):
    """ Get the tag title for a track """
    title = track.get('title', None)
    return title


def tag_vorbis(tags, idx, album, track):
    """ Add a vorbis comment section to an ogg/flac file """
    frames = {
        'ARTIST': track.get('artist', album.get('artist')),
        'ALBUM': album.get('title'),
        'TITLE': track_tag_title(track),
        'TRACKNUMBER': str(idx),
        'GENRE': track.get('genre', album.get('genre')),
        'LYRICS': util.text_to_lines(track.get('lyrics')),
        'DESCRIPTION': track.get('comment'),
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


def make_flac_picture(img, picture_type, desc):
    """ Given an image tag spec, generate a FLAC Picture element """
    from mutagen import flac

    pic = flac.Picture()
    pic.type = picture_type
    pic.desc = desc
    pic.width = img.width
    pic.height = img.height
    pic.mime = "image/jpeg"
    pic.data = images.make_blob(img, ext='jpeg')

    return pic


def encode_ogg(in_path, out_path, idx, album, track, encode_args, cover_art):
    """ Encode a track as ogg vorbis """
    from mutagen import oggvorbis

    util.run_encoder(in_path, out_path, encode_args)

    tags = oggvorbis.OggVorbis(out_path)
    tag_vorbis(tags, idx, album, track)

    if cover_art:
        def make_ogg_picture(img, picture_type, desc):
            picture_data = make_flac_picture(img, picture_type, desc).write()
            return base64.b64encode(picture_data).decode('ascii')

        tags['metadata_block_picture'] = generate_art_tags(
            album, track, cover_art, make_ogg_picture)

    tags.save()

    LOGGER.info("Finished writing %s", out_path)


def encode_flac(in_path, out_path, idx, album, track, encode_args, cover_art):
    """ Encode a track as ogg vorbis """
    from mutagen import flac

    util.run_encoder(in_path, out_path, encode_args)

    tags = flac.FLAC(out_path)
    tag_vorbis(tags.tags, idx, album, track)

    tags.clear_pictures()

    if cover_art:
        for picture in generate_art_tags(album, track, cover_art, make_flac_picture):
            tags.add_picture(picture)
        LOGGER.debug("%s pictures=%s", out_path, tags.pictures)

    tags.save(deleteid3=True)

    tags = flac.FLAC(out_path)
    LOGGER.debug("reload %s pictures=%s", out_path, tags.pictures)

    LOGGER.info("Finished writing %s", out_path)


def make_web_preview(input_dir, output_dir, album, protections, futures):
    """ Generate the embedded preview player """
    LOGGER.info("Preview: Waiting for %s (%d tasks)", output_dir, len(futures))
    wait_futures(futures)
    LOGGER.info("Preview: Building player in %s", output_dir)

    from .players import camptown
    player = camptown.Player(art_size=200, fullsize_art_size=1600)

    # filter out all hidden tracks
    album = copy.deepcopy(album)
    album['tracks'] = [track for track in album['tracks']
                       if not track.get('hidden')]

    @functools.lru_cache()
    def gen_art_preview(in_path: str) -> typing.Dict[str, typing.Union[str, int]]:
        """ Generate web preview art for the given file

        :param str in_path: Input path of the source file
        :param str out_dir: Output directory

        :returns: tuple of the 1x and 2x renditions of the artwork
        """
        LOGGER.debug("generating preview art for %s", in_path)
        renditions = [(spec, *images.generate_rendition(in_path, output_dir, size))
                      for spec, size in player.art_rendition_sizes]

        _, _, width, height = renditions[0]
        return {
            "width": width,
            "height": height,

            **{size: path for size, path, _, _ in renditions}
        }

    def extract_protections(art_spec):
        """ given an artwork spec, extract the file protections """
        return set(art_spec[size] for size, _ in player.art_rendition_sizes)

    if 'artwork' in album:
        LOGGER.debug("album art")
        album['artwork_preview'] = gen_art_preview(
            os.path.join(input_dir, album['artwork']))
        protections |= extract_protections(album['artwork_preview'])
        LOGGER.debug("added preview protections %s", album['artwork_preview'])

    for track in album['tracks']:
        if track.get('filename'):
            input_filename = os.path.join(input_dir, track['filename'])

            duration = util.get_audio_duration(input_filename)
            track['duration'] = duration
            track['duration_timestamp'] = seconds_to_timestamp(duration)
            track['duration_datetime'] = seconds_to_datetime(duration)

        if 'artwork' in track:
            track['artwork_preview'] = gen_art_preview(
                os.path.join(input_dir, track['artwork']))
            protections |= extract_protections(track['artwork_preview'])
            LOGGER.debug("added preview protections %s",
                         track['artwork_preview'])

    player.convert(input_dir, output_dir, album,
                   protections, version=__version__)

    LOGGER.info("Preview: Finished generating web preview at %s; protections=%s",
                output_dir, protections)


def clean_subdir(path: str, allowed: typing.Set[str], futures):
    """ Clean up a subdirectory of extraneous files """
    LOGGER.info("Cleanup: Waiting for %s (%d tasks)", path, len(futures))
    wait_futures(futures)
    LOGGER.info("Cleaning up directory %s", path)

    LOGGER.info("Allowed in %s: %s", path, allowed)
    for file in os.scandir(path):
        if file.name not in allowed:
            LOGGER.info("Removing extraneous file %s", file.path)
            if file.is_dir():
                shutil.rmtree(file)
            else:
                os.remove(file)


def submit_butler(config, target, futures):
    """ Submit the directory to itch.io via butler """

    output_dir = os.path.join(config.output_dir, target)

    if target == 'preview':
        target = 'html'

    channel = f'{config.butler_target}:{config.butler_prefix}{target}'

    LOGGER.info("Butler: Waiting for %s (%d tasks)", output_dir, len(futures))
    wait_futures(futures)

    LOGGER.info("Butler: pushing '%s' to channel '%s'", output_dir, channel)
    try:
        result = subprocess.run([config.butler_path, 'push', *config.butler_args,
                                 output_dir, channel],
                                stdin=subprocess.DEVNULL,
                                capture_output=True,
                                check=True,
                                creationflags=getattr(
            subprocess, 'CREATE_NO_WINDOW', 0),
        )

        LOGGER.info("butler completed successfully: %s",
                    result.stdout.decode())
    except subprocess.CalledProcessError as err:
        if 'Please set BUTLER_API_KEY' in err.output.decode():
            raise RuntimeError("Butler login needed") from err
        raise RuntimeError(f'Butler error: {err.output}') from err


def seconds_to_timestamp(duration):
    """ Convert a duration (in seconds) to a timestamp like h:mm:ss """
    minutes, seconds = divmod(round(duration), 60)
    hours, minutes = divmod(minutes, 60)

    if hours:
        return f'{hours:.0f}:{minutes:02.0f}:{seconds:02.0f}'
    return f'{minutes:.0f}:{seconds:02.0f}'


def seconds_to_datetime(duration):
    """ Convert a duration (in seconds) to an HTML5 datetime like 3h 5m 10s """
    minutes, seconds = divmod(duration, 60)
    hours, minutes = divmod(minutes, 60)

    if hours:
        return f'{hours:.0f}h {minutes:.0f}m {seconds:.0f}s'
    return f'{minutes:.0f}m {seconds:.0f}s'


def encode_tracks(config, album, protections, pool, futures):
    """ run the track encode process """

    def enqueue(target, encode_func, input_filename, *args, **kwargs):
        if input_filename:
            futures[target].append(pool.submit(
                encode_func, input_filename, *args, **kwargs))

    # caches preview input file -> output filename
    preview_filemap: dict[str, str] = {}

    for idx, track in enumerate(album['tracks'], start=1):
        base_filename = f'{idx:02d} '
        if 'artist' in track:
            base_filename += f"{track['artist']} - "
        base_filename += track.get('title', '')
        base_filename = util.slugify_filename(base_filename)

        def out_path(fmt, ext=None, fname=None):
            # pylint:disable=cell-var-from-loop
            out_file = f'{fname or base_filename}.{ext or fmt}'
            protections[fmt].add(out_file)
            return os.path.join(config.output_dir, fmt, out_file)

        if track.get('filename'):
            input_filename = os.path.join(config.input_dir, track['filename'])
        else:
            input_filename = ''

        if 'artwork' in track:
            track['artwork_path'] = os.path.join(
                config.input_dir, track['artwork'])

        if 'lyrics' in track and isinstance(track['lyrics'], str):
            lyricfile = os.path.join(config.input_dir, track['lyrics'])
            if os.path.isfile(lyricfile):
                track['lyrics'] = util.read_lines(lyricfile)

        if config.do_mp3:
            enqueue('mp3',
                    encode_mp3,
                    input_filename,
                    out_path('mp3'),
                    idx, album, track, config.mp3_encoder_args, cover_art=1500)

        if config.do_ogg:
            enqueue('ogg',
                    encode_ogg,
                    input_filename,
                    out_path('ogg'),
                    idx, album, track, config.ogg_encoder_args, cover_art=1500)

        if config.do_flac:
            enqueue('flac',
                    encode_flac,
                    input_filename,
                    out_path('flac'),
                    idx, album, track, config.flac_encoder_args, cover_art=1500)

        # only encode a preview track if it's going to be visible to the player
        if (config.do_preview
            and input_filename
            and not track.get('hidden')
                and track.get('preview', True)):
            enqueue('preview',
                    encode_preview_mp3,
                    input_filename,
                    # We don't know the filename until encode time
                    os.path.join(config.output_dir, 'preview'),
                    preview_filemap,
                    track, config.preview_encoder_args, protections['preview'])


def make_zipfile(input_dir, output_file, futures):
    """ Make a .zip archive for manual uploading """
    LOGGER.info("Zipfile: Waiting for %s (%d tasks)",
                input_dir, len(futures))
    wait_futures(futures)

    LOGGER.info("Building %s.zip from directory %s", output_file, input_dir)
    shutil.make_archive(output_file, 'zip', input_dir)


def process(config, album, pool, futures):
    """
    Process the album given the parsed config and the loaded album data

    :param options.Options config: Encoder configuration
    :param dict album: :doc:`Album metadata <metadata>`
    :param concurrent.Futures.Executor pool: The threadpool to submit tasks to
    :param dict futures: Pending tasks for a particular build phase; should be
        a :py:class:`collections.defaultdict(list)` or similar

    Each format has the following phases, each one depending on the previous:

    1. ``encode``: Encodes and tags the output files
    2. ``build``: Builds any extra files (e.g. the web player)
    3. ``clean``: Directory cleanup tasks

    And then these two phases are shared across formats but depend on ``clean``
    (and may run in parallel):

    1. ``butler``: Pushes the build to itch.io via the butler tool
    2. ``zip``: Builds the local .zip file for manual uploading

    When this function exits, the futures dict will be fully-populated with a
    mapping from each phase to a list of :py:class:`concurrent.futures.Future` for
    that phase.

    You can wait on each phase's list separately, or you can collapse it with e.g.:

    .. code-block:: python

        all_futures = list(itertools.chain(*futures.values()))
        concurrent.futures.wait(all_futures)

    """
    # pylint:disable=too-many-branches

    # Make a copy of the dict, since some pipeline steps mutate it and we want
    # to be nice to the caller
    album = copy.deepcopy(album)

    # Coerce album configuration to app configuration if it hasn't been specified
    LOGGER.debug("config = %s", config)
    for attrname, default in (
        ('do_preview', True),
        ('do_mp3', True),
        ('do_ogg', True),
        ('do_flac', True),
        ('do_zip', True),
        ('do_cdda', False),
        ('do_butler', bool(album.get('butler_target'))),
        ('do_cleanup', True),
        ('butler_target', ''),
        ('butler_prefix', '')
    ):
        LOGGER.debug("config.%s = %s", attrname, getattr(config, attrname))
        if getattr(config, attrname) is None:
            setattr(config, attrname, album.get(attrname, default))
            LOGGER.debug("config.%s unset, using album value %s",
                         attrname, getattr(config, attrname))

    LOGGER.info("Starting encode with configuration: %s", config)

    formats = set()
    for target in ALL_TARGETS:
        attrname = f'do_{target}'
        if getattr(config, attrname) is None:
            LOGGER.debug(
                "config.%s is None, falling back to album spec", attrname)
            setattr(config, attrname, album.get(attrname, True))

        if getattr(config, attrname):
            LOGGER.info("Building %s", target)
            formats.add(target)
            os.makedirs(os.path.join(
                config.output_dir, target), exist_ok=True)

    if config.do_butler and not (config.butler_path and shutil.which(config.butler_path)):
        LOGGER.warning("Couldn't find tool 'butler'; disabling upload")
        config.do_butler = False

    if not formats and not config.do_cdda:
        raise RuntimeError("No targets specified and nothing to do")

    protections: typing.Dict[str, typing.Set[str]
                             ] = collections.defaultdict(set)

    if 'artwork' in album:
        album['artwork_path'] = os.path.join(
            config.input_dir, album['artwork'])

    # PHASE 1: Encode

    encode_tracks(config, album, protections, pool, futures)

    if config.do_cdda:
        futures['cdda'] = cdda.encode(album,
                                      config.input_dir,
                                      os.path.join(config.output_dir, 'cdda'),
                                      protections['cdda'],
                                      pool
                                      )

    if config.do_preview:
        futures['preview'].append(pool.submit(make_web_preview,
                                              config.input_dir,
                                              os.path.join(config.output_dir,
                                                           'preview'),
                                              album, protections['preview'],
                                              [*futures['preview']]))

    # PHASE 2: Clean
    if config.do_cleanup:
        for target in formats:
            futures[target].append(pool.submit(
                clean_subdir, os.path.join(config.output_dir, target),
                protections[target], [*futures[target]]))

    # PHASE 3: Distribution
    for target in (t for t in DIST_TARGETS if t in formats):
        if config.do_butler and config.butler_target:
            futures['butler'].append(pool.submit(
                submit_butler,
                config,
                target,
                futures[target]))

        if config.do_zip:
            filename_parts = [album.get(field)
                              for field in ('artist', 'title')
                              if album.get(field)]
            fname = os.path.join(config.output_dir,
                                 util.slugify_filename(
                                     ' - '.join([*filename_parts, target])))
            futures['zip'].append(pool.submit(
                make_zipfile,
                os.path.join(config.output_dir, target),
                fname,
                futures[target])
            )
