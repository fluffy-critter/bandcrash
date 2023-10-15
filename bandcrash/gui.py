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
        # layout.setSpacing(0)
        layout.setContentsMargins(0,0,0,0)

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

    def __init__(self, album_editor):
        """ edit an individual track

        :param dict data: The metadata blob
        """
        super().__init__()
        self.setMinimumSize(400, 0)

        self.album_editor = album_editor
        self.data : typing.Optional[typing.Dict[str, typing.Any]] = None

        layout = QtWidgets.QFormLayout(
            fieldGrowthPolicy=QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        self.setLayout(layout)

        self.filename = FileSelector()
        self.group = QtWidgets.QLineEdit(placeholderText="Track grouping")
        self.title = QtWidgets.QLineEdit(placeholderText="Song title")
        self.genre = QtWidgets.QLineEdit()
        self.artist = QtWidgets.QLineEdit(
            placeholderText="Track-specific artist (leave blank if none)")
        self.composer = QtWidgets.QLineEdit()
        self.cover_of = QtWidgets.QLineEdit(
            placeholderText="Original performing artist (leave blank if none)")
        self.artwork = FileSelector()
        self.lyrics = QtWidgets.QPlainTextEdit()
        self.about = QtWidgets.QLineEdit()

        self.preview = QtWidgets.QCheckBox("Generate preview")
        self.hidden = QtWidgets.QCheckBox("Hidden track")

        layout.addRow("Audio file", self.filename)
        layout.addRow("Title", self.title)
        layout.addRow("Track artist", self.artist)
        layout.addRow("Cover of", self.cover_of)
        layout.addRow("Artwork", self.artwork)
        layout.addRow("Lyrics", self.lyrics)
        layout.addRow("Genre", self.genre)
        layout.addRow("Grouping", self.group)
        layout.addRow("Track comment", self.about)

        player_options = QtWidgets.QHBoxLayout()
        player_options.addWidget(self.preview)
        player_options.addWidget(self.hidden)
        layout.addRow(player_options)

        self.reset(self.data)

    def reset(self, data):
        """ Reset to the specified backing data """
        self.data = data
        if self.data is None:
            return

        for key, widget in (
            ('filename', self.filename.file_path),
            ('title', self.title),
            ('genre', self.genre),
            ('artist', self.artist),
            ('composer', self.composer),
            ('cover_of', self.cover_of),
            ('artwork', self.artwork.file_path),
            ('group', self.group),
            ('about', self.about),
        ):
            widget.setText(self.data.get(key, ''))

        lyrics = self.data.get('lyrics', '')
        if isinstance(lyrics, str):
            self.lyrics.document().setPlainText(lyrics)
        else:
            self.lyrics.document().setPlainText('\n'.join(lyrics))

        self.preview.setCheckState(to_checkstate(self.data.get('preview', True)))
        self.hidden.setCheckState(to_checkstate(self.data.get('hidden', False)))

    def apply(self):
        """ Apply our data to the backing data """

        if not self.data:
            return

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
            ('composer', self.composer),
            ('cover_of', self.cover_of),
            ('group', self.group),
            ('about', self.about),
        ):
            if value := widget.text():
                self.data[key] = value
            elif key in self.data:
                del self.data[key]

        for key, widget in (
            ('lyrics', self.lyrics),
            ):
            if value := widget.document().toPlainText():
                lines = value.split('\n')
                self.data[key] = lines if len(lines) != 1 else lines[0]
            elif key in self.data:
                del self.data[key]

        for key, widget, dfl in (('preview', self.preview, True),
                                 ('hidden', self.hidden, False)):
            value = widget.checkState() == QtCore.Qt.Checked
            if value != dfl:
                self.data[key] = value
            elif key in self.data:
                del self.data[key]

class TrackListing(QtWidgets.QSplitter):
    """ The track listing panel and editor """
    def __init__(self, album_editor):
        super().__init__()

        self.data = album_editor.data['tracks']

        self.track_listing = QtWidgets.QListWidget(self)
        self.addWidget(self.track_listing)

        self.track_editor = TrackEditor(album_editor)
        scroller = QtWidgets.QScrollArea()
        scroller.setMinimumSize(450, 0)
        scroller.setWidget(self.track_editor)
        scroller.setWidgetResizable(True)
        # scroller.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroller.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.addWidget(scroller)

        self.track_listing.currentRowChanged.connect(self.set_row)

        for widget in (self, self.track_listing):
            policy = widget.sizePolicy()
            policy.setVerticalPolicy(QtWidgets.QSizePolicy.Expanding)
            widget.setSizePolicy(policy)

        self.setSizes([1, 10])

        self.reset()

    def reset(self):
        """ Reset to the backing storage """
        current_row = self.track_listing.currentRow()
        self.track_listing.clear()

        for track in self.data:
            parts = []
            if 'filename' in track:
                parts.append(track['filename'])
            if 'title' in track:
                parts.append(track['title'])

            self.track_listing.addItem(': '.join(parts) if parts else '(unknown)')

        if current_row < self.count():
            self.track_listing.setCurrentRow(current_row)

    def apply(self):
        """ Save any currently-edited track """
        self.track_editor.apply()

    def set_row(self, row):
        """ Set the editor row """
        self.track_editor.apply()
        self.track_editor.reset(self.data[row])



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
            ('composer', self.composer),
        ):
            widget.setText(self.data.get(key, ''))

        if 'year' in self.data:
            self.year.setText(str(self.data['year']))

        self.track_listing.reset()

    def apply(self):
        """ Apply edits to the saved data """
        relpath = FileSelector.make_relative(self.filename)

        for key, widget in (
            ('title', self.title),
            ('genre', self.genre),
            ('artist', self.artist),
            ('compsoer', self.composer),
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

        self.track_listing.apply()

    def save(self):
        """ Save the file to disk """
        with open(self.filename, 'w', encoding='utf8') as file:
            json.dump(self.data, indent=3)

    def encode_album(self):
        """ Run the encoder process """
        self.apply()
        # TODO run the actual encode of course


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
