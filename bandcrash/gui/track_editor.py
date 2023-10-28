""" Track editing widgets """

import logging
import os
import os.path
import typing

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QAbstractScrollArea,
                               QButtonGroup, QCheckBox, QFileDialog,
                               QFormLayout, QHBoxLayout, QLineEdit,
                               QListWidget, QListWidgetItem, QPlainTextEdit,
                               QPushButton, QRadioButton, QScrollArea,
                               QSizePolicy, QSplitter, QVBoxLayout, QWidget)

from .. import util
from . import datatypes, file_utils
from .file_utils import FileRole
from .widgets import FileSelector, FlowLayout, wrap_layout

LOGGER = logging.getLogger(__name__)


class TrackEditor(QWidget):
    """ A track editor pane """
    # pylint:disable=too-many-instance-attributes

    def __init__(self, album_editor):
        """ edit an individual track

        :param dict data: The metadata blob
        """
        super().__init__()
        self.setMinimumSize(400, 0)

        self.album_editor = album_editor
        self.data: typing.Optional[datatypes.TrackData] = None
        self.setEnabled(False)

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
        self.comment = QLineEdit()

        layout.addRow("Audio file", self.filename)
        layout.addRow("Title", self.title)

        self.preview = QRadioButton("Preview")
        self.listed = QRadioButton("Listed")
        self.hidden = QRadioButton("Hidden")

        self.track_type = QButtonGroup()
        self.track_type.addButton(self.preview)
        self.track_type.addButton(self.listed)
        self.track_type.addButton(self.hidden)

        player_options = FlowLayout()
        player_options.setContentsMargins(0, 0, 0, 0)
        player_options.addWidget(self.preview)
        player_options.addWidget(self.listed)
        player_options.addWidget(self.hidden)
        layout.addRow("Track type", player_options)

        self.explicit = QCheckBox("Explicit")
        player_options.addWidget(self.explicit)

        layout.addRow("Track artist", self.artist)
        layout.addRow("Composer", self.composer)
        layout.addRow("Cover of", self.cover_of)
        layout.addRow("Artwork", self.artwork)
        layout.addRow("Lyrics", self.lyrics)
        layout.addRow("Genre", self.genre)
        layout.addRow("Grouping", self.group)
        layout.addRow("Track comment", self.comment)

    def reset(self, data: datatypes.TrackData):
        """ Reset to the specified backing data """
        self.data = data
        self.setEnabled(data is not None)

        for key, widget in (
            ('filename', self.filename.file_path),
            ('title', self.title),
            ('genre', self.genre),
            ('artist', self.artist),
            ('composer', self.composer),
            ('cover_of', self.cover_of),
            ('artwork', self.artwork.file_path),
            ('group', self.group),
            ('comment', self.comment),
        ):
            widget.setText(self.data.get(key, ''))

        lyrics = self.data.get('lyrics', '')
        if isinstance(lyrics, str):
            self.lyrics.document().setPlainText(lyrics)
        else:
            self.lyrics.document().setPlainText('\n'.join(lyrics))

        hidden = self.data.get('hidden', False)
        preview = self.data.get('preview', True) and not hidden
        listed = not hidden and not preview
        LOGGER.debug("hidden=%s preview=%s listed=%s", hidden, preview, listed)
        self.hidden.setChecked(hidden)
        self.preview.setChecked(preview)
        self.listed.setChecked(listed)

        self.explicit.setCheckState(
            datatypes.to_checkstate(self.data.get('explicit', False)))

    def apply(self):
        """ Apply our data to the backing data """
        # pylint:disable=too-many-branches

        if not self.data:
            LOGGER.debug("TrackEditor apply - no data")
            return

        LOGGER.debug("TrackEditor.apply %s", self.data.get('filename'))

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
            ('comment', self.comment),
        ))

        def split_lyrics(text):
            lines = text.split('\n')
            return lines if len(lines) != 1 else text

        lyrics = split_lyrics(self.lyrics.document().toPlainText())
        if lyrics:
            self.data['lyrics'] = lyrics
        elif 'lyrics' in self.data:
            del self.data['lyrics']

        datatypes.apply_radio_fields(self.data, (
            ('preview', self.preview, True),
            ('hidden', self.hidden, False),
        ))

        datatypes.apply_checkbox_fields(self.data, (
            ('explicit', self.explicit, False),
        ))

        LOGGER.debug("applied: %s", self.data)


