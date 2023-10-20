""" Common custom widgets """

from PySide6 import QtWidgets
from PySide6.QtCore import QMargins, QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QSizePolicy

from .. import util


class FileSelector(QtWidgets.QWidget):
    """ A file selector textbox with ... button """

    def __init__(self, album_editor=None, text=''):
        super().__init__()

        layout = QtWidgets.QHBoxLayout()
        # layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)

        self.album_editor = album_editor
        self.file_path = QtWidgets.QLineEdit(text=text)
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

    def text(self):
        """ Get the value out """
        return self.file_path.text()

    def setText(self, text):
        """ Set the value """
        # pylint:disable=invalid-name
        return self.file_path.setText(text)


class FuturesProgress(QtWidgets.QWidget):
    """ A stack of progress indicators """

    def __init__(self, futures):
        super().__init__()

        self.futures = futures
        self.mapping = {}

        self.layout = QtWidgets.QFormLayout()
        for key, tasks in futures.items():
            progress_bar = QtWidgets.QProgressBar(
                minimum=0, maximum=len(tasks))
            self.mapping[key] = progress_bar
            self.layout.addRow(key, progress_bar)

        self.setLayout(self.layout)

    def update(self):
        """ Update the progress indicators; returns True if everything's done """
        for key, tasks in self.futures.items():
            if key in self.mapping:
                if len([task for task in tasks if task.done()]) == len(tasks):
                    # This task set is finished, so we can remove the progress bar
                    self.layout.removeRow(self.mapping[key])
                    del self.mapping[key]

        return bool(self.mapping)


class FlowLayout(QtWidgets.QLayout):
    """ Layout with reflow
    adapted from https://doc.qt.io/qtforpython-6/examples/example_widgets_layouts_flowlayout.html
    """

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
                QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal
            )
            layout_spacing_y = style.layoutSpacing(
                QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical
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
