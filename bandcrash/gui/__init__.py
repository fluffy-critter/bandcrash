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

from .. import __version__, process, util
from . import datatypes, widgets
from .track_editor import TrackListing

LOG_LEVELS = [logging.WARNING, logging.INFO, logging.DEBUG]
LOGGER = logging.getLogger(__name__)


def to_checkstate(val):
    """ Convert a bool to a qt CheckState """
    return QtCore.Qt.Checked if val else QtCore.Qt.Unchecked


def add_menu_item(menu, name, method, shortcut, role=None):
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
                setattr(config, field.name, settings.value(field.name).split())
            else:
                setattr(config, field.name, settings.value(field.name))

    return config


def default_music_dir(dfl):
    """ Find the best default music storage directory """
    for candidate in itertools.chain(
        QtCore.QStandardPaths.standardLocations(
            QtCore.QStandardPaths.MusicLocation),
        QtCore.QStandardPaths.standardLocations(
            QtCore.QStandardPaths.DocumentsLocation),
        QtCore.QStandardPaths.standardLocations(
            QtCore.QStandardPaths.HomeLocation),
    ):
        return candidate

    return dfl


class PreferencesWindow(QtWidgets.QDialog):
    """ Sets application-level preferences """
    # pylint:disable=too-many-instance-attributes

    def __init__(self):
        super().__init__()
        LOGGER.debug("Creating prefs window")
        self.setMinimumSize(500, 0)

        self.settings = QtCore.QSettings()

        layout = QtWidgets.QFormLayout(
            fieldGrowthPolicy=QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        self.setLayout(layout)

        # App-specific settings

        self.num_threads = QtWidgets.QSpinBox(minimum=1, maximum=128, value=int(
            self.settings.value("num_threads", os.cpu_count())))
        layout.addRow("Number of Threads", self.num_threads)

        layout.addRow(QtWidgets.QFrame(frameShape=QtWidgets.QFrame.HLine))

        # Encode settings

        defaults = get_encode_options()

        self.preview_encoder_args = QtWidgets.QLineEdit(
            text=' '.join(defaults.preview_encoder_args))
        layout.addRow("Preview encoder options", self.preview_encoder_args)
        self.mp3_encoder_args = QtWidgets.QLineEdit(
            text=' '.join(defaults.mp3_encoder_args))
        layout.addRow("MP3 encoder options", self.mp3_encoder_args)

        self.ogg_encoder_args = QtWidgets.QLineEdit(
            text=' '.join(defaults.ogg_encoder_args))
        layout.addRow("Ogg encoder options", self.ogg_encoder_args)

        self.flac_encoder_args = QtWidgets.QLineEdit(
            text=' '.join(defaults.flac_encoder_args))
        layout.addRow("FLAC encoder options", self.flac_encoder_args)

        layout.addRow(QtWidgets.QFrame(frameShape=QtWidgets.QFrame.HLine))

        self.butler_path = widgets.FileSelector(text=defaults.butler_path)
        layout.addRow("Butler binary", self.butler_path)
        connect_button = QtWidgets.QPushButton("Connect")
        self.butler_path.layout().addWidget(connect_button)
        connect_button.clicked.connect(self.connect_butler)

        buttons = QtWidgets.QHBoxLayout()

        reset_button = QtWidgets.QPushButton("Load Defaults")
        reset_button.clicked.connect(self.reset_defaults)
        buttons.addWidget(reset_button)

        apply_button = QtWidgets.QPushButton("Apply")
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

        self.num_threads.setValue(os.cpu_count())
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
                                    creationflags=subprocess.CREATE_NO_WINDOW,
                                    )
        if connection.returncode:
            QtWidgets.QMessageBox.warning(
                self, "Connection failed", connection.stdout.decode())
        else:
            QtWidgets.QMessageBox.information(
                self, "Butler connected", connection.stdout.decode())

    @staticmethod
    def show_preferences():
        """ Show a preferences window """
        prefs_window = PreferencesWindow()
        prefs_window.setModal(True)
        prefs_window.exec()


