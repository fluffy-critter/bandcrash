""" Common custom widgets """

import logging
import os
import os.path

from PySide6.QtCore import QMargins, QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import (QFileDialog, QFormLayout, QHBoxLayout, QLayout,
                               QLineEdit, QProgressBar, QPushButton,
                               QSizePolicy, QWidget)

from .. import util
from .file_utils import FileRole

LOGGER = logging.getLogger(__name__)


def wrap_layout(parent: QWidget, layout: QLayout):
    widget = QWidget(parent)
    widget.setLayout(layout)
    return widget


class FileSelector(QWidget):
    """ A file selector textbox with ... button """

    def __init__(self, role: FileRole, album_editor=None, text=''):
        super().__init__()

        layout = QHBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)

        self.role = role
        self.album_editor = album_editor
        self.file_path = QLineEdit(text)
        self.button = QPushButton("...")

        layout.addWidget(self.file_path)
        layout.addWidget(self.button)

        self.button.clicked.connect(self.choose_file)

    def choose_file(self):
        """ Pick a file """

        path = self.file_path.text()
        if self.album_editor:
            start_dir = self.album_editor.get_last_directory(self.role, path)
        elif self.file_path and os.path.isabs(path):
            start_dir = os.path.dirname(path)
        else:
            start_dir = self.role.default_directory

        LOGGER.debug("start_dir=%s filter=%s",
                     start_dir, self.role.file_filter)
        (filename, _) = QFileDialog.getOpenFileName(self,
                                                    f'Select your {self.role.name}',
                                                    start_dir,
                                                    self.role.file_filter)
        if filename:
            # Update the global default for files of this role
            filedir = os.path.dirname(filename)
            self.role.default_directory = filedir

            if self.album_editor:
                # Update the album editor's default for files of this role
                self.album_editor.set_last_directory(self.role, filedir)
                filename = util.make_relative_path(
                    self.album_editor.filename)(filename)
                os.path.dirname(filename)

            self.file_path.setText(filename)

    def text(self):
        """ Get the value out """
        return self.file_path.text()

    def setText(self, text):
        """ Set the value """
        # pylint:disable=invalid-name
        return self.file_path.setText(text)


class FuturesProgress(QWidget):
    """ A stack of progress indicators """

    def __init__(self, futures):
        super().__init__()

        self.futures = futures
        self.mapping = {}

        self.form = QFormLayout(self)
        for key, tasks in futures.items():
            progress_bar = QProgressBar(self)
            progress_bar.setMinimum(0)
            progress_bar.setMaximum(len(tasks))
            self.mapping[key] = progress_bar
            self.form.addRow(key, progress_bar)

        self.setLayout(self.form)

    def update(self):
        """ Update the progress indicators; returns True if everything's done """
        for key, tasks in self.futures.items():
            if key in self.mapping:
                if len([task for task in tasks if task.done()]) == len(tasks):
                    # This task set is finished, so we can remove the progress bar
                    self.form.removeRow(self.mapping[key])
                    del self.mapping[key]

        return bool(self.mapping)


class FlowLayout(QLayout):
    """ Layout with reflow
    adapted from https://doc.qt.io/qtforpython-6/examples/example_widgets_layouts_flowlayout.html
    """
    # pylint:disable=invalid-name,missing-function-docstring

    def __init__(self, parent=None):
        super().__init__(parent)

        if parent is not None:
            self.setContentsMargins(QMargins(0, 0, 0, 0))

        self._item_list = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self._item_list.append(item)

    def count(self):
        return len(self._item_list)

    def itemAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list[index]

        return None

    def takeAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)

        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self._do_layout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()

        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())

        size += QSize(2 * self.contentsMargins().top(),
                      2 * self.contentsMargins().top())
        return size

    def _do_layout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()

        for item in self._item_list:
            style = item.widget().style()
            layout_spacing_x = style.layoutSpacing(
                QSizePolicy.ControlType.PushButton,
                QSizePolicy.ControlType.PushButton,
                Qt.Orientation.Horizontal
            )
            layout_spacing_y = style.layoutSpacing(
                QSizePolicy.ControlType.PushButton,
                QSizePolicy.ControlType.PushButton,
                Qt.Orientation.Vertical
            )
            space_x = spacing + layout_spacing_x
            space_y = spacing + layout_spacing_y
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y()
