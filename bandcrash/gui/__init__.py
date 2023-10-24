""" Bandcrash GUI """
# pylint:disable=invalid-name,too-few-public-methods,too-many-ancestors
# type: ignore
import argparse
import collections
import concurrent.futures
import itertools
import json
import logging
import os
import os.path
import subprocess
import threading
import typing

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QErrorMessage,
                               QFileDialog, QFormLayout, QFrame, QHBoxLayout,
                               QLabel, QLineEdit, QMainWindow, QMessageBox,
                               QProgressDialog, QPushButton, QSpinBox, QWidget)

from .. import __version__, process, util
from . import datatypes, widgets
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
        self.setMinimumSize(500, 0)

        self.settings = QtCore.QSettings()

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
        self.num_threads.setValue(
            typing.cast(int,
                        self.settings.value("num_threads",
                                            os.cpu_count())))
        layout.addRow("Number of Threads", self.num_threads)

        layout.addRow(separator())

        defaults = get_encode_options()

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
        for key, value in (
            ('num_threads', self.num_threads.value()),

            ('preview_encoder_args', self.preview_encoder_args.text()),
            ('mp3_encoder_args', self.mp3_encoder_args.text()),
            ('ogg_encoder_args', self.ogg_encoder_args.text()),
            ('flac_encoder_args', self.flac_encoder_args.text()),

            ('butler_path', self.butler_path.text()),
        ):
            self.settings.setValue(key, value)

        self.settings.sync()

    def reset_defaults(self):
        """ Reset to defaults """
        from .. import options
        defaults = options.Options()

        LOGGER.debug("foo 1")

        self.num_threads.setValue(os.cpu_count() or 4)
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
        connection = subprocess.run([self.butler_path.text(), 'login'],
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


class AlbumEditor(QMainWindow):
    """ An album editor window """
    # pylint:disable=too-many-instance-attributes

    def __init__(self, path: str):
        """ edit an album file

        :param str path: The path to the JSON file
        """
        # pylint:disable=too-many-statements
        super().__init__()

        self.setMinimumSize(600, 0)

        self.output_dir: typing.Optional[str] = None
        self.last_directory: dict[str, str] = {}

        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")

        add_menu_item(file_menu, "&New", self.file_new, "Ctrl+N")
        add_menu_item(file_menu, "&Open...", self.file_open, "Ctrl+O")
        add_menu_item(file_menu, "&Save", self.save, "Ctrl+S")
        add_menu_item(file_menu, "Save &As...", self.save_as, "Ctrl+Shift+S")
        add_menu_item(file_menu, "&Revert", self.revert, "Ctrl+Shift+R")
        add_menu_item(file_menu, "&Close", self.close, "Ctrl+W")

        album_menu = menubar.addMenu("&Album")

        add_menu_item(album_menu, "&Encode", self.encode_album, "Ctrl+Enter")

        edit_menu = menubar.addMenu("&Edit")
        add_menu_item(edit_menu, "&Preferences", PreferencesWindow.show_preferences, "Ctrl+,",
                      QtGui.QAction.MenuRole.PreferencesRole)

        help_menu = menubar.addMenu("&Help")
        add_menu_item(help_menu, "&About...", self.show_about_box, None,
                      QtGui.QAction.MenuRole.AboutRole)

        self.filename = path
        self.data: dict[str, typing.Any] = {'tracks': []}
        if path:
            self.reload(path)

        layout = QFormLayout()
        layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.setCentralWidget(widgets.wrap_layout(self, layout))

        self.artist = QLineEdit()
        self.title = QLineEdit()
        self.year = QLineEdit()
        self.year.setValidator(QtGui.QIntValidator(0, 99999))
        self.year.setMaxLength(5)
        self.genre = QLineEdit()
        self.artwork = widgets.FileSelector(FileRole.IMAGE, self)
        self.composer = QLineEdit()
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

        self.track_listing = TrackListEditor(self)
        layout.addRow("Audio Tracks", QWidget(self))
        layout.addRow(self.track_listing)

        checkboxes = widgets.FlowLayout()
        self.do_preview = QCheckBox("Web preview")
        self.do_mp3 = QCheckBox("MP3")
        self.do_ogg = QCheckBox("Ogg Vorbis")
        self.do_flac = QCheckBox("FLAC")
        self.do_zip = QCheckBox("Build .zip files")
        self.do_cleanup = QCheckBox("Clean extra files")
        checkboxes.addWidget(self.do_preview)
        checkboxes.addWidget(self.do_mp3)
        checkboxes.addWidget(self.do_ogg)
        checkboxes.addWidget(self.do_flac)
        checkboxes.addWidget(self.do_zip)
        checkboxes.addWidget(self.do_cleanup)
        layout.addRow("Build options", checkboxes)

        butler_opts = QHBoxLayout()
        self.do_butler = QCheckBox()
        self.butler_target = QLineEdit()
        self.butler_target.setPlaceholderText("username/my-album-name")
        self.butler_prefix = QLineEdit()
        self.butler_prefix.setPlaceholderText("prefix")
        butler_opts.addWidget(self.do_butler)
        butler_opts.addWidget(self.butler_target, 50)
        butler_opts.addWidget(self.butler_prefix, 10)
        layout.addRow("itch.io", butler_opts)

        buttons = QHBoxLayout()

        start_button = QPushButton("Encode")
        start_button.clicked.connect(self.encode_album)

        buttons.addWidget(start_button)

        layout.addRow(buttons)

        self.setWindowTitle(self.filename or 'New Album')

        self.reset()

    @staticmethod
    def file_new():
        """ Create a new album file """
        AlbumEditor('').show()

    @staticmethod
    def file_open(or_new: bool = False):
        """ Dialog box to open an existing file

        :param bool or_new: Fallback to a new document if
         """
        role = FileRole.ALBUM
        path, _ = QFileDialog.getOpenFileName(None,
                                              "Open album",
                                              role.default_directory,
                                              role.file_filter)
        if path or or_new:
            if path:
                role.default_directory = os.path.dirname(path)
            editor = AlbumEditor(path)
            editor.show()
            return editor

        return None

    def reload(self, path):
        """ Load from the backing storage """
        with open(path, 'r', encoding='utf8') as file:
            try:
                self.data = typing.cast(dict[str, typing.Any], json.load(file))
                if 'tracks' not in self.data:
                    raise KeyError('tracks')
            except (json.decoder.JSONDecodeError, KeyError, TypeError):
                err = QErrorMessage(self)
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
            ('butler_target', self.butler_target),
            ('butler_prefix', self.butler_prefix),
        ):
            widget.setText(self.data.get(key, ''))

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
        self.do_zip.setCheckState(
            datatypes.to_checkstate(self.data.get('do_zip', True)))
        self.do_cleanup.setCheckState(
            datatypes.to_checkstate(self.data.get('do_cleanup', True)))
        self.do_butler.setCheckState(
            datatypes.to_checkstate(self.data.get('do_butler', True)))

        self.last_directory = self.data.get('_gui', {}).get('lastdir', {})

    def apply(self):
        """ Apply edits to the saved data """
        LOGGER.debug("AlbumEditor.apply")
        relpath = util.make_relative_path(self.filename)

        datatypes.apply_text_fields(self.data,
                                    (
                                        ('title', self.title),
                                        ('genre', self.genre),
                                        ('artist', self.artist),
                                        ('composer', self.composer),
                                        ('butler_target', self.butler_target),
                                        ('butler_prefix', self.butler_prefix),
                                    ))

        datatypes.apply_text_fields(self.data,
                                    (('artwork', self.artwork.file_path),),
                                    relpath)

        datatypes.apply_text_fields(self.data,
                                    (('year', self.year),),
                                    int)

        datatypes.apply_checkbox_fields(self.data, (
            ('do_preview', self.do_preview, True),
            ('do_mp3', self.do_mp3, True),
            ('do_ogg', self.do_ogg, True),
            ('do_flac', self.do_flac, True),
            ('do_zip', self.do_zip, True),
            ('do_cleanup', self.do_cleanup, True),
            ('do_butler', self.do_butler, True),
        ))
        self.track_listing.apply()

        geom = self.geometry()
        self.data['_gui'] = {
            'geom': [geom.x(), geom.y(), geom.width(), geom.height()],
            'lastdir': self.last_directory
        }

    def save(self):
        """ Save the file to disk """
        LOGGER.debug("AlbumEditor.save")
        if self.filename:
            self.apply()

            with open(self.filename, 'w', encoding='utf8') as file:
                json.dump(self.data, file, indent=3)
        else:
            self.save_as()

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
            self.filename = path
            self.setWindowTitle(self.filename)
            self.reset()
            self.save()
            role.default_directory = os.path.dirname(self.filename)

        self.reset()

    def revert(self):
        """ Revert all changes """
        LOGGER.debug("AlbumEditor.revert")
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
        settings = QtCore.QSettings()
        role = FileRole.OUTPUT
        if not self.output_dir:
            self.output_dir = role.default_directory

        LOGGER.debug("self.output_dir = %s", self.output_dir)

        # prompt for the actual output directory
        base_dir = QFileDialog.getExistingDirectory(
            self,
            "Choose an output directory",
            self.output_dir or '')
        if not base_dir:
            return

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

        LOGGER.info("Album data: %s", self.data)
        LOGGER.info("Config options: %s", config)

        threadpool = concurrent.futures.ThreadPoolExecutor(
            max_workers=typing.cast(int, settings.value("num_threads",
                                                        os.cpu_count() or 4)))
        futures: dict[str, list[concurrent.futures.Future]
                      ] = collections.defaultdict(list)

        # Eventually I want to use FuturesProgress to show structured info
        # and not block the UI thread but for now this'll do

        errors = []
        progress = QProgressDialog(
            "Encoding album...", "Abort", 0, 1, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)

        all_tasks = []
        try:
            process(config, self.data, threadpool, futures)

            all_tasks = list(itertools.chain(*futures.values()))
            progress.setMaximum(len(all_tasks))

            for task in concurrent.futures.as_completed(all_tasks):
                pending = [t for t in all_tasks if not t.done()]
                LOGGER.debug("%d pending tasks", len(pending))

                progress.setValue(len(all_tasks) - len(pending))
                if progress.wasCanceled():
                    threadpool.shutdown(cancel_futures=True)

                task.result()
        except Exception as e:  # pylint:disable=broad-exception-caught
            threadpool.shutdown(cancel_futures=True)
            errors.append(e)

        progress.reset()

        for task in all_tasks:
            try:
                task.result()
            except Exception as e:  # pylint:disable=broad-exception-caught
                errors.append(e)

        if errors:
            LOGGER.debug("errors: %d %s", len(errors), errors)
            msgbox = QMessageBox(
                QMessageBox.Icon.Critical, "Error", "An error occurred")
            msgbox.setParent(self)
            text = f"An error occurred: {str(errors[0])}"
            if len(errors) > 1:
                # For some reason mypy isn't seeing setOption or the Option flag type
                msgbox.setOption(  # type:ignore[attr-defined]
                    QMessageBox.Option.DontUseNativeDialog)  # type:ignore[attr-defined]
                text += f", plus {len(errors)-1} more."
                msgbox.setDetailedText('\n\n'.join(
                    str(e) for e in errors))
            msgbox.setText(text)
            msgbox.exec()
        elif not progress.wasCanceled() and all_tasks:
            task_names = "Encode"
            if config.do_butler:
                task_names += " and upload"
            result = QMessageBox.information(
                self,
                "Encode complete",
                f"{task_names} completed successfully",
                QMessageBox.StandardButton.Open |
                QMessageBox.StandardButton.Ok,
                QMessageBox.StandardButton.Open)
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
        LOGGER.debug("last_directory before %s", self.last_directory)
        self.last_directory.update({
            key: renorm(value)
            for key, value
            in self.last_directory.items()
        })
        LOGGER.debug("after %s", self.last_directory)

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

    def show_about_box(self):
        """ Show the about box for the app """
        QMessageBox.about(self, "Bandcrash",
                          f"Bandcrash version {__version__.__version__}")


