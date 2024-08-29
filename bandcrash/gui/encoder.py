""" Album encoder dialog """
import collections
import concurrent.futures
import itertools
import logging

from PySide6.QtCore import Qt, QTimer, Signal
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

        self.signal.connect(self.update_progress)

        self.setLayout(layout)

    def exec_(self):
        LOGGER.debug("overridden exec")
        for future in list(itertools.chain(*self.futures.values())):
            future.add_done_callback(self.signal.emit)

        # If everything finishes before the dialog presents itself, the thing
        # just stalls. So this is a little hack.
        QTimer.singleShot(250, self.check_finished)

        LOGGER.debug("parent exec")
        return super().exec_()

    def stop(self):
        """ End an encode due to error or cancelation """
        LOGGER.warning("Stopping encode")
        self.pool.shutdown(cancel_futures=True)
        self.reject()

    def check_finished(self):
        """ Watchdog to make sure we aren't waiting on an already-complete futures queue """
        for task in list(itertools.chain(*self.futures.values())):
            if not task.done():
                return

        if self.errors:
            self.reject()
        else:
            self.accept()

    def update_progress(self, future):
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
    with concurrent.futures.ThreadPoolExecutor(max_workers=config.num_threads) as pool:

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
