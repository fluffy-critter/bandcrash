""" Bandcrash GUI """
# pylint:disable=invalid-name,too-few-public-methods,too-many-ancestors
import argparse
import json
import logging
import os.path
import typing

from PySide6 import QtCore, QtGui, QtWidgets

from bandcrash import __version__, args

LOG_LEVELS = [logging.WARNING, logging.INFO, logging.DEBUG]
LOGGER = logging.getLogger(__name__)


class EditorBinding:
    """ Maintain bindings between editor and JSON data

    :param dict data: The dict to bind the editor to
    """

    def __init__(self, data):
        self.data = data
        self.setters: typing.Dict[str,
                                  typing.Tuple[typing.Callable, typing.Callable]] = {}

    def connect(self, key, signal, setter, to_json=lambda x: x, to_qt=lambda x: x):
        """ Connect a widget signal to a metadata field

        :param str key: The key in the dict
        :param signal: The editor signal slot
        :param setter: The widget's setter method
        :param to_json: Type transform when setting the JSON field
        :param to_qt: Type transform when setting the Qt field
        """
        def apply(value):
            if value:
                self.data[key] = to_json(value)
            else:
                del self.data[key]

        signal.connect(apply)

        self.setters[key] = (setter, to_qt)

    def apply(self):
        """ Apply the dict's data to the editor """
        for key, (setter, xform) in self.setters.items():
            if key in self.data:
                setter(xform(self.data[key]))



class FileSelector(QtWidgets.QWidget):
    """ A file selector textbox with ... button """

    @typing.no_type_check
    def __init__(self, dialog_text="Choose file",
        filters:typing.Optional[typing.List[str]]=None):
        super().__init__()

        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)

        self.path_text = QtWidgets.QLineEdit()
        self.button = QtWidgets.QPushButton("...")

        self.dialog_text = dialog_text
        self.filters = filters

        layout.addWidget(self.path_text)
        layout.addWidget(self.button)

        self.button.clicked.connect(self.choose_file)

    def choose_file(self):
        """ Pick a file """
        dialog = QtWidgets.QFileDialog(caption=self.dialog_text)
        if self.filters:
            dialog.setNameFilters(filters)
        (filename, _) = dialog.getOpenFileName()
        if filename:
            self.path_text.setText(filename)

    @staticmethod
    def make_relative(base_file):
        """ Returns a function to provide a path relative to the specified filename """
        return lambda path : os.path.relpath(path, os.basename(base_file))

class TrackEditor(QtWidgets.QWidget):
    """ A track editor pane """

    @typing.no_type_check
    def __init__(self, album_editor, data:dict):
        """ edit an individual track

        :param dict data: The metadata blob
        """
        super().__init__()
        self.setMinimumSize(400, 0)

        self.album_editor = album_editor
        self.data = data

        self.binding = EditorBinding(self.data)

        layout = QtWidgets.QFormLayout(
            fieldGrowthPolicy=QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        self.setLayout(layout)

        widget = FileSelector("Choose audio file")
        self.binding.connect('filename', widget.path_text.textChanged,
            widget.path_text.setText, FileSelector.make_relative(self.album_editor.filename))
        layout.addRow("Audio file", widget)

        # TODO track artwork

        widget = QtWidgets.QLineEdit(placeholderText="Song title")
        self.binding.connect('title', widget.textChanged, widget.setText)
        layout.addRow("Title", widget)

        widget = QtWidgets.QLineEdit()
        self.binding.connect('genre', widget.textChanged, widget.setText)
        layout.addRow("Genre", widget)

        widget = QtWidgets.QLineEdit(placeholderText="Track-specific artist")
        self.binding.connect('artist', widget.textChanged, widget.setText)
        layout.addRow("Performing Artist", widget)

        lyrics = QtWidgets.QTextEdit()
        self.binding.connect('lyrics', lyrics.textChanged, lyrics.setText,
            ,
            '\n'.join)
        layout.addRow("Lyrics", widget)

        self.binding.apply()



class AlbumEditor(QtWidgets.QWidget):
    """ An album editor window """

    @typing.no_type_check
    def __init__(self, path: str):
        """ edit an album file

        :param str path: The path to the JSON file
        """
        super().__init__()
        self.setMinimumSize(600, 0)

        self.filename: str = path
        self.album: typing.Dict[str, typing.Any] = {'tracks': []}
        if os.path.isfile(path):
            with open(path, 'r', encoding='utf8') as file:
                self.album = json.load(file)

        self.binding = EditorBinding(self.album)

        layout = QtWidgets.QFormLayout(
            fieldGrowthPolicy=QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        self.setLayout(layout)

        text = QtWidgets.QLineEdit(placeholderText="Artist name")
        self.binding.connect('artist', text.textChanged, text.setText)
        text.textChanged.connect(self.updateDisplayTitle)
        layout.addRow("Artist", text)

        text = QtWidgets.QLineEdit(placeholderText="Album title")
        self.binding.connect('title', text.textChanged, text.setText)
        text.textChanged.connect(self.updateDisplayTitle)
        layout.addRow("Album", text)

        text = QtWidgets.QLineEdit(
            inputMask='0000', placeholderText="1978")
        self.binding.connect('year', text.textChanged, text.setText, int, str)
        layout.addRow("Year", text)

        text = QtWidgets.QLineEdit()
        self.binding.connect('genre', text.textChanged, text.setText)
        layout.addRow("Genre", text)

        # TODO: player colors
        # TODO: album artwork

        # TODO this needs to be a track list box on the left
        for track in self.album['tracks']:
            layout.addRow(track.get('title', 'no title'), TrackEditor(self, track))
            break

        start_button = QtWidgets.QPushButton("Go!")
        start_button.clicked.connect(self.encode_album)
        layout.addRow(start_button)

        self.binding.apply()
        self.updateDisplayTitle()

    def updateDisplayTitle(self):
        """ Update the album's display title """

        title = os.path.basename(self.filename)

        parts = []
        if "artist" in self.album:
            parts.append(self.album["artist"])
        if "title" in self.album:
            parts.append(self.album["title"])
        if parts:
            title += f": {' — '.join(parts)}"

        self.setWindowTitle(title)

    def encode_album(self):
        """ Run the encoder process """
        print(json.dumps(self.album, indent='   '))


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
