""" Bandcrash GUI """
# pylint:disable=invalid-name,too-few-public-methods,too-many-ancestors
# type: ignore
import argparse
import collections
import concurrent.futures
import copy
import itertools
import json
import logging
import os
import os.path
import shutil
import subprocess
import threading
import typing

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QErrorMessage,
                               QFileDialog, QFormLayout, QFrame, QHBoxLayout,
                               QLabel, QLineEdit, QMainWindow, QMessageBox,
                               QProgressDialog, QPushButton, QSpinBox, QWidget)

from .. import __version__, util
from ..players import camptown
from . import datatypes, encoder, widgets
from .file_utils import FileRole
from .track_editor import TrackListEditor

LOG_LEVELS = [logging.WARNING, logging.INFO, logging.DEBUG]
LOGGER = logging.getLogger(__name__)


def add_menu_item(menu, name, method, shortcut=None, role=None):
    """ Add a menu item """
    action = menu.addAction(name)
    action.triggered.connect(method)
    if shortcut:
        action.setShortcut(QtGui.QKeySequence(shortcut))
    if role:
        action.setMenuRole(role)
    return action


def get_encode_options():
    """ Get the encoder options """

    from .. import options

    LOGGER.debug("get encode options")
    settings = QtCore.QSettings()
    LOGGER.debug("get config defaults")
    config = options.Options()

    for field in options.fields():
        LOGGER.debug("get field %s", field.name)
        if settings.contains(field.name):
            LOGGER.debug("type=%s value=%s", field.type,
                         settings.value(field.name))
            if field.type == list[str]:
                setattr(config, field.name, str(
                    settings.value(field.name)).split())
            else:
                setattr(config, field.name, settings.value(field.name))

    return config


class PreferencesWindow(QDialog):
    """ Sets application-level preferences """
    # pylint:disable=too-many-instance-attributes

    def __init__(self):
        super().__init__()
        LOGGER.debug("Creating prefs window")
        self.setWindowTitle("Bandcrash Preferences")
        self.setMinimumSize(500, 0)

        defaults = get_encode_options()

        def separator():
            frame = QFrame()
            frame.setFrameShape(QFrame.Shape.HLine)
            return frame

        layout = QFormLayout()
        layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.setLayout(layout)

        self.num_threads = QSpinBox(self)
        self.num_threads.setMinimum(1)
        self.num_threads.setMaximum(128)
        self.num_threads.setValue(defaults.num_threads)
        layout.addRow("Number of threads", self.num_threads)

        layout.addRow(separator())

        self.preview_encoder_args = QLineEdit()
        self.preview_encoder_args.setText(
            ' '.join(defaults.preview_encoder_args))
        layout.addRow("Preview encoder options", self.preview_encoder_args)

        self.mp3_encoder_args = QLineEdit()
        self.mp3_encoder_args.setText(' '.join(defaults.mp3_encoder_args))
        layout.addRow("MP3 encoder options", self.mp3_encoder_args)

        self.ogg_encoder_args = QLineEdit()
        self.ogg_encoder_args.setText(' '.join(defaults.ogg_encoder_args))
        layout.addRow("Ogg encoder options", self.ogg_encoder_args)

        self.flac_encoder_args = QLineEdit()
        self.flac_encoder_args.setText(' '.join(defaults.flac_encoder_args))
        layout.addRow("FLAC encoder options", self.flac_encoder_args)

        layout.addRow(separator())

        self.butler_path = widgets.FileSelector(
            FileRole.BINARY, text=defaults.butler_path)
        layout.addRow("Butler binary", self.butler_path)
        connect_button = QPushButton("Connect")
        self.butler_path.layout().addWidget(connect_button)
        connect_button.clicked.connect(self.connect_butler)

        buttons = QHBoxLayout()

        reset_button = QPushButton("Load Defaults")
        reset_button.clicked.connect(self.reset_defaults)
        buttons.addWidget(reset_button)

        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self.accept)
        apply_button.setDefault(True)
        buttons.addWidget(apply_button)

        layout.addRow(buttons)

        self.accepted.connect(self.apply)

    def apply(self):
        """ Save the settings out """
        settings = QtCore.QSettings()
        for key, value in (
            ('num_threads', self.num_threads.value()),

            ('preview_encoder_args', self.preview_encoder_args.text()),
            ('mp3_encoder_args', self.mp3_encoder_args.text()),
            ('ogg_encoder_args', self.ogg_encoder_args.text()),
            ('flac_encoder_args', self.flac_encoder_args.text()),

            ('butler_path', self.butler_path.text()),
        ):
            settings.setValue(key, value)

    def reset_defaults(self):
        """ Reset to defaults """
        from .. import options
        defaults = options.Options()

        LOGGER.debug("foo 1")

        self.num_threads.setValue(defaults.num_threads)
        self.preview_encoder_args.setText(
            ' '.join(defaults.preview_encoder_args))
        self.mp3_encoder_args.setText(' '.join(defaults.mp3_encoder_args))
        self.ogg_encoder_args.setText(' '.join(defaults.ogg_encoder_args))
        self.flac_encoder_args.setText(' '.join(defaults.flac_encoder_args))

        LOGGER.debug("foo 2")

        self.butler_path.setText(defaults.butler_path)

        LOGGER.debug("foo 3")

        self.apply()

    def connect_butler(self):
        """ Connect to butler """
        connection = subprocess.run([self.butler_path.text(), 'login', '--assume-yes'],
                                    capture_output=True,
                                    check=False,
                                    creationflags=getattr(
            subprocess, 'CREATE_NO_WINDOW', 0),
        )
        if connection.returncode:
            QMessageBox.warning(
                self, "Connection failed", connection.stdout.decode())
        else:
            QMessageBox.information(
                self, "Butler connected", connection.stdout.decode())

    @staticmethod
    def show_preferences():
        """ Show a preferences window """
        prefs_window = PreferencesWindow()
        prefs_window.setModal(True)
        prefs_window.exec()

        for window in BandcrashApplication.instance().windows:
            window.apply()


