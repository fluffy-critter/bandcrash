""" Parsed arguments """

import argparse
import os
import shutil

from . import __version__


def get_parser():
    """ Parse the command line arguments

    :param list args: Replace os.args (for GUIs and tests)
     """
    parser = argparse.ArgumentParser(
        description="Generate purchasable albums for independent storefronts")

    parser.add_argument("-v", "--verbosity", action="count",
                        help="increase output verbosity",
                        default=0)

    parser.add_argument('--version', action='version',
                        version="%(prog)s " + __version__.__version__)

    parser.add_argument('--init', action='store_true',
                        help="Attempt to populate the JSON file automatically")

    parser.add_argument('input_dir', type=str, nargs='?',
                        default='.',
                        help="Directory with the source files")
    parser.add_argument('output_dir', type=str, nargs='?',
                        default='./output',
                        help="Directory to store the output files into")

    parser.add_argument('--json', '-j', type=str,
                        help="Name of the album JSON file, relative to input_dir",
                        default='album.json')

    parser.add_argument('--num-threads', '-t', type=int,
                        dest='num_threads',
                        help="Maximum number of concurrent threads",
                        default=os.cpu_count())

    for tool in ('lame', 'oggenc', 'flac', 'butler'):
        parser.add_argument(f'--{tool}-path', type=str,
                            help=f"Full path to the {tool} binary",
                            default=shutil.which(tool) or tool)

    def add_encoder(name, info, args):
        """ Add a feature group to the CLI """
        feature = parser.add_mutually_exclusive_group(required=False)
        fname = f'do_{name}'
        feature.add_argument(f'--{name}', dest=fname, action='store_true',
                             help=f"Generate {info}")
        feature.add_argument(f'--no-{name}', dest=fname, action='store_false',
                             help=f"Don't generate {info}")
        feature.set_defaults(**{fname: True})

        parser.add_argument(f'--{name}-encoder-args', type=str,
                            help=f"Arguments to pass to the {info} encoder",
                            default=args)

    add_encoder('preview', 'web preview', '-b 32 -V 5 -q 5 -m j')
    add_encoder('mp3', 'mp3 album', '-V 0 -q 0 -m j')
    add_encoder('ogg', 'ogg album', '')
    add_encoder('flac', 'flac album', '')

    feature = parser.add_mutually_exclusive_group(required=False)
    feature.add_argument('--zip', dest='do_zip', action='store_true',
                         help="Generate .zip archives")
    feature.add_argument('--no-zip', dest='do_zip', action='store_false',
                         help="Don't generate a .zip archive")
    feature.set_defaults(do_zip=True)

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

    return parser


def parse_args(args=None):
    """ Parse an argument list

    :param list args: Argument list override
    """
    return get_parser().parse_args(args)