def open_file(path):
    """ Open a file for editing """
    editor = AlbumEditor(path)
    editor.show()


class BandcrashApplication(QApplication):
    """ Application event handler """

    def __init__(self, open_files):
        super().__init__()

        self.opened = False

        for path in open_files:
            open_file(os.path.abspath(path))
            self.opened = True

        QtCore.QTimer.singleShot(50, self.open_on_startup)

    def open_on_startup(self):
        """ Hacky way to open the file dialog on startup. there must be a better way... """
        if not self.opened:
            AlbumEditor.file_open(or_new=True)

    def event(self, evt):
        """ Handle an application-level event """
        LOGGER.debug("Event: %s", evt)
        if evt.type() == QtCore.QEvent.Type.FileOpen:
            LOGGER.debug("Got file open event: %s", evt.file())
            open_file(evt.file())
            self.opened = True
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
                        version="%(prog)s " + __version__.__version__)
    parser.add_argument('open_files', type=str, nargs='*')
    options = parser.parse_args()

    logging.basicConfig(level=LOG_LEVELS[min(
        options.verbosity, len(LOG_LEVELS) - 1)],
        format='%(message)s')

    LOGGER.debug(
        "Opening bandcrash GUI with provided files: %s", options.open_files)

    app = BandcrashApplication(options.open_files)

    app.exec()


if __name__ == '__main__':
    main()
