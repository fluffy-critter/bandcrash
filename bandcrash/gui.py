""" Bandcrash GUI """
# pylint:disable=invalid-name,too-few-public-methods,too-many-ancestors
# type: ignore
import argparse
import json
import logging
import os.path
import typing

from PySide6 import QtCore, QtGui, QtWidgets

from bandcrash import __version__, args

LOG_LEVELS = [logging.WARNING, logging.INFO, logging.DEBUG]
LOGGER = logging.getLogger(__name__)


def to_checkstate(val):
    """ Convert a bool to a qt CheckState """
    return QtCore.Qt.Checked if val else QtCore.Qt.Unchecked

class FileSelector(QtWidgets.QWidget):
    """ A file selector textbox with ... button """

    def __init__(self):
        super().__init__()

        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)

        self.file_path = QtWidgets.QLineEdit()
        self.button = QtWidgets.QPushButton("...")

        layout.addWidget(self.file_path)
        layout.addWidget(self.button)

        self.button.clicked.connect(self.choose_file)

    def choose_file(self):
        """ Pick a file """
        dialog = QtWidgets.QFileDialog()
        (filename, _) = dialog.getOpenFileName(self)
        if filename:
            self.file_path.setText(filename)

    @staticmethod
    def make_relative(base_file):
        """ Returns a function to provide a path relative to the specified filename or directory """
        if os.path.isdir(base_file):
            dirname = base_file
        else:
            dirname = os.path.dirname(base_file)

        return lambda path: (os.path.relpath(path, dirname)
                             if os.path.isabs(path)
                             else path)


