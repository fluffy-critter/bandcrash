""" Track editing widgets """

import logging
import os
import os.path
import typing

from PySide6.QtWidgets import (QAbstractScrollArea, QCheckBox, QFileDialog,
                               QFormLayout, QHBoxLayout, QLineEdit,
                               QListWidget, QListWidgetItem, QPlainTextEdit,
                               QPushButton, QScrollArea, QSizePolicy,
                               QSplitter, QVBoxLayout, QWidget, QAbstractItemView)

from .. import util
from . import datatypes
from .file_utils import FileRole
from .widgets import FileSelector, wrap_layout

LOGGER = logging.getLogger(__name__)


class TrackEditor(QWidget):
    """ A track editor pane """
    # pylint:disable=too-many-instance-attributes

    def __init__(self, album_editor, data: datatypes.TrackData):
        """ edit an individual track

        :param dict data: The metadata blob
        """
        super().__init__()
        self.setMinimumSize(400, 0)

        self.album_editor = album_editor
        self.data = data

        layout = QFormLayout()
        layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.setLayout(layout)

        self.filename = FileSelector(FileRole.AUDIO, album_editor)
        self.group = QLineEdit()
        self.title = QLineEdit()
        self.genre = QLineEdit()
        self.artist = QLineEdit()
        self.composer = QLineEdit()
        self.cover_of = QLineEdit()
        self.artwork = FileSelector(FileRole.IMAGE, album_editor)
        self.lyrics = QPlainTextEdit()
        self.about = QLineEdit()

        self.preview = QCheckBox("Generate preview")
        self.hidden = QCheckBox("Hidden track")

        layout.addRow("Audio file", self.filename)
        layout.addRow("Title", self.title)

        player_options = QHBoxLayout()
        player_options.setSpacing(0)
        player_options.setContentsMargins(0, 0, 0, 0)
        player_options.addWidget(self.preview)
        player_options.addWidget(self.hidden)
        layout.addRow("Player options", player_options)

        layout.addRow("Track artist", self.artist)
        layout.addRow("Cover of", self.cover_of)
        layout.addRow("Artwork", self.artwork)
        layout.addRow("Lyrics", self.lyrics)
        layout.addRow("Genre", self.genre)
        layout.addRow("Grouping", self.group)
        layout.addRow("Track comment", self.about)

        self.reset(data)

    def reset(self, data: datatypes.TrackData):
        """ Reset to the specified backing data """
        self.data = data

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
            datatypes.to_checkstate(self.data.get('preview', True)))
        self.hidden.setCheckState(
            datatypes.to_checkstate(self.data.get('hidden', False)))

    def apply(self):
        """ Apply our data to the backing data """
        # pylint:disable=too-many-branches

        if not self.data:
            return

        relpath = util.make_relative_path(self.album_editor.filename)

        datatypes.apply_text_fields(self.data, (
            ('filename', self.filename.file_path),
            ('artwork', self.artwork.file_path),
        ), relpath)

        datatypes.apply_text_fields(self.data, (
            ('title', self.title),
            ('genre', self.genre),
            ('artist', self.artist),
            ('composer', self.composer),
            ('cover_of', self.cover_of),
            ('group', self.group),
            ('about', self.about),
        ))

        def split_lyrics(text):
            lines = text.split('\n')
            return lines if len(lines) != 1 else text

        lyrics = split_lyrics(self.lyrics.document().toPlainText())
        if lyrics:
            self.data['lyrics'] = lyrics
        elif 'lyrics' in self.data:
            del self.data['lyrics']

        datatypes.apply_checkbox_fields(self.data, (
            ('preview', self.preview, True),
            ('hidden', self.hidden, False),
        ))


