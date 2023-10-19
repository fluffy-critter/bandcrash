""" Common custom widgets """

from PySide6 import QtWidgets

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