class AlbumEditor(QMainWindow):
    """ An album editor window """
    # pylint:disable=too-many-instance-attributes,too-many-public-methods

    class PathDelegate:
        """ Storage for the album editor's file information """

        def __init__(self, filename):
            self.filename = filename
            self.last_directory = {}

        def get_last_directory(self, role: FileRole, file_path: typing.Optional[str] = None):
            """ Get the last directory used for a file of a particular type

            :param role: The role
            :param str file_path: The current path to use as a reference
            """
            LOGGER.debug("get_last_directory %s %s", role, file_path)
            LOGGER.debug("   %s", self.last_directory)

            if file_path:
                if os.path.isabs(file_path):
                    # We can just use the existing file's directory
                    return os.path.dirname(file_path)

                if self.filename:
                    # Just make it absolute to our directory
                    return os.path.dirname(util.make_absolute_path(self.filename)(file_path))

            if self.filename:
                # We know where we are
                if role.name in self.last_directory:
                    # And we know where the last file of this type was put
                    return util.make_absolute_path(self.filename)(self.last_directory[role.name])
                # just assume the album's directory
                return os.path.dirname(self.filename)

            # We're not mapped to the filesystem, so just use the system default
            return role.default_directory

        def set_last_directory(self, role: FileRole, dir_path: str):
            """ Set the last directory for this role relative to our album file

            :param role: The role
            :param str dir_path: The directory to use as the reference
            """
            LOGGER.debug("set_last_directory %s %s", role, dir_path)
            if self.filename:
                self.last_directory[role.name] = util.make_relative_path(
                    self.filename)(dir_path)
            else:
                # We aren't mapped to the filesystem so let's just stash it as absolute
                self.last_directory[role.name] = dir_path
            LOGGER.debug("   -> %s", self.last_directory[role.name])

    def __init__(self, path: str):
        """ edit an album file

        :param str path: The path to the JSON file
        """
        # pylint:disable=too-many-statements,too-many-locals
        super().__init__()

        self.setMinimumSize(600, 0)

        self.output_dir: typing.Optional[str] = None

        self.undo_history: list[tuple[int, dict[str, typing.Any]]] = []
        self.redo_history: list[tuple[int, dict[str, typing.Any]]] = []

        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")

        standard_key = QtGui.QKeySequence.StandardKey

        add_menu_item(file_menu, "&New",
                      BandcrashApplication.file_new, standard_key.New)
        add_menu_item(file_menu, "&Open...",
                      BandcrashApplication.file_open, standard_key.Open)
        add_menu_item(file_menu, "&Save", self.save, standard_key.Save)
        add_menu_item(file_menu, "Save &As...",
                      self.save_as, standard_key.SaveAs)
        add_menu_item(file_menu, "&Revert", self.revert, standard_key.Refresh)
        add_menu_item(file_menu, "&Close", self.close, standard_key.Close)

        album_menu = menubar.addMenu("&Album")

        add_menu_item(album_menu, "&Encode", self.encode_album, "Ctrl+Shift+E")

        edit_menu = menubar.addMenu("&Edit")
        self.undo_menu = add_menu_item(
            edit_menu, "&Undo", self.undo_step, standard_key.Undo)
        self.redo_menu = add_menu_item(
            edit_menu, "&Redo", self.redo_step, standard_key.Redo)
        add_menu_item(edit_menu, "&Preferences", PreferencesWindow.show_preferences,
                      standard_key.Preferences,
                      QtGui.QAction.MenuRole.PreferencesRole)

        self.undo_menu.setEnabled(False)
        self.redo_menu.setEnabled(False)

        track_menu = menubar.addMenu("&Track")

        help_menu = menubar.addMenu("&Help")
        add_menu_item(help_menu, "&About...", self.show_about_box, None,
                      QtGui.QAction.MenuRole.AboutRole)
        add_menu_item(help_menu, "&Manual", self.open_manual, None)

        self.path_delegate = AlbumEditor.PathDelegate(path)
        self.save_hash = 0
        self.data: dict[str, typing.Any] = {'tracks': []}
        if path:
            self.reload(path)

        layout = QFormLayout()
        layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.setCentralWidget(widgets.wrap_layout(layout))

        self.artist = QLineEdit()
        self.title = QLineEdit()
        self.year = QLineEdit()
        self.year.setValidator(QtGui.QIntValidator(0, 99999))
        self.year.setMaxLength(5)
        self.genre = QLineEdit()
        self.artwork = widgets.FileSelector(FileRole.IMAGE, self.path_delegate)
        self.composer = QLineEdit()

        layout.addRow("Artist", self.artist)
        layout.addRow("Title", self.title)

        hbox = widgets.QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(0)
        hbox.addWidget(QLabel("Artist"))
        self.artist_url = QLineEdit()
        self.artist_url.setPlaceholderText("https://my-cool-band.com/")
        hbox.addWidget(self.artist_url)
        hbox.addWidget(QLabel("Album"))
        self.album_url = QLineEdit()
        self.album_url.setPlaceholderText(
            "https://my-cool-band.com/my-cool-album")
        hbox.addWidget(self.album_url)
        layout.addRow("URLs", hbox)

        theme_settings = widgets.FlowLayout()
        self.theme_foreground = widgets.ColorPicker(self, "Foreground")
        self.theme_background = widgets.ColorPicker(self, "Background")
        self.theme_highlight = widgets.ColorPicker(self, "Highlight")
        self.hide_footer = QCheckBox("Hide footer")
        theme_settings.addWidget(self.theme_foreground)
        theme_settings.addWidget(self.theme_background)
        theme_settings.addWidget(self.theme_highlight)
        theme_settings.addWidget(self.hide_footer)
        layout.addRow("Theme settings", theme_settings)

        self.user_css = widgets.FileSelector(
            FileRole.STYLESHEET, self.path_delegate)
        layout.addRow("User CSS", self.user_css)

        layout.addRow("Composer", self.composer)
        layout.addRow("Year", self.year)
        layout.addRow("Genre", self.genre)

        layout.addRow("Artwork", self.artwork)

        self.track_listing = TrackListEditor(self)
        layout.addRow("Audio Tracks", QWidget(self))
        layout.addRow(self.track_listing)

        add_menu_item(track_menu, "&Add...",
                      self.track_listing.add_track_button, "Ctrl+Shift+A")
        add_menu_item(track_menu, "&Delete",
                      self.track_listing.delete_track, "Ctrl+Del")
        add_menu_item(track_menu, "&Previous",
                      self.track_listing.select_previous, "PgUp")
        add_menu_item(track_menu, "&Next",
                      self.track_listing.select_next, "PgDown")
        add_menu_item(track_menu, "Move &up",
                      self.track_listing.move_up, "Alt+Up")
        add_menu_item(track_menu, "Move &down",
                      self.track_listing.move_down, "Alt+Down")

        checkboxes = widgets.FlowLayout()
        self.do_preview = QCheckBox("Web player")
        self.do_preview.setToolTip("Build a web-based preview player")
        self.do_mp3 = QCheckBox("MP3")
        self.do_mp3.setToolTip("Generate an album in MP3 format")
        self.do_ogg = QCheckBox("Ogg Vorbis")
        self.do_ogg.setToolTip("Generate an album in Ogg Vorbis format")
        self.do_flac = QCheckBox("FLAC")
        self.do_flac.setToolTip("Generate an album in FLAC lossless format")
        self.do_cdda = QCheckBox("CD")
        self.do_cdda.setToolTip("Generate .bin/.cue files for CD replication")
        self.do_cleanup = QCheckBox("Clean up files")
        self.do_cleanup.setToolTip("Remove extraneous/left over files")
        self.do_zip = QCheckBox("Build .zip files")
        self.do_zip.setToolTip("Make a .zip file for each output")
        checkboxes.addWidget(self.do_preview)
        checkboxes.addWidget(self.do_mp3)
        checkboxes.addWidget(self.do_ogg)
        checkboxes.addWidget(self.do_flac)
        checkboxes.addWidget(self.do_cdda)
        checkboxes.addWidget(self.do_cleanup)
        checkboxes.addWidget(self.do_zip)
        layout.addRow("Build options", checkboxes)

        butler_opts = QHBoxLayout()
        self.do_butler = QCheckBox()
        self.butler_target = QLineEdit()
        self.butler_target.setPlaceholderText("username/my-album-name")
        self.do_butler.setToolTip(
            "Automate uploads to itch.io via the butler tool")
        self.butler_prefix = QLineEdit()
        self.butler_prefix.setPlaceholderText("prefix")
        butler_opts.addWidget(self.do_butler)
        butler_opts.addWidget(self.butler_target, 50)
        butler_opts.addWidget(self.butler_prefix, 10)
        layout.addRow("itch.io butler", butler_opts)

        buttons = QHBoxLayout()

        start_button = QPushButton("Encode")
        start_button.clicked.connect(self.encode_album)

        buttons.addWidget(start_button)

        layout.addRow(buttons)

        self.setWindowTitle(self.filename or 'New Album')

        self.reset()

        for widget in (
            self.artist,
            self.title,
            self.genre,
            self.composer
        ):
            widget.textChanged.connect(self.apply)

        self.apply()
        self.update_hash()

    @property
    def filename(self):
        """ The current filename of the album """
        return self.path_delegate.filename

    @filename.setter
    def filename(self, path):
        self.path_delegate.filename = path

    def update_hash(self):
        """ Update the fingerprint hash """
        old_hash = self.save_hash
        self.save_hash = hash(repr(self.data))
        LOGGER.debug("updating hash from %s to %s", old_hash, self.save_hash)

    def unsaved(self):
        """ Returns whether there are unsaved changes """
        current_hash = hash(repr(self.data))
        LOGGER.debug("save_hash=%d cur_hash=%d", self.save_hash, current_hash)
        return self.save_hash != current_hash

    def reload(self, path):
        """ Load from the backing storage """
        with open(path, 'r', encoding='utf8') as file:
            try:
                self.data = typing.cast(dict[str, typing.Any], json.load(file))
                if 'tracks' not in self.data:
                    raise KeyError('tracks')
                self.update_hash()
            except (json.decoder.JSONDecodeError, KeyError, TypeError):
                err = QErrorMessage(self)
                err.showMessage("Invalid album JSON file")
                self.filename = ''
                self.data = {'tracks': []}

    @property
    def theme_colors(self) -> typing.Iterable[tuple[widgets.ColorPicker, str, str]]:
        """ mapping for theme items to color values """
        return (
            (self.theme_foreground, 'foreground', '#000000'),
            (self.theme_background, 'background', '#ffffff'),
            (self.theme_highlight, 'highlight', '#7f0000'),
        )

    def reset(self):
        """ Reset to the saved values """
        LOGGER.debug("AlbumEditor.reset")

        for key, text_field in (
            ('artist', self.artist),
            ('title', self.title),
            ('artist_url', self.artist_url),
            ('album_url', self.album_url),
            ('genre', self.genre),
            ('artwork', self.artwork.file_path),
            ('composer', self.composer),
            ('butler_target', self.butler_target),
            ('butler_prefix', self.butler_prefix),
        ):
            text_field.setText(self.data.get(key, ''))

        if 'year' in self.data:
            self.year.setText(str(self.data['year']))

        self.track_listing.reset(self.data['tracks'])

        self.do_preview.setCheckState(
            datatypes.to_checkstate(self.data.get('do_preview', True)))
        self.do_mp3.setCheckState(
            datatypes.to_checkstate(self.data.get('do_mp3', True)))
        self.do_ogg.setCheckState(
            datatypes.to_checkstate(self.data.get('do_ogg', True)))
        self.do_flac.setCheckState(
            datatypes.to_checkstate(self.data.get('do_flac', True)))
        self.do_cdda.setCheckState(
            datatypes.to_checkstate(self.data.get('do_cdda', False)))
        self.do_zip.setCheckState(
            datatypes.to_checkstate(self.data.get('do_zip', True)))
        self.do_cleanup.setCheckState(
            datatypes.to_checkstate(self.data.get('do_cleanup', True)))
        self.do_butler.setCheckState(
            datatypes.to_checkstate(self.data.get('do_butler', True)))

        theme = self.data.get('theme', self.data.get('blamscamp', {}))
        for color, key, dfl in self.theme_colors:
            color.setName(theme.get(key, dfl))
        self.user_css.setText(theme.get('user_css', ''))
        self.hide_footer.setCheckState(
            datatypes.to_checkstate(theme.get('hide_footer', False)))

        self.path_delegate.last_directory = self.data.get(
            '_gui', {}).get('lastdir', {})

    def apply(self):
        """ Apply edits to the saved data """
        LOGGER.debug("AlbumEditor.apply")

        self.record_undo()

        relpath = util.make_relative_path(self.filename)

        datatypes.apply_text_fields(self.data, (
            ('title', self.title),
            ('genre', self.genre),
            ('album_url', self.album_url),
            ('artist_url', self.artist_url),
            ('artist', self.artist),
            ('composer', self.composer),
            ('butler_target', self.butler_target),
            ('butler_prefix', self.butler_prefix),
        ))

        datatypes.apply_text_fields(self.data, (
                                    ('artwork', self.artwork.file_path),
                                    ),
                                    relpath)

        datatypes.apply_text_fields(self.data, (
            ('year', self.year),
        ),
            int)

        datatypes.apply_checkbox_fields(self.data, (
            ('do_preview', self.do_preview, True),
            ('do_mp3', self.do_mp3, True),
            ('do_ogg', self.do_ogg, True),
            ('do_flac', self.do_flac, True),
            ('do_cdda', self.do_cdda, False),
            ('do_zip', self.do_zip, True),
            ('do_cleanup', self.do_cleanup, True),
            ('do_butler', self.do_butler, True),
        ))
        self.track_listing.apply()

        theme = self.data.setdefault('theme', {})
        datatypes.apply_text_fields(theme, (
            ('user_css', self.user_css.file_path),
        ), relpath)
        datatypes.apply_checkbox_fields(theme, (
            ('hide_footer', self.hide_footer, False),
        ))
        for widget, key, dfl in self.theme_colors:
            if widget.name() != dfl:
                theme[key] = widget.name()
            elif key in theme:
                del theme[key]

        datatypes.apply_checkbox_fields(theme, (
            ('hide_footer', self.hide_footer, False),
        ))

        self.data['_gui'] = {
            'lastdir': self.path_delegate.last_directory
        }

        # update whether the itch.io checkbox is enabled
        butler_path = get_encode_options().butler_path
        if bool(butler_path and shutil.which(butler_path)):
            self.do_butler.setEnabled(True)
            self.butler_target.setPlaceholderText("username/my-album-name")
        else:
            self.do_butler.setEnabled(False)
            self.butler_target.setPlaceholderText(
                "Configure butler in the application preferences")

        self.track_listing.track_editor.update_placeholders(self.data)

    @property
    def history_state(self):
        """ Get the current edit history state """
        return self.track_listing.current_row, copy.deepcopy(self.data)

    @history_state.setter
    def history_state(self, state):
        """ Apply an edit history state """
        row, data = state
        self.data = data
        self.reset()
        self.track_listing.current_row = row

    def undo_step(self):
        """ Undo one action """
        if self.undo_history:
            LOGGER.debug("Undoing a step")
            self.redo_history.append(self.history_state)
            self.redo_menu.setEnabled(True)

            self.history_state = self.undo_history.pop()

            self.undo_menu.setEnabled(bool(self.undo_history))
            LOGGER.debug("history size = %d/%d",
                         len(self.undo_history), len(self.redo_history))

    def redo_step(self):
        """ Redo an undone action """
        if self.redo_history:
            LOGGER.debug("Redoing a step")
            self.undo_history.append(self.history_state)
            self.undo_menu.setEnabled(True)

            self.history_state = self.redo_history.pop()

            self.redo_menu.setEnabled(bool(self.redo_history))
            LOGGER.debug("history size = %d/%d",
                         len(self.undo_history), len(self.redo_history))

    def record_undo(self):
        """ Record an undo step """
        LOGGER.debug("Recording undo step")
        self.undo_history.append(self.history_state)
        self.undo_menu.setEnabled(True)
        self.redo_history.clear()
        self.redo_menu.setEnabled(False)
        LOGGER.debug("history size = %d/%d",
                     len(self.undo_history), len(self.redo_history))

    def save(self):
        """ Save the file to disk """
        LOGGER.debug("AlbumEditor.save")
        self.apply()
        if not self.filename:
            return self.save_as()

        with open(self.filename, 'w', encoding='utf8') as file:
            json.dump(self.data, file, indent=3)
            self.update_hash()
        return True

    def save_as(self):
        """ Save the file and change the name """
        LOGGER.debug("AlbumEditor.save_as")
        self.apply()

        role = FileRole.ALBUM
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Select your album file",
            os.path.dirname(self.filename) or role.default_directory,
            role.file_filter,
        )
        if path:
            self.renormalize_paths(self.filename, path)
            self.path_delegate.filename = path
            self.setWindowTitle(self.filename)
            self.reset()
            self.save()
            role.default_directory = os.path.dirname(self.filename)
            return True
        return False

    def revert(self):
        """ Revert all changes """
        LOGGER.debug("AlbumEditor.revert")
        self.apply()

        do_revert = True
        if self.unsaved():
            do_revert = False
            answer = QMessageBox.question(self, "Confirmation",
                                          "Really revert all changes?",
                                          (QMessageBox.StandardButton.Yes |
                                           QMessageBox.StandardButton.No),
                                          QMessageBox.StandardButton.No)

            if answer == QMessageBox.StandardButton.Yes:
                do_revert = True

        if do_revert:
            self.reload(self.filename)
            self.reset()

    def encode_album(self):
        """ Run the encoder process """
        # pylint:disable=too-many-branches,too-many-statements,too-many-locals
        LOGGER.debug("AlbumEditor.encode_album")
        self.apply()

        config = get_encode_options()
        config.input_dir = os.path.dirname(self.filename)

        # find a good default directory to stash the output in
        role = FileRole.OUTPUT
        if not self.output_dir:
            self.output_dir = role.default_directory

        LOGGER.debug("self.output_dir = %s", self.output_dir)

        # prompt for the actual output directory
        dialog = QFileDialog(
            self, "Choose an output directory", self.output_dir or '')
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
        dialog.setLabelText(QFileDialog.DialogLabel.Accept, "Encode")
        if not dialog.exec():
            return

        result = dialog.selectedFiles()
        if not result or not result[0]:
            return

        base_dir = result[0]

        # store our output directory for later
        self.output_dir = base_dir or ''

        role.default_directory = self.output_dir

        # Users will most likely be choosing a generic directory and NOT one that's
        # already sandboxed, so, let's make that sandbox for them (just for better UX).
        filename_parts = [part for part in [
            self.data.get(field) for field in ('artist', 'title')]
            if part]
        config.output_dir = os.path.join(
            self.output_dir, util.slugify_filename(' - '.join(filename_parts)))

        config.butler_args = BandcrashApplication.instance().config.butler_args.split()

        LOGGER.info("Album data: %s", self.data)
        LOGGER.info("Config options: %s", config)

        try:
            result, errors = encoder.encode(self, config, self.data)
        except RuntimeError as error:
            QMessageBox.warning(self, "An error occurred", str(error))

        LOGGER.debug("Finished: %d %s", result, errors)

        if errors:
            dlg = widgets.ErrorMessage(self, errors)
            dlg.exec_()
        elif result:
            task_names = "Encode"
            if config.do_butler:
                task_names += " and upload"
            result = QMessageBox.information(
                self,
                "Encode complete",
                f"{task_names} completed successfully",
                QMessageBox.StandardButton.Open | QMessageBox.StandardButton.Ok,
                QMessageBox.StandardButton.Open)  # type:ignore
            if result == QMessageBox.StandardButton.Open:
                QtGui.QDesktopServices.openUrl(
                    QtCore.QUrl.fromLocalFile(config.output_dir))

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
            if not os.path.exists(old_abs):
                LOGGER.warning(
                    "Not touching nonexisting path %s (%s)", path, old_abs)
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

        # last_directory is aliased into data instead of being copied
        LOGGER.debug("last_directory before %s",
                     self.path_delegate.last_directory)
        self.path_delegate.last_directory.update({
            key: renorm(value)
            for key, value
            in self.path_delegate.last_directory.items()
        })
        LOGGER.debug("after %s", self.path_delegate.last_directory)

    def show_about_box(self):
        """ Show the about box for the app """
        QMessageBox.about(self, "Bandcrash",
                          f"Bandcrash version {__version__}")

    def closeEvent(self, event):
        self.apply()
        do_close = True
        if self.unsaved():
            do_close = False
            answer = QMessageBox.question(self, "Unsaved changes",
                                          "You have unsaved changes. Really close?",
                                          (QMessageBox.StandardButton.Save |
                                           QMessageBox.StandardButton.Close |
                                           QMessageBox.StandardButton.Cancel))

            if answer == QMessageBox.StandardButton.Save:
                do_close = self.save()
            elif answer == QMessageBox.StandardButton.Close:
                do_close = True

        if do_close:
            BandcrashApplication.instance().release_editor(self)
        else:
            event.ignore()

    @staticmethod
    def open_manual():
        """ Opens the online documentation """
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(
            'https://bandcrash.readthedocs.io'))


