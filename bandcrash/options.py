""" Encoder options """

import dataclasses
import os
import shutil
import typing


def default_path(tool):
    """ Wrapper to keep Sphinx from exposing local build info to the world """
    def get():
        return shutil.which(tool)
    return get


DEFAULT_BUTLER_PATH = shutil.which('butler')


@dataclasses.dataclass
class Options:
    """ Encoder options for processing an album.

    The following parameters are set by whatever is running the album's process.

    :param str input_dir: The working directory for the input specification
    :param str output_dir: The output directory to store the various builds

    :param str butler_path: The path to the itch.io Butler tool. By default,
        searches for ``butler`` in the user's ``PATH``.
    :param str butler_args: Extra arguments to give to the butler tool (e.g. upload
        version, ``--identity``, etc.)

    :param list preview_encoder_args: FFmpeg encoder options for the web player
    :param list mp3_encoder_args: FFmpeg encoder options for the album download
    :param list ogg_encoder_args: FFmpeg encoder options for the Ogg album download
    :param list flac_encoder_args: FFmpeg encoder options for the FLAC album download

    The following parameters are set by the album's specification data, but may be
    overridden by the process runner (e.g. via command line arguments). A value of
    None indicates that it should use the album's configuration; defaults listed
    here are what occurs if it is unset both here and in the album specification.
    If unset, all of them default to True unless otherwise specified.

    :param bool do_preview: Whether to build the web preview
    :param bool do_mp3: Whether to build the MP3 album download
    :param bool do_ogg: Whether to build the Ogg album download
    :param bool do_flac: Whether to build the FLAC album download

    :param bool do_cleanup: Whether to clean up extra files from the target directories
    :param bool do_zip: Whether to build a .zip archive

    :param bool do_butler: Whether to automatically upload builds to
       `itch.io <https://itch.io>`_ via `Butler <https://itch.io/docs/butler/>`_

    :param str butler_target: The Butler target for the upload
        (e.g. ``fluffy/novembeat-2022`` for ``https://fluffy.itch.io/novembeat-2022``)
    :param str butler_prefix: A prefix to add to the Butler channel name; used for
        variations (e.g. ``bob-`` gives channel names of ``bob-mp3``, ``bob-flac``, etc.)
    """
    # pylint:disable=too-many-instance-attributes
    input_dir: typing.Optional[str] = None  # Base directory for all inputs
    output_dir: typing.Optional[str] = None  # Base directory for all outputs

    num_threads: int = os.cpu_count() or 4  # Number of threads to use for encoding

    preview_encoder_args: list[str] = dataclasses.field(
        default_factory="-q:a 5".split().copy)
    mp3_encoder_args: list[str] = dataclasses.field(
        default_factory="-q:a 0".split().copy)
    ogg_encoder_args: list[str] = dataclasses.field(
        default_factory="-q:a 0".split().copy)
    flac_encoder_args: list[str] = dataclasses.field(default_factory=list)

    butler_path: typing.Optional[str] = dataclasses.field(
        default_factory=default_path('butler'))
    butler_args: list[str] = dataclasses.field(default_factory=list)

    # The following options can override the values set in the album specification
    # (thus the None values)

    do_preview: typing.Optional[bool] = None  # Whether to build a web preview
    # Whether to build an MP3 album download
    do_mp3: typing.Optional[bool] = None
    # Whether to build an Ogg album download
    do_ogg: typing.Optional[bool] = None
    # Whether to build a FLAC album download
    do_flac: typing.Optional[bool] = None
    # Whether to build a CD-R bin/cue pair
    do_cdda: typing.Optional[bool] = None

    # Whether to clean up extraneous files from the output directories
    do_cleanup: typing.Optional[bool] = None

    # Whether to build a .zip file of each output
    do_zip: typing.Optional[bool] = None

    # Whether to initiate a Butler upload
    do_butler: typing.Optional[bool] = None

    butler_target: typing.Optional[str] = None  # Butler project target
    # Channel prefix for the Butler uploads
    butler_prefix: typing.Optional[str] = None


def fields():
    """ Get the dataclass fields """
    return dataclasses.fields(Options)
