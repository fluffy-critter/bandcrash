""" Bandcrash GUI """
# pylint:disable=invalid-name,too-few-public-methods,too-many-ancestors
import argparse
import json
import logging

from PySide6 import QtCore, QtGui, QtWidgets

from bandcrash import __version__, args

LOG_LEVELS = [logging.WARNING, logging.INFO, logging.DEBUG]
LOGGER = logging.getLogger(__name__)


class AlbumEditor(QtWidgets.QWidget):
    def __init__(self, load_file=None):
        super().__init__()

        # album metadata
        self.album = {'tracks':[]}

        # json key -> widget
        self.connections = {}

        layout = QtWidgets.QFormLayout(fieldGrowthPolicy=QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        self.setLayout(layout)

        artist_name = QtWidgets.QLineEdit(placeholderText = "Artist name")
        self.connect(artist_name, artist_name.textChanged, 'artist')
        layout.addRow("Artist", artist_name)

        album_title = QtWidgets.QLineEdit(placeholderText = "Album title")
        self.connect(album_title, album_title.textChanged, 'title')
        layout.addRow("Album", album_title)

        release_year = QtWidgets.QLineEdit(inputMask='0000', placeholderText = "1978")
        self.connect(release_year, release_year.textChanged, 'year', int)
        layout.addRow("Year", release_year)

        album_genre = QtWidgets.QLineEdit(placeholderText = "Avant-Industrial Loungecore")
        self.connect(album_genre, album_genre.textChanged, 'genre')
        layout.addRow("Genre", album_genre)

        # TODO: player colors
        # TODO: album artwork

        start_button = QtWidgets.QPushButton("Go!")
        start_button.clicked.connect(self.encode_album)
        layout.addRow(start_button)

    def connect(self, widget, signal, key, transform=lambda x:x):
        """ Connect a widget signal to an album metadata field

        :param widget: The owning widget
        :param signal: The signal slot to connect
        :param str key: The JSON key to set
        :param transform: Optional function for data conversion
        """

        self.connections[key] = widget
        def apply(value):
            if value:
                self.album[key] = value
            else:
                del self.album[key]

            if key in ('artist', 'title'):
                self.updateDisplayTitle()

        signal.connect(apply)

    def updateDisplayTitle(self):
        """ Update the album's display title """
        parts = []
        if "artist" in self.album:
            parts.append(self.album["artist"])
        if "title" in self.album:
            parts.append(self.album["title"])
        if parts:
            self.output_name = ' - '.join(parts)
        else:
            self.output_name = "(untitled album)"

        self.setWindowTitle(self.output_name)

    def encode_album(self):
        """ Run the encoder process """
        print(self.album)

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
        "Opening bandcrash GUI with provided files: [%s]", options.open_files)

    app = QtWidgets.QApplication([])

    mainwin = AlbumEditor()
    mainwin.show()

    app.exec()



if __name__ == '__main__':
    main()
