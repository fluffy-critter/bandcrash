""" Album encoder dialog """
import collections
import concurrent.futures
import itertools
import logging
import os
import typing

from PySide6.QtCore import QSettings, Qt, QTimer, Signal
from PySide6.QtWidgets import QDialog, QFormLayout, QProgressBar, QPushButton

from .. import process

LOGGER = logging.getLogger(__name__)


class _Encoder(QDialog):
    """ Album encoder dialog box """
    signal = Signal(concurrent.futures.Future)

    def __init__(self, parent, pool, futures):
        super().__init__(parent)
        self.setWindowTitle("Encoding album")
        self.setWindowModality(Qt.WindowModality.WindowModal)

        self.pool = pool
        self.futures = futures

        layout = QFormLayout()

        self.progress: dict[str, QProgressBar] = {}
        for phase, items in futures.items():
            progress_bar = QProgressBar(self)
            progress_bar.setMinimum(0)
            progress_bar.setMaximum(len(items))
            self.progress[phase] = progress_bar
            layout.addRow(phase, progress_bar)

        self.abort = QPushButton("Abort")
        layout.addRow("", self.abort)
        self.abort.clicked.connect(self.stop)

        self.errors = []

        self.signal.connect(self.update)

        self.setLayout(layout)

    def exec_(self):
        LOGGER.debug("overridden exec")
        for future in list(itertools.chain(*self.futures.values())):
            future.add_done_callback(self.signal.emit)

        if self.errors:
            # An error occurred causing pre-rejection
            # Simply aborting execution here seems to mess up Qt, though, so
            # instead we just generate a fake update in the future
            LOGGER.debug("Errors already found, scheduling prejection")
            QTimer.singleShot(250, self.reject)

        LOGGER.debug("parent exec")
        return super().exec_()

    def stop(self):
        """ End an encode due to error or cancelation """
        LOGGER.warning("Stopping encode")
        self.pool.shutdown(cancel_futures=True)
        self.reject()

    def update(self, future):
        """ Update the progress """
        LOGGER.debug("Got update for future %s", future)
        done = True
        for phase, tasks in self.futures.items():
            remaining = len([task for task in tasks if not task.done()])
            LOGGER.debug("%s: %d tasks remaining", phase, remaining)
            if remaining:
                done = False
            self.progress[phase].setValue(len(tasks) - remaining)

        # check to see if the task failed
        if future:
            try:
                future.result()
            except concurrent.futures.CancelledError:
                pass
            except Exception as error:  # pylint:disable=broad-exception-caught
                LOGGER.exception("Got exception %s", error)
                self.errors.append(error)
                self.stop()

        if done:
            LOGGER.info("All tasks finished with %d errors", len(self.errors))
            if self.errors:
                self.reject()
            else:
                self.accept()


def encode(parent, config, album):
    """ Start the album encode and bring up a progress indicator dialog """
    settings = QSettings()
    pool = concurrent.futures.ThreadPoolExecutor(
        max_workers=typing.cast(int, settings.value("num_threads",
                                                    os.cpu_count() or 4)))

    futures: dict[str, list[concurrent.futures.Future]
                  ] = collections.defaultdict(list)

    LOGGER.debug("processing %s", config)
    process(config, album, pool, futures)

    LOGGER.debug("opening dialog")
    dialog = _Encoder(parent, pool, futures)
    LOGGER.debug("waiting for dialog")
    result = dialog.exec_()
    LOGGER.debug("got result %d (%d errors)", result, len(dialog.errors))
    return result, dialog.errors
