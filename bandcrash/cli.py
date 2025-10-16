""" main CLI entry point """

import argparse
import collections
import concurrent.futures
import dataclasses
import itertools
import json
import logging
import os
import sys
import typing

from . import __version__, options, process, util

LOG_LEVELS = [logging.WARNING, logging.INFO, logging.DEBUG]
LOGGER = logging.getLogger(__name__)


def parse_args():
    """ Parse commandline arguments """
    defaults = options.Options()
    parser = argparse.ArgumentParser("Bandcrash CLI")

    parser.add_argument('input', type=str,
                        help="Album input directory or JSON file")
    parser.add_argument('output', type=str, nargs='?', default=None,
                        help="Album output directory")

    parser.add_argument("-v", "--verbosity", action="count",
                        help="Increase output logging level", default=0)
    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {__version__}")

    parser.add_argument('--num-threads', '-t', type=int,
                        dest='num_threads',
                        help="Maximum number of concurrent threads",
                        default=defaults.num_threads)

    parser.add_argument('--json', '-j', type=str, dest='json_file',
                        default='album.json',
                        help="If input is a directory, specifies the JSON file "
                        "(relative to that directory)")

    parser.add_argument('--init', dest='init_json', action='store_true',
                        help="Populate the JSON file automatically")

    for target, description, add_args in (
        ('preview', 'Build web player', True),
        ('mp3', 'Encode mp3 album', True),
        ('ogg', 'Encode ogg album', True),
        ('flac', 'Encode flac album', True),
        ('cdda', 'Generate .bin/.cue file for CD-R replication', False),
        ('cleanup', 'Clean extraneous files in the output directories', False),
        ('zip', 'Build a .zip archive', False),
        ('butler', 'Upload to itch.io using Butler', False),
    ):
        feature = parser.add_mutually_exclusive_group(required=False)
        fname = f'do_{target}'
        feature.add_argument(f'--{target}', dest=fname, action='store_true',
                             help=description)
        feature.add_argument(f'--no-{target}', dest=fname, action='store_false',
                             help=f"Don't {description}")
        feature.set_defaults(**{fname: None})

        if add_args:
            parser.add_argument(f'--{target}-encoder-args', type=str,
                                help=f"Arguments to pass to the {target} encoder",
                                default=' '.join(getattr(defaults, f'{target}_encoder_args')))

    parser.add_argument('--butler-path', type=str, default=defaults.butler_path,
                        help="Path to the butler executable")

    parser.add_argument('--butler-target', '-b', type=str,
                        dest='butler_target',
                        help="Butler push target prefix",
                        default=None)

    parser.add_argument('--butler-channel-prefix', '-p', type=str,
                        dest='butler_prefix',
                        help="Prefix for the Butler channel name",
                        default=None)

    parser.add_argument('--butler-args', type=str, default='',
                        help="Extra arguments to provide to butler")

    return parser.parse_args()


def get_config(args) -> options.Options:
    """ Convert the parsed command arguments to an options structure """

    config = options.Options()

    for field in dataclasses.fields(config):
        value = getattr(args, field.name, None)
        if value is not None:
            if field.type == list[str]:
                LOGGER.debug("Setting config list %s to %s", field.name, value)
                setattr(config, field.name, value.split())
            else:
                LOGGER.debug("Setting config field %s to %s",
                             field.name, value)
                setattr(config, field.name, value)

    return config


def main():
    """ Main entry point """
    # pylint:disable=too-many-branches,too-many-statements,too-many-locals
    args = parse_args()
    config = get_config(args)

    logging.basicConfig(level=LOG_LEVELS[min(
        args.verbosity, len(LOG_LEVELS) - 1)],
        format='%(message)s')

    if os.path.isdir(args.input):
        config.input_dir = args.input
        json_file = os.path.join(args.input, args.json_file)
    else:
        config.input_dir = os.path.dirname(args.input)
        json_file = args.input
    assert config.input_dir is not None

    config.output_dir = args.output

    if not os.path.isfile(json_file) and not args.init_json:
        LOGGER.error("%s not found and --init not specified", json_file)
        sys.exit(1)

    if not config.output_dir and not args.init_json:
        LOGGER.error("Output directory not specified")
        sys.exit(1)

    if os.path.isfile(json_file):
        with open(json_file, 'r', encoding='utf8') as file:
            album = json.load(file)
    else:
        album = None

    if args.init_json:
        LOGGER.info("Populating %s with files from %s",
                    json_file, config.input_dir)
        album = util.populate_album(config.input_dir, album)
        LOGGER.info("Album now has %d tracks", len(album['tracks']))
        with open(json_file, 'w', encoding='utf8') as file:
            json.dump(album, file)

    if not config.output_dir:
        return

    pool = concurrent.futures.ThreadPoolExecutor(
        max_workers=config.num_threads)

    futures: typing.Dict[str,
                         typing.List[concurrent.futures.Future]] = collections.defaultdict(list)

    process(config, album, pool, futures)

    all_tasks = list(itertools.chain(*futures.values()))
    remaining_tasks = [f for f in all_tasks if not f.done()]
    LOGGER.info("Waiting for all tasks to complete... (%d/%d pending)",
                len(remaining_tasks), len(all_tasks))

    errors = []
    for task in concurrent.futures.as_completed(all_tasks):
        try:
            task.result()
        except Exception as err:  # pylint:disable=broad-exception-caught
            LOGGER.exception("Background task generated an exception")
            errors.append(err)

    if errors:
        sys.exit(1)

    LOGGER.info("Done")


if __name__ == '__main__':
    main()