class TrackListing(QSplitter):
    """ The track listing panel and editor """
    # pylint:disable=too-many-instance-attributes

    class TrackItem(QListWidgetItem):
        """ an item in the track listing """

        def __init__(self, album_editor, data: datatypes.TrackData):
            super().__init__()
            self.editor = TrackEditor(album_editor, data)
            self.setText(self.display_name)

            self.editor.title.textChanged.connect(self.apply)
            self.editor.filename.file_path.textChanged.connect(self.apply)

        def reset(self, data: datatypes.TrackData):
            """ Reset the track listing from a new tracklist

            :param list data: album['data']
            """
            LOGGER.debug("TrackItem.__reset__ %s", self.display_name)
            self.editor.reset(data)
            self.setText(self.display_name)

        def apply(self):
            """ Apply the GUI values to the backing store """
            LOGGER.debug("TrackItem.__apply__ %s", self.display_name)
            self.editor.apply()
            self.setText(self.display_name)

        @property
        def display_name(self):
            """ Get the display name of this track """
            info = self.editor.data
            if info and 'title' in info:
                return info['title']
            if info and 'filename' in info:
                return f"({os.path.basename(info['filename'])})"
            return "(unknown)"

    def __init__(self, album_editor):
        super().__init__()
        LOGGER.debug("TrackListing.__init__")

        self.data: datatypes.TrackList = []
        self.album_editor = album_editor

        left_panel = QVBoxLayout(self)
        left_panel.setSpacing(0)
        left_panel.setContentsMargins(0, 0, 0, 0)
        self.addWidget(wrap_layout(self, left_panel))

        self.track_listing = QListWidget(self)
        self.track_listing.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        left_panel.addWidget(self.track_listing)

        self.button_add = QPushButton("+")
        self.button_add.clicked.connect(self.add_tracks)
        self.button_delete = QPushButton("-")
        self.button_delete.clicked.connect(self.delete_track)
        self.button_move_up = QPushButton("^")
        self.button_move_up.clicked.connect(self.move_up)
        self.button_move_down = QPushButton("v")
        self.button_move_down.clicked.connect(self.move_down)

        buttons = QHBoxLayout(self)
        buttons.setSpacing(0)
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.addWidget(self.button_add)
        buttons.addWidget(self.button_delete)
        buttons.addStretch(1000)
        buttons.addWidget(self.button_move_up)
        buttons.addWidget(self.button_move_down)
        left_panel.addWidget(wrap_layout(self, buttons))

        self.slug = TrackEditor(album_editor, {})
        self.slug.setEnabled(False)

        self.editpanel = QScrollArea()
        self.editpanel.setMinimumSize(450, 0)
        self.editpanel.setWidgetResizable(True)
        self.editpanel.setSizeAdjustPolicy(
            QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.editpanel.setWidget(self.slug)
        self.addWidget(self.editpanel)

        self.track_listing.currentRowChanged.connect(self.set_item)

        for widget in (self, self.track_listing):
            policy = widget.sizePolicy()
            policy.setVerticalPolicy(QSizePolicy.Policy.Expanding)
            widget.setSizePolicy(policy)

        self.setSizes([1, 10])

    def reset(self, data: datatypes.TrackList):
        """ Reset to the backing storage """
        LOGGER.debug("TrackListing.reset")

        current_row = self.track_listing.currentRow()

        if self.track_listing.count() and self.track_listing.count() != len(data):
            LOGGER.warning("Sync error: Track listing had %d, expected %d",
                           self.track_listing.count(), len(data))

        for idx, track in enumerate(data):
            item = typing.cast(TrackListing.TrackItem,
                               self.track_listing.item(idx))
            if item:
                item.reset(track)
            else:
                self.track_listing.addItem(
                    TrackListing.TrackItem(self.album_editor, track))

        while self.track_listing.count() > len(data):
            self.track_listing.takeItem(self.track_listing.count() - 1)

        self.data = data

        if current_row != self.track_listing.currentRow():
            LOGGER.warning("Sync error: list position changed from %d to %d",
                           self.track_listing.currentRow(), current_row)
            self.track_listing.setCurrentRow(current_row)

    def apply(self):
        """ Save any currently-edited track """
        LOGGER.debug("TrackListing.apply")
        self.data.clear()
        for row in range(self.track_listing.count()):
            item = typing.cast(TrackListing.TrackItem,
                               self.track_listing.item(row))
            item.editor.apply()
            self.data.append(item.editor.data)

    def set_item(self, row):
        """ Signal handler for row change """
        LOGGER.debug("TrackListing.set_item")
        self.apply()
        self.editpanel.takeWidget()  # necessary to prevent Qt from GCing it on replacement
        item = typing.cast(TrackListing.TrackItem,
                           self.track_listing.item(row))
        if item:
            self.editpanel.setWidget(item.editor)
        else:
            self.editpanel.setWidget(self.slug)

    def add_tracks(self):
        """ Add some tracks """
        LOGGER.debug("TrackListing.add_tracks")
        role = FileRole.AUDIO
        filenames, _ = QFileDialog.getOpenFileNames(
            self,
            "Select audio files",
            dir=self.album_editor.get_last_directory(role),
            filter=role.file_filter)

        for filename in filenames:
            _, title = util.guess_track_title(filename)
            track = {'filename': filename, 'title': title}
            self.data.append(track)
            self.track_listing.addItem(
                TrackListing.TrackItem(self.album_editor, track))

        if filenames:
            ref_file = filenames[0]
            LOGGER.debug("Using filename %s", ref_file)
            role.default_directory = os.path.dirname(ref_file)
            self.album_editor.set_last_directory(
                role, os.path.dirname(ref_file))

    def delete_track(self):
        """ Remove a track """
        LOGGER.debug("TrackListing.delete_track")
        self.track_listing.takeItem(self.track_listing.currentRow())

    def move_up(self):
        """ Move the currently-selected track up in the track listing """
        LOGGER.debug("TrackListing.move_up")
        row = self.track_listing.currentRow()
        if row > 0:
            dest = row - 1
            item = self.track_listing.takeItem(row)
            self.track_listing.insertItem(dest, item)
            self.track_listing.setCurrentRow(dest)

    def move_down(self):
        """ Move the currently-selected track up in the track listing """
        LOGGER.debug("TrackListing.move_down")
        row = self.track_listing.currentRow()
        if row < self.track_listing.count() - 1:
            dest = row + 1
            item = self.track_listing.takeItem(row)
            self.track_listing.insertItem(dest, item)
            self.track_listing.setCurrentRow(dest)
