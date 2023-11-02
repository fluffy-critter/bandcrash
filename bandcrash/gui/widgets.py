""" Common custom widgets """

import logging
import os
import os.path

from PySide6.QtCore import QMargins, QPoint, QRect, QSize, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QColorDialog, QDialog, QFileDialog, QHBoxLayout,
                               QLabel, QLayout, QLineEdit, QPlainTextEdit,
                               QPushButton, QSizePolicy, QVBoxLayout, QWidget)

from .. import util
from .file_utils import FileRole

LOGGER = logging.getLogger(__name__)


def wrap_layout(layout: QLayout):
    """ Wrap a layout in a QWidget, which is for some reason not a standard Qt function """
    widget = QWidget()
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


class ColorPicker(QWidget):
    """ A color picker button """

    def __init__(self, parent=None, label=""):
        super().__init__(parent)

        self.label = label

        self._value = QColor.fromString('#000000')
        self._button = QPushButton()
        self._button.setAutoFillBackground(True)

        self.setName('#000000')

        self._button.clicked.connect(self.pickColor)

        hbox = QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(0)
        hbox.addWidget(self._button)
        self.setLayout(hbox)

    def pickColor(self):  # pylint:disable=invalid-name
        """ Pick a color """
        color = QColorDialog.getColor(self._value)
        if color.isValid():
            self.setValue(color)

    def value(self):
        """ Get the color as a Qt color object """
        return self._value

    def name(self):
        """ Get the color as a hex string """
        return self._value.name()

    def setValue(self, color):  # pylint:disable=invalid-name
        """ Set the color value by Qt color """
        self._value = color
        fg_color = 'white' if self._value.valueF() < 0.5 else 'black'
        self._button.setText(
            f'{self.label}: {color.name()}' if self.label else color.name())
        self._button.setStyleSheet(
            f'background-color: {color.name()}; color: {fg_color};')

    def setName(self, name):  # pylint:disable=invalid-name
        """ Set the color value by hex string """
        self.setValue(QColor.fromString(name))


class ErrorMessage(QDialog):
    """ An error box with details; the builtin QMessageBox behaves strangely """

    def __init__(self, parent, errors):
        super().__init__(parent)
        self.setWindowTitle("Error")
        self.setWindowModality(Qt.WindowModality.WindowModal)

        layout = QVBoxLayout()

        if len(errors) == 1:
            layout.addWidget(QLabel("An error occurred:"))
        else:
            layout.addWidget(QLabel(f"{len(errors)} errors occurred:"))

        text = QPlainTextEdit()
        text.setPlainText('\n\n'.join(str(e) for e in errors))
        text.setReadOnly(True)
        layout.addWidget(text)

        button = QPushButton("Okay")
        button.clicked.connect(self.accept)
        layout.addWidget(button)

        self.setLayout(layout)