class TrackListEditor(QSplitter):
    """ The track listing panel and editor """
    # pylint:disable=too-many-instance-attributes

    class TrackItem(QListWidgetItem):
        """ an item in the track listing """

        def __init__(self, track_num: int, track: datatypes.TrackData):
            super().__init__()
            self.track_number = track_num
            self.track_data = track
            self.update_name()

        def set_track_num(self, track_num: int):
            """ Update the track number for this one """
            self.track_number = track_num
            self.update_name()

        def reset(self, track_num: int, data: datatypes.TrackData):
            """ Reset the track listing from a new tracklist

            :param list data: album['data']
            """
            LOGGER.debug("TrackItem.reset %s", self.display_name)
            self.track_number = track_num
            self.track_data = data
            self.update_name()

        def apply(self):
            """ Apply the GUI values to the backing store """
            LOGGER.debug("TrackItem.apply %s", self.display_name)
            self.update_name()

        def update_name(self):
            """ Update the display name """
            self.setText(self.display_name)

        @property
        def display_name(self):
            """ Get the display name of this track """
            info = self.track_data
            if info and 'title' in info:
                title = info['title']
            elif info and 'filename' in info:
                title = f"({os.path.basename(info['filename'])})"
            else:
                title = "(unknown)"

            return f"{self.track_number + 1}. {title}"

    class TrackList(QListWidget):
        """ The actual track listing panel """

        def __init__(self, parent):
            super().__init__(parent)
            self.track_editor = parent
            self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
            self.setAcceptDrops(True)

        def dragEnterEvent(self, event):
            LOGGER.debug("dragEnterEvent %s %s", event, event.proposedAction())
            LOGGER.debug("hasurls: %s", event.mimeData().hasUrls())
            if event.proposedAction() == Qt.DropAction.CopyAction and event.mimeData().hasUrls():
                if files := file_utils.filter_audio_urls(event.mimeData().urls()):
                    LOGGER.debug("accepted files: %s", files)
                    event.acceptProposedAction()
            else:
                super().dragEnterEvent(event)

        def dropEvent(self, event):
            if event.proposedAction() == Qt.DropAction.CopyAction and event.mimeData().hasUrls():
                if files := file_utils.filter_audio_urls(event.mimeData().urls()):
                    LOGGER.debug("adding files: %s", files)
                    self.track_editor.add_files(files)
                    event.acceptProposedAction()
            elif event.proposedAction() == Qt.DropAction.MoveAction:
                self.track_editor.album_editor.record_undo()
                super().dropEvent(event)

            self.track_editor.apply()

    def __init__(self, album_editor):
        super().__init__()
        LOGGER.debug("TrackListEditor.__init__")

        self.data: datatypes.TrackList = []
        self.album_editor = album_editor

        left_panel = QVBoxLayout(self)
        left_panel.setSpacing(0)
        left_panel.setContentsMargins(0, 0, 0, 0)
        self.addWidget(wrap_layout(self, left_panel))

        self.track_listing = TrackListEditor.TrackList(self)
        left_panel.addWidget(self.track_listing)

        self.button_add = QPushButton("+")
        self.button_add.clicked.connect(self.add_track_button)
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

        self.track_editor = TrackEditor(album_editor)
        self.track_editor.setEnabled(False)

        self.editpanel = QScrollArea()
        self.editpanel.setMinimumSize(450, 0)
        self.editpanel.setWidgetResizable(True)
        self.editpanel.setSizeAdjustPolicy(
            QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.editpanel.setWidget(self.track_editor)
        self.addWidget(self.editpanel)

        self.track_listing.currentRowChanged.connect(self.set_item)

        for widget in (self, self.track_listing):
            policy = widget.sizePolicy()
            policy.setVerticalPolicy(QSizePolicy.Policy.Expanding)
            widget.setSizePolicy(policy)

        self.setSizes([1, 10])

    def reset(self, data: datatypes.TrackList):
        """ Reset to the backing storage """
        LOGGER.debug("TrackListEditor.reset")

        current_row = self.track_listing.currentRow()

        if self.track_listing.count() and self.track_listing.count() != len(data):
            LOGGER.warning("Sync error: Track listing had %d, expected %d",
                           self.track_listing.count(), len(data))

        for idx, track in enumerate(data):
            item = typing.cast(TrackListEditor.TrackItem,
                               self.track_listing.item(idx))
            if item:
                item.reset(idx, track)
            else:
                self.track_listing.addItem(
                    TrackListEditor.TrackItem(idx, track))

        while self.track_listing.count() > len(data):
            self.track_listing.takeItem(self.track_listing.count() - 1)

        self.data = data

        if current_row != self.track_listing.currentRow():
            LOGGER.warning("Sync error: list position changed from %d to %d",
                           self.track_listing.currentRow(), current_row)
            self.track_listing.setCurrentRow(current_row)

    def apply(self):
        """ Save any currently-edited track """
        LOGGER.debug("TrackListEditor.apply")
        self.track_editor.apply()

        self.data.clear()
        for row in range(self.track_listing.count()):
            item = typing.cast(TrackListEditor.TrackItem,
                               self.track_listing.item(row))
            item.set_track_num(row)
            item.apply()
            LOGGER.debug("  -- append %s", item.display_name)
            self.data.append(item.track_data)

    def set_item(self, row):
        """ Signal handler for row change """
        LOGGER.debug("TrackListEditor.set_item")
        self.apply()
        item = typing.cast(TrackListEditor.TrackItem,
                           self.track_listing.item(row))
        if item:
            self.track_editor.reset(item.track_data)
            self.track_editor.setEnabled(True)
        else:
            self.track_editor.reset({})
            self.track_editor.setEnabled(False)

    def add_track_button(self):
        """ Prompt to add some tracks """
        LOGGER.debug("TrackListEditor.add_tracks")
        role = FileRole.AUDIO
        LOGGER.debug("filter: %s", role.file_filter)
        filenames, _ = QFileDialog.getOpenFileNames(
            self,
            "Select audio files",
            dir=self.album_editor.get_last_directory(role),
            filter=role.file_filter)

        if filenames:
            # update the audio role selection path
            ref_file = filenames[0]
            LOGGER.debug("Audio role: using filename %s", ref_file)
            role.default_directory = os.path.dirname(ref_file)
            self.album_editor.set_last_directory(
                role, os.path.dirname(ref_file))

        self.add_files(filenames)

    @property
    def current_row(self):
        """ The current selected row """
        return self.track_listing.currentRow()

    @current_row.setter
    def current_row(self, idx):
        """ Change the current row """
        self.track_listing.setCurrentRow(idx)

    def add_files(self, filenames):
        """ Accepts files into the track listing """
        LOGGER.debug("TrackListEditor.add_files")
        self.album_editor.record_undo()
        for filename in filenames:
            _, title = util.guess_track_title(filename)
            track = {'filename': filename, 'title': title}
            self.track_listing.addItem(
                TrackListEditor.TrackItem(len(self.data), track))
            self.data.append(track)

    def delete_track(self):
        """ Remove a track """
        LOGGER.debug("TrackListEditor.delete_track")
        self.album_editor.record_undo()
        self.track_listing.takeItem(self.track_listing.currentRow())

    def select_previous(self):
        """ Select the previous track """
        current_row = self.track_listing.currentRow()
        if current_row > 0:
            self.track_listing.setCurrentRow(current_row - 1)

    def select_next(self):
        """ Select the next track """
        current_row = self.track_listing.currentRow()
        if current_row + 1 < self.track_listing.count():
            self.track_listing.setCurrentRow(current_row + 1)

    def move_up(self):
        """ Move the currently-selected track up in the track listing """
        LOGGER.debug("TrackListEditor.move_up")
        self.album_editor.record_undo()
        row = self.track_listing.currentRow()
        if row > 0:
            dest = row - 1
            item = self.track_listing.takeItem(row)
            self.track_listing.insertItem(dest, item)
            self.track_listing.setCurrentRow(dest)

    def move_down(self):
        """ Move the currently-selected track up in the track listing """
        LOGGER.debug("TrackListEditor.move_down")
        self.album_editor.record_undo()
        row = self.track_listing.currentRow()
        if row < self.track_listing.count() - 1:
            dest = row + 1
            item = self.track_listing.takeItem(row)
            self.track_listing.insertItem(dest, item)
            self.track_listing.setCurrentRow(dest)