class AlbumEditor(QtWidgets.QMainWindow):
    """ An album editor window """
    # pylint:disable=too-many-instance-attributes

    def __init__(self, path: str):
        """ edit an album file

        :param str path: The path to the JSON file
        """
        # pylint:disable=too-many-statements
        super().__init__()

        self.setMinimumSize(600, 0)

        self.output_dir = None

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
                      QtGui.QAction.PreferencesRole)

        self.filename = path
        self.data: typing.Dict[str, typing.Any] = {'tracks': []}
        if path:
            AlbumEditor.default_open_dir(os.path.dirname(path))
            self.reload(path)

        layout = QtWidgets.QFormLayout(
            fieldGrowthPolicy=QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        self.setCentralWidget(QtWidgets.QWidget(layout=layout))
        self.layout = layout

        self.artist = QtWidgets.QLineEdit(placeholderText="Artist name")
        self.title = QtWidgets.QLineEdit(placeholderText="Album title")
        self.year = QtWidgets.QLineEdit(
            placeholderText="1978",
            validator=QtGui.QIntValidator(0, 99999),
            maxLength=5)
        self.genre = QtWidgets.QLineEdit(
            placeholderText="Avant-Industrial Loungecore")
        self.artwork = widgets.FileSelector(self)
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

        checkboxes = widgets.FlowLayout()
        self.do_preview = QtWidgets.QCheckBox("Web preview")
        self.do_mp3 = QtWidgets.QCheckBox("MP3")
        self.do_ogg = QtWidgets.QCheckBox("Ogg Vorbis")
        self.do_flac = QtWidgets.QCheckBox("FLAC")
        self.do_zip = QtWidgets.QCheckBox("Build .zip files")
        self.do_cleanup = QtWidgets.QCheckBox("Clean extra files")
        checkboxes.addWidget(self.do_preview)
        checkboxes.addWidget(self.do_mp3)
        checkboxes.addWidget(self.do_ogg)
        checkboxes.addWidget(self.do_flac)
        checkboxes.addWidget(self.do_zip)
        checkboxes.addWidget(self.do_cleanup)
        layout.addRow("Build options", checkboxes)

        butler_opts = QtWidgets.QHBoxLayout()
        self.do_butler = QtWidgets.QCheckBox()
        self.butler_target = QtWidgets.QLineEdit(
            placeholderText="username/my-album-name")
        self.butler_prefix = QtWidgets.QLineEdit(
            placeholderText="prefix", maxLength=10)
        butler_opts.addWidget(self.do_butler)
        butler_opts.addWidget(self.butler_target, 50)
        butler_opts.addWidget(self.butler_prefix, 10)
        layout.addRow("itch.io", butler_opts)

        buttons = QtWidgets.QHBoxLayout()

        start_button = QtWidgets.QPushButton("Encode")
        start_button.clicked.connect(self.encode_album)

        buttons.addWidget(start_button)

        layout.addRow(buttons)

        self.setWindowTitle(self.filename or 'New Album')

        self.reset()

    def file_new(self):
        """ Create a new album file """
        AlbumEditor('').show()

    def file_open(self):
        """ Dialog box to open an existing file """
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            caption="New album file",
            filter="Album files (*.json *.bcalbum)",
            dir=AlbumEditor.default_open_dir())
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
            ('do_preview', self.do_mp3, True),
            ('do_mp3', self.do_mp3, True),
            ('do_ogg', self.do_ogg, True),
            ('do_flac', self.do_flac, True),
            ('do_zip', self.do_zip, True),
            ('do_cleanup', self.do_cleanup, True),
            ('do_butler', self.do_butler, True),
        ))
        self.track_listing.apply()

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

        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            caption="Select your album file",
            filter="Album files (*.bcalbum *.json)",
            dir=os.path.dirname(self.filename) or AlbumEditor.default_open_dir())
        if path:
            self.renormalize_paths(self.filename, path)
            self.filename = path
            self.setWindowTitle(self.filename)
            self.reset()
            self.save()
            AlbumEditor.default_open_dir(os.path.dirname(self.filename))

        self.reset()

    def revert(self):
        """ Revert all changes """
        LOGGER.debug("AlbumEditor.revert")
        self.reload(self.filename)
        self.reset()

    def encode_album(self):
        """ Run the encoder process """
        # pylint:disable=too-many-branches,too-many-statements
        LOGGER.debug("AlbumEditor.encode_album")
        self.apply()

        config = get_encode_options()
        config.input_dir = os.path.dirname(self.filename)

        # find a good default directory to stash the output in
        settings = QtCore.QSettings()
        if self.output_dir is None:
            if settings.contains("last_album_output"):
                self.output_dir = settings.value("last_album_output")
            else:
                self.output_dir = default_music_dir(config.input_dir)

        # prompt for the actual output directory
        base_dir = QtWidgets.QFileDialog.getExistingDirectory(
            dir=self.output_dir,
            caption="Choose an output directory")
        if not base_dir:
            return

        # store our output directory for later
        self.output_dir = base_dir
        settings.setValue("last_album_output", self.output_dir)

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
            max_workers=int(settings.value("num_threads", os.cpu_count())))
        futures = collections.defaultdict(list)

        try:
            process(config, self.data, threadpool, futures)
        except RuntimeError as e:
            QtWidgets.QMessageBox.critical(self, "An error occurred", str(e))
            return

        # Eventually I want to use FuturesProgress to show structured info but
        # for now this'll do

        errors = []
        all_tasks = list(itertools.chain(*futures.values()))
        progress = QtWidgets.QProgressDialog(
            "Encoding album...", "Abort", 0, len(all_tasks), self)
        progress.setWindowModality(QtCore.Qt.WindowModal)

        for task in concurrent.futures.as_completed(all_tasks):
            pending = [t for t in all_tasks if not t.done()]
            LOGGER.debug("%d pending tasks", len(pending))

            progress.setValue(len(all_tasks) - len(pending))
            if progress.wasCanceled():
                threadpool.shutdown(cancel_futures=True)

            try:
                task.result()
            except Exception as e:  # pylint:disable=broad-exception-caught
                LOGGER.exception("Background task generated an exception")
                errors.append(e)

        if errors:
            msgbox = QtWidgets.QMessageBox(self)
            if len(errors) == 1:
                msgbox.setText("An error occurred")
            else:
                msgbox.setText("Some errors occurred")
            msgbox.setDetailedText('\n\n'.join(
                f'{type(e)}: {e}' for e in errors))
            msgbox.exec()
        elif not progress.wasCanceled() and all_tasks:
            result = QtWidgets.QMessageBox.information(self,
                                                       "Encode complete",
                                                       "Encoding completed successfully",
                                                       QtWidgets.QMessageBox.StandardButton.Open |
                                                       QtWidgets.QMessageBox.StandardButton.Ok,
                                                       QtWidgets.QMessageBox.StandardButton.Open)
            if result == QtWidgets.QMessageBox.StandardButton.Open:
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

    @staticmethod
    def default_open_dir(set_value=None):
        """ Set or get the default directory for album files """
        settings = QtCore.QSettings()
        if set_value:
            settings.setValue("last_album_dir", set_value)
            settings.sync()

        dfl = default_music_dir(os.getcwd())
        ret = settings.value("last_album_dir", dfl)
        if not os.path.isdir(ret):
            ret = dfl
        return ret


def open_file(path):
    """ Open a file for editing """
    editor = AlbumEditor(path)
    editor.show()


class BandcrashApplication(QtWidgets.QApplication):
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
            path, _ = QtWidgets.QFileDialog.getOpenFileName(caption="Open album",
                                                            filter="Album files (*.json *.bcalbum)",
                                                            dir=AlbumEditor.default_open_dir())
            AlbumEditor(path).show()

    def event(self, evt):
        """ Handle an application-level event """
        LOGGER.debug("Event: %s", evt)
        if evt.type() == QtCore.QEvent.FileOpen:
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