class TrackEditor(QtWidgets.QWidget):
    """ A track editor pane """

    def __init__(self, album_editor, data: dict):
        """ edit an individual track

        :param dict data: The metadata blob
        """
        super().__init__()
        self.setMinimumSize(400, 0)

        self.album_editor = album_editor
        self.data = data

        layout = QtWidgets.QFormLayout(
            fieldGrowthPolicy=QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        self.setLayout(layout)

        self.filename = FileSelector()
        self.title = QtWidgets.QLineEdit(placeholderText="Song title")
        self.genre = QtWidgets.QLineEdit()
        self.artist = QtWidgets.QLineEdit(
            placeholderText="Track-specific artist (leave blank if none)")
        self.cover_of = QtWidgets.QLineEdit(
            placeholderText="Original performing artist (leave blank if none)")
        self.artwork = FileSelector()
        self.lyrics = QtWidgets.QPlainTextEdit()

        self.preview = QtWidgets.QCheckBox("Generate preview")
        self.hidden = QtWidgets.QCheckBox("Hidden track")

        layout.addRow("Audio file", self.filename)
        layout.addRow("Title", self.title)
        layout.addRow("Genre", self.genre)
        layout.addRow("Track artist", self.artist)
        layout.addRow("Original performer", self.cover_of)
        layout.addRow("Artwork", self.artwork)
        layout.addRow("Lyrics", self.lyrics)

        player_options = QtWidgets.QHBoxLayout()
        player_options.addWidget(self.preview)
        player_options.addWidget(self.hidden)
        layout.addRow(player_options)

        buttons = QtWidgets.QHBoxLayout()

        apply_button = QtWidgets.QPushButton("Apply")
        apply_button.clicked.connect(self.apply)
        buttons.addWidget(apply_button)

        reset_button = QtWidgets.QPushButton("Reset")
        reset_button.clicked.connect(self.reset)
        buttons.addWidget(reset_button)

        layout.addRow(buttons)

        self.reset()

    def reset(self):
        """ Reset to the backing data """
        for key, widget in (
            ('filename', self.filename.file_path),
            ('title', self.title),
            ('genre', self.genre),
            ('artist', self.artist),
            ('cover_of', self.cover_of),
            ('artwork', self.artwork.file_path),
        ):
            widget.setText(self.data.get(key, ''))

        self.lyrics.document().setPlainText('\n'.join(self.data.get('lyrics', '')))

        self.preview.setCheckState(self.data.get('preview', to_checkstate(True)))
        self.hidden.setCheckState(self.data.get('hidden', to_checkstate(False)))

    def apply(self):
        """ Apply our data to the backing data """

        relpath = FileSelector.make_relative(self.album_editor.filename)

        for key, widget in (
            ('filename', self.filename.file_path),
            ('artwork', self.artwork.file_path),
        ):
            if value := widget.text():
                self.data[key] = relpath(value)
            elif key in self.data:
                del self.data[key]

        for key, widget in (
            ('title', self.title),
            ('genre', self.genre),
            ('artist', self.artist),
            ('cover_of', self.cover_of),
        ):
            if value := widget.text():
                self.data[key] = value
            elif key in self.data:
                del self.data[key]

        if value := self.lyrics.document().toPlainText():
            lines = value.split('\n')
            self.data['lyrics'] = lines if len(lines) != 1 else lines[0]
        else:
            del self.data['lyrics']

        for key, widget, dfl in (('preview', self.preview, True),
                                 ('hidden', self.hidden, False)):
            value = widget.checkState() == QtCore.Qt.Checked
            if value != dfl:
                self.data[key] = value
            elif key in self.data:
                del self.data[key]


class AlbumEditor(QtWidgets.QWidget):
    """ An album editor window """

    def __init__(self, path: str):
        """ edit an album file

        :param str path: The path to the JSON file
        """
        super().__init__()
        self.setMinimumSize(600, 0)

        self.filename = path
        self.data: typing.Dict[str, typing.Any] = {'tracks': []}
        if os.path.isfile(path):
            with open(path, 'r', encoding='utf8') as file:
                self.data = json.load(file)

        layout = QtWidgets.QFormLayout(
            fieldGrowthPolicy=QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        self.setLayout(layout)

        self.artist = QtWidgets.QLineEdit(placeholderText="Artist name")
        self.title = QtWidgets.QLineEdit(placeholderText="Album title")
        self.year = QtWidgets.QLineEdit(
            placeholderText="1978", inputMask='0000')
        self.genre = QtWidgets.QLineEdit(
            placeholderText="Avant-Industrial Loungecore")
        self.artwork = FileSelector()
        # self.fg_color = ColorSelector("Foreground")
        # self.bg_color = ColorSelector("Background")
        # self.highlight_color = ColorSelector("Highlight")

        layout.addRow("Artist", self.artist)
        layout.addRow("Title", self.title)
        layout.addRow("Year", self.year)
        layout.addRow("Genre", self.genre)
        layout.addRow("Artwork", self.artwork)

        # button hbox for colors

        # TODO this needs to be a track list box on the left
        for track in self.data['tracks']:
            layout.addRow(track.get('title', 'no title'),
                          TrackEditor(self, track))
            break

        buttons = QtWidgets.QHBoxLayout()

        save_button = QtWidgets.QPushButton("Save")
        save_button.clicked.connect(self.apply)
        start_button = QtWidgets.QPushButton("Encode")
        start_button.clicked.connect(self.encode_album)

        buttons.addWidget(save_button)
        buttons.addWidget(start_button)

        layout.addRow(buttons)

        self.setWindowTitle(self.filename)

        self.reset()

    def reset(self):
        """ Reset to the saved values """

        for key, widget in (
            ('artist', self.artist),
            ('title', self.title),
            ('genre', self.genre),
            ('artwork', self.artwork.file_path),
        ):
            widget.setText(self.data.get(key, ''))

        if 'year' in self.data:
            self.year.setText(str(self.data['year']))

    def apply(self):
        """ Apply edits to the saved data """
        relpath = FileSelector.make_relative(self.filename)

        for key, widget in (
            ('title', self.title),
            ('genre', self.genre),
            ('artist', self.artist),
        ):
            if value := widget.text():
                self.data[key] = value
            elif key in self.data:
                del self.data[key]

        for key, widget in (
            ('artwork', self.artwork.file_path),
        ):
            if value := widget.text():
                self.data[key] = relpath(value)
            elif key in self.data:
                del self.data[key]

        if value := self.year.text():
            self.data['year'] = int(value)
        elif 'year' in self.data:
            del self.data['year']

        # TODO apply all track editors as well

        # with open(self.filename, 'w', encoding='utf8') as file:
        #     json.dump(self.data, file, indent='   ')

    def encode_album(self):
        """ Run the encoder process """
        self.apply()
        print(json.dumps(self.data, indent='   '))


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

    app = QtWidgets.QApplication([])

    if options.open_files:
        for path in options.open_files:
            editor = AlbumEditor(path)
            editor.show()
    # else:
    #   open file picker that opens an AlbumEditor with new or existing path

    app.exec()


if __name__ == '__main__':
    main()
