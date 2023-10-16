""" Bandcrash GUI """
# pylint:disable=invalid-name,too-few-public-methods,too-many-ancestors
# type: ignore
import argparse
import json
import logging
import os.path
import typing

from PySide6 import QtCore, QtGui, QtWidgets

from .. import __version__, util
from . import datatypes
from .track_editor import TrackListing
from .widgets import FileSelector

LOG_LEVELS = [logging.WARNING, logging.INFO, logging.DEBUG]
LOGGER = logging.getLogger(__name__)


def to_checkstate(val):
    """ Convert a bool to a qt CheckState """
    return QtCore.Qt.Checked if val else QtCore.Qt.Unchecked


def add_menu_item(menu, name, method, shortcut):
    """ Add a menu item """
    action = menu.addAction(name)
    action.triggered.connect(method)
    if shortcut:
        action.setShortcut(QtGui.QKeySequence(shortcut))
    return action


class AlbumEditor(QtWidgets.QMainWindow):
    """ An album editor window """
    # pylint:disable=too-many-instance-attributes

    def __init__(self, path: str):
        """ edit an album file

        :param str path: The path to the JSON file
        """
        super().__init__()
        self.setMinimumSize(600, 0)

        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")

        add_menu_item(file_menu, "&New", self.file_new, "Ctrl+N")
        add_menu_item(file_menu, "&Open...", self.file_open, "Ctrl+O")
        add_menu_item(file_menu, "&Save", self.save, "Ctrl+S")
        add_menu_item(file_menu, "Save &As...", self.save_as, "Ctrl+Shift+S")
        add_menu_item(file_menu, "&Revert", self.revert, "Ctrl+Shift+R")

        self.filename = path
        self.data: typing.Dict[str, typing.Any] = {'tracks': []}
        if path:
            self.reload(path)

        layout = QtWidgets.QFormLayout(
            fieldGrowthPolicy=QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        self.setCentralWidget(QtWidgets.QWidget(layout=layout))

        self.artist = QtWidgets.QLineEdit(placeholderText="Artist name")
        self.title = QtWidgets.QLineEdit(placeholderText="Album title")
        self.year = QtWidgets.QLineEdit(
            placeholderText="1978", inputMask='0000')
        self.genre = QtWidgets.QLineEdit(
            placeholderText="Avant-Industrial Loungecore")
        self.artwork = FileSelector(self)
        self.composer = QtWidgets.QLineEdit()
        # self.fg_color = ColorSelector("Foreground")
        # self.bg_color = ColorSelector("Background")
        # self.highlight_color = ColorSelector("Highlight")

        layout.addRow("Artist", self.artist)
        layout.addRow("Title", self.title)
        layout.addRow("Composer", self.composer)
        layout.addRow("Year", self.year)
        layout.addRow("Genre", self.genre)
        layout.addRow("Artwork", self.artwork)

        # button hbox for colors

        self.track_listing = TrackListing(self)
        layout.addRow("Audio Tracks", None)
        layout.addRow(self.track_listing)

        buttons = QtWidgets.QHBoxLayout()

        start_button = QtWidgets.QPushButton("Encode")
        start_button.clicked.connect(self.encode_album)

        buttons.addWidget(start_button)

        layout.addRow(buttons)

        self.setWindowTitle(self.filename)

        self.reset()

    def file_new(self):
        """ Dialog box to create a new album file """
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            caption="New album file",
            filter="Album files (*.json *.bcalbum)")
        if path:
            editor = AlbumEditor(path)
            editor.show()

    def file_open(self):
        """ Dialog box to open an existing file """
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            caption="New album file",
            filter="Album files (*.json *.bcalbum)")
        if path:
            editor = AlbumEditor(path)
            editor.show()

    def reload(self, path):
        """ Load from the backing storage """
        with open(path, 'r', encoding='utf8') as file:
            try:
                self.data = json.load(file)
                if 'tracks' not in self.data:
                    raise KeyError('tracks')
            except (json.decoder.JSONDecodeError, KeyError, TypeError):
                err = QtWidgets.QErrorMessage(self)
                err.showMessage("Invalid album JSON file")
                self.filename = ''
                self.data = {'tracks': []}

    def reset(self):
        """ Reset to the saved values """
        LOGGER.debug("AlbumEditor.reset")

        for key, widget in (
            ('artist', self.artist),
            ('title', self.title),
            ('genre', self.genre),
            ('artwork', self.artwork.file_path),
            ('composer', self.composer),
        ):
            widget.setText(self.data.get(key, ''))

        if 'year' in self.data:
            self.year.setText(str(self.data['year']))

        self.track_listing.reset(self.data['tracks'])

    def apply(self):
        """ Apply edits to the saved data """
        LOGGER.debug("AlbumEditor.apply")
        relpath = util.make_relative_path(self.filename)

        datatypes.apply_text_fields(self.data,
                                    (
                                        ('title', self.title),
                                        ('genre', self.genre),
                                        ('artist', self.artist),
                                        ('compsoer', self.composer),
                                    ))

        datatypes.apply_text_fields(self.data,
                                    (('artwork', self.artwork.file_path),),
                                    relpath)

        datatypes.apply_text_fields(self.data,
                                    (('year', self.year),),
                                    int)

        self.track_listing.apply()

    def save(self):
        """ Save the file to disk """
        LOGGER.debug("AlbumEditor.save")
        self.apply()

        with open(self.filename, 'w', encoding='utf8') as file:
            json.dump(self.data, file, indent=3)

    def save_as(self):
        """ Save the file and change the name """
        LOGGER.debug("AlbumEditor.save_as")
        self.apply()

        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            caption="Select your album file",
            filter="Album files (*.bcalbum *.json)",
            dir=os.path.dirname(self.filename))
        if path:
            self.renormalize_paths(self.filename, path)
            self.filename = path
            self.setWindowTitle(self.filename)
            self.reset()
            self.save()

        self.reset()

    def revert(self):
        """ Revert all changes """
        LOGGER.debug("AlbumEditor.revert")
        # TODO confirmation box
        self.reload(self.filename)
        self.reset()

    def encode_album(self):
        """ Run the encoder process """
        LOGGER.debug("AlbumEditor.encode_album")
        self.apply()
        # TODO run the actual encode of course

    def renormalize_paths(self, old_name, new_name):
        """ Renormalize the file paths in the backing data """
        abspath = util.make_absolute_path(old_name)
        relpath = util.make_relative_path(new_name)

        LOGGER.debug("renormalize_paths %s %s", old_name, new_name)

        def renorm(path):
            if os.path.isabs(path):
                LOGGER.debug("Keeping %s absolute", path)
                return path

            old_abs = abspath(path)
            if not os.path.isfile(old_abs):
                LOGGER.warning(
                    "Not touching non-file path %s (%s)", path, old_abs)
                return path

            out = relpath(old_abs)
            LOGGER.debug("Renormalizing %s -> %s -> %s", path, old_abs, out)
            return out

        for key in ('artwork',):
            if key in self.data:
                self.data[key] = renorm(self.data[key])

        for track in self.data['tracks']:
            for key in ('filename', 'artwork', 'lyrics'):
                if key in track and isinstance(track[key], str):
                    track[key] = renorm(track[key])