class BandcrashApplication(QApplication):
    """ Application event handler """

    def __init__(self, config):
        super().__init__()

        self.config = config

        self.windows: set[AlbumEditor] = set()

        for path in config.open_files:
            self.open_file(os.path.abspath(path))

        QtCore.QTimer.singleShot(100, self.open_on_startup)

    @staticmethod
    def instance():
        """ Get the current app instance """
        return typing.cast(BandcrashApplication, QApplication.instance())

    @staticmethod
    def file_new():
        """ Create a new album file """
        BandcrashApplication.instance().open_file('')

    @staticmethod
    def file_open(or_new: bool = False):
        """ Dialog box to open an existing file

        :param bool or_new: Fallback to a new document if the user cancels
        """
        role = FileRole.ALBUM
        path, _ = QFileDialog.getOpenFileName(None,
                                              "Open album",
                                              role.default_directory,
                                              role.file_filter)
        if path or or_new:
            if path:
                role.default_directory = os.path.dirname(path)
            BandcrashApplication.instance().open_file(path)

    def open_file(self, path):
        """ Open a file into a new window """
        editor = AlbumEditor(path)
        editor.show()
        self.windows.add(editor)

    def release_editor(self, editor):
        """ Release a previously-opened editor """
        self.windows.remove(editor)

    def open_on_startup(self):
        """ Hacky way to open the file dialog on startup. there must be a better way... """
        if not self.windows:
            self.file_open(or_new=True)

    def event(self, evt):
        """ Handle an application-level event """
        LOGGER.debug("Event: %s", evt)
        if evt.type() == QtCore.QEvent.Type.FileOpen:
            LOGGER.debug("Got file open event: %s", evt.file())
            self.open_file(evt.file())
            return True

        return super().event(evt)


def main():
    """ instantiate an app """
    QtCore.QCoreApplication.setOrganizationName("busybee")
    QtCore.QCoreApplication.setOrganizationDomain("beesbuzz.biz")
    QtCore.QCoreApplication.setApplicationName("Bandcrash")

    parser = argparse.ArgumentParser(description="GUI for Bandcrash")
    parser.add_argument('-v', '--verbosity', action="count",
                        help="increase output verbosity", default=0)
    parser.add_argument('--version', action='version',
                        version=f"%(prog)s {__version__}")
    parser.add_argument('open_files', type=str, nargs='*')
    parser.add_argument('--butler-args', type=str, default='',
                        help='Options to pass along to butler push')
    options = parser.parse_args()

    logging.basicConfig(level=LOG_LEVELS[min(
        options.verbosity, len(LOG_LEVELS) - 1)],
        format='%(message)s')

    LOGGER.debug(
        "Opening bandcrash GUI with provided files: %s", options.open_files)

    app = BandcrashApplication(options)

    app.exec()


if __name__ == '__main__':
    main()
