""" File handling utilities """

import enum
import itertools
import logging
import os.path

from PySide6.QtCore import QSettings, QStandardPaths, QUrl

from .. import images

LOGGER = logging.getLogger(__name__)
ACCEPT_AUDIO_EXTS = ('.wav', '.ogg', '.flac', '.mp3', '.aif', '.aiff')


class FileRole(enum.Enum):
    """ File roles, for file selector widgets """

    def __init__(self, label, file_filter):
        self.label = label
        self.file_filter = file_filter

    ALBUM = ("album", "Bandcrash album (*.bcalbum *.json)")
    AUDIO = (
        "track", f"Audio files ({' '.join(f'*{ext}' for ext in ACCEPT_AUDIO_EXTS)})")
    IMAGE = (
        "image", f"Image files ({' '.join(f'*{ext}' for ext in images.known_extensions())})")
    STYLESHEET = ("stylesheet", "Stylesheets (*.css)")
    OUTPUT = ("output", '')
    BINARY = ("binary", '')

    @property
    def default_directory(self):
        """ Get the default system-level directory for this file role """
        settings = QSettings()
        settings.beginGroup("defaultDirs")

        if settings.contains(self.name):
            return settings.value(self.name)

        sloc = QStandardPaths.StandardLocation

        for candidate in itertools.chain(
                *[QStandardPaths.standardLocations(loc)
                  for loc in (sloc.MusicLocation, sloc.DocumentsLocation, sloc.HomeLocation)]):
            return candidate

        LOGGER.warning(
            "Couldn't find default directory for role %s", self.name)
        return ''

    @default_directory.setter
    def default_directory(self, file_dir):
        """ Set the default system-level directory for this file role """
        settings = QSettings()
        settings.beginGroup("defaultDirs")
        settings.setValue(self.name, file_dir)
        settings.sync()


def filter_audio_urls(urls: list[QUrl]):
    """ Given a list of audio URLs, provide ones which are a local file in an
    accepted format """

    return [path for path in [url.toLocalFile() for url in urls if url.isLocalFile()]
            if os.path.splitext(path)[1] in ACCEPT_AUDIO_EXTS]