def open_file(path):
    """ Open a file for editing """
    editor = AlbumEditor(path)
    editor.show()


class BandcrashApplication(QtWidgets.QApplication):
    """ Application event handler """

    def event(self, evt):
        """ Handle an application-level event """
        LOGGER.debug("Event: %s", evt)
        if evt.type() == QtCore.QEvent.FileOpen:
            LOGGER.debug("Got file open event: %s", evt.file())
            open_file(evt.file())
            return True

        return super().event(evt)


def main():
    """ instantiate an app """
    parser = argparse.ArgumentParser(description="GUI for Bandcrash")
    parser.add_argument('-v', '--verbosity', action="count",
                        help="increase output verbosity", default=0)
    parser.add_argument('--version', action='version',
                        version="%(prog)s " + __version__.__version__)
    parser.add_argument('open_files', type=str, nargs='*')
    options = parser.parse_args()

    logging.basicConfig(level=LOG_LEVELS[min(
        options.verbosity, len(LOG_LEVELS) - 1)],
        format='%(message)s')

    LOGGER.debug(
        "Opening bandcrash GUI with provided files: %s", options.open_files)

    app = BandcrashApplication()

    if options.open_files:
        for path in options.open_files:
            open_file(os.path.abspath(path))
    else:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            caption="Select your album file",
            filter="Album files (*.json *.bcalbum)",
            options=QtWidgets.QFileDialog.DontConfirmOverwrite)
        editor = AlbumEditor(path)
        editor.show()

    app.exec()


if __name__ == '__main__':
    main()
