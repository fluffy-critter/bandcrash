""" Bandcrash GUI """
# pylint:disable=invalid-name,too-few-public-methods,too-many-ancestors
# type: ignore
import argparse
import json
import logging
import os.path
import typing

from PySide6 import QtCore, QtGui, QtWidgets

from . import __version__, util

LOG_LEVELS = [logging.WARNING, logging.INFO, logging.DEBUG]
LOGGER = logging.getLogger(__name__)


def to_checkstate(val):
    """ Convert a bool to a qt CheckState """
    return QtCore.Qt.Checked if val else QtCore.Qt.Unchecked


class FileSelector(QtWidgets.QWidget):
    """ A file selector textbox with ... button """

    def __init__(self, album_editor=None):
        super().__init__()

        layout = QtWidgets.QHBoxLayout()
        # layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)

        self.album_editor = album_editor
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
            if self.album_editor:
                filename = util.make_relative_path(
                    self.album_editor.filename)(filename)
            self.file_path.setText(filename)


class TrackEditor(QtWidgets.QWidget):
    """ A track editor pane """
    # pylint:disable=too-many-instance-attributes

    def __init__(self, album_editor):
        """ edit an individual track

        :param dict data: The metadata blob
        """
        super().__init__()
        self.setMinimumSize(400, 0)

        self.album_editor = album_editor
        self.data = None

        layout = QtWidgets.QFormLayout(
            fieldGrowthPolicy=QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        self.setLayout(layout)

        self.filename = FileSelector(album_editor)
        self.group = QtWidgets.QLineEdit(placeholderText="Track grouping")
        self.title = QtWidgets.QLineEdit(placeholderText="Song title")
        self.genre = QtWidgets.QLineEdit()
        self.artist = QtWidgets.QLineEdit(
            placeholderText="Track-specific artist (leave blank if none)")
        self.composer = QtWidgets.QLineEdit()
        self.cover_of = QtWidgets.QLineEdit(
            placeholderText="Original performing artist (leave blank if none)")
        self.artwork = FileSelector(album_editor)
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

    def reset(self, data):
        """ Reset to the specified backing data """
        self.data = data
        if self.data is None:
            self.setEnabled(False)
            return

        self.setEnabled(True)

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

        self.preview.setCheckState(
            to_checkstate(self.data.get('preview', True)))
        self.hidden.setCheckState(
            to_checkstate(self.data.get('hidden', False)))

    def apply(self):
        """ Apply our data to the backing data """
        # pylint:disable=too-many-branches

        if not self.data:
            return

        relpath = util.make_relative_path(self.album_editor.filename)

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

        self.data = None

        left_panel = QtWidgets.QVBoxLayout(self)
        left_panel.setSpacing(0)
        left_panel.setContentsMargins(0, 0, 0, 0)
        self.addWidget(QtWidgets.QWidget(layout=left_panel))

        self.track_listing = QtWidgets.QListWidget(self)
        left_panel.addWidget(self.track_listing)

        self.button_add = QtWidgets.QPushButton("+")
        self.button_add.clicked.connect(self.add_tracks)
        self.button_delete = QtWidgets.QPushButton("-")
        self.button_delete.clicked.connect(self.delete_track)
        self.button_move_up = QtWidgets.QPushButton("^")
        self.button_move_up.clicked.connect(self.move_up)
        self.button_move_down = QtWidgets.QPushButton("v")
        self.button_move_down.clicked.connect(self.move_down)

        buttons = QtWidgets.QHBoxLayout(self)
        buttons.setSpacing(0)
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.addWidget(self.button_add)
        buttons.addWidget(self.button_delete)
        buttons.addStretch(1000)
        buttons.addWidget(self.button_move_up)
        buttons.addWidget(self.button_move_down)
        left_panel.addWidget(QtWidgets.QWidget(layout=buttons))

        self.track_editor = TrackEditor(album_editor)
        scroller = QtWidgets.QScrollArea()
        scroller.setMinimumSize(450, 0)
        scroller.setWidget(self.track_editor)
        scroller.setWidgetResizable(True)
        # scroller.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroller.setSizeAdjustPolicy(
            QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.addWidget(scroller)

        self.track_listing.currentRowChanged.connect(self.set_row)

        for widget in (self, self.track_listing):
            policy = widget.sizePolicy()
            policy.setVerticalPolicy(QtWidgets.QSizePolicy.Expanding)
            widget.setSizePolicy(policy)

        self.setSizes([1, 10])

        self.reset(album_editor.data['tracks'])

    @staticmethod
    def display_name(track):
        """ Get the list display name for a track object """
        parts = []
        if 'filename' in track:
            parts.append(os.path.basename(track['filename']))
        if 'title' in track:
            parts.append(track['title'])

        return ': '.join(parts) if parts else '(unknown)'

    def reset(self, data):
        """ Reset to the backing storage """
        self.data = data

        current_row = self.track_listing.currentRow()
        self.track_listing.clear()

        for track in self.data:
            self.track_listing.addItem(self.display_name(track))

        if current_row < self.track_listing.count():
            self.track_listing.setCurrentRow(current_row)

    def apply(self):
        """ Save any currently-edited track """
        self.track_editor.apply()

    def set_row(self, row):
        """ Set the editor row """
        self.track_editor.apply()
        self.track_editor.reset(self.data[row])

    def add_tracks(self):
        """ Add some tracks """
        filenames, _ = QtWidgets.QFileDialog.getOpenFileNames(self,
                                                              "Select audio files",
                                                              filter="WAV audio (*.wav)")

        for filename in filenames:
            _, title = util.guess_track_title(filename)
            track = {'filename': filename, 'title': title}
            self.data.append(track)
            self.track_listing.addItem(self.display_name(track))

    def delete_track(self):
        """ Remove a track """
        current_row = self.track_listing.currentRow()
        del self.data[current_row]
        self.track_listing.takeItem(current_row)
        self.apply()

    def move_up(self):
        """ Move the currently-selected track up in the track listing """
        row = self.track_listing.currentRow()
        if row > 0:
            idx = row - 1
            self.move_item(row, idx)
            self.track_listing.setCurrentRow(idx)

    def move_down(self):
        """ Move the currently-selected track down in the track listing """
        row = self.track_listing.currentRow()
        if row < self.track_listing.count() - 1:
            idx = row + 1
            self.move_item(row, idx)
            self.track_listing.setCurrentRow(idx)

    def move_item(self, from_idx, to_idx):
        """
        Move the specified track from the given index to the specified one
        """
        self.data.insert(to_idx, self.data.pop(from_idx))

        item = self.track_listing.takeItem(from_idx)
        self.track_listing.insertItem(to_idx, item)


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
        try:
            self.reload(path)
            if 'tracks' not in self.data:
                raise KeyError('tracks')
        except (json.decoder.JSONDecodeError, KeyError, TypeError):
            err = QtWidgets.QErrorMessage(self)
            err.showMessage("Invalid album JSON file")
            self.filename = ''
            self.data = {'tracks': []}

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
        if os.path.isfile(path):
            with open(path, 'r', encoding='utf8') as file:
                self.data = json.load(file)

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

        self.track_listing.reset(self.data['tracks'])

    def apply(self):
        """ Apply edits to the saved data """
        relpath = util.make_relative_path(self.filename)

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
        self.apply()

        with open(self.filename, 'w', encoding='utf8') as file:
            json.dump(self.data, file, indent=3)

    def save_as(self):
        """ Save the file and change the name """
        self.apply()

        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            caption="Select your album file",
            filter="Album files (*.bcalbum *.json)",
            dir=os.path.dirname(self.filename))
        if path:
            self.renormalize_paths(self.filename, path)
            self.filename = path
            self.setWindowTitle(self.filename)
            self.save()

        self.reset()

    def revert(self):
        """ Revert all changes """
        # TODO confirmation box
        self.reload(self.filename)
        self.reset()

    def encode_album(self):
        """ Run the encoder process """
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
            out = relpath(old_abs)
            LOGGER.debug("Renormalizing %s -> %s -> %s", path, old_abs, out)
            return out

        for key in ('artwork',):
            if key in self.data:
                self.data[key] = renorm(self.data[key])

        for track in self.data['tracks']:
            for key in ('filename', 'artwork'):
                if key in track:
                    track[key] = renorm(track[key])
            if 'lyrics' in track and isinstance(track['lyrics'], str):
                lyricfile = abspath(track['lyrics'])
                if os.path.isfile(lyricfile):
                    track['lyrics'] = relpath(lyricfile)


def open_file(path):
    """ Open a file for editing """
    editor = AlbumEditor(path)
    editor.show()


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
