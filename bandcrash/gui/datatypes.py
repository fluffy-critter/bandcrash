""" Data type conversion functions """

import typing

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QLineEdit, QRadioButton

TrackData = dict[str, typing.Any]
TrackList = list[TrackData]


def to_checkstate(val):
    """ Convert a bool to a qt CheckState """
    return Qt.CheckState.Checked if val else Qt.CheckState.Unchecked


def apply_text_fields(data, fields: typing.Iterable[tuple[str, QLineEdit]],
                      xform=lambda x: x):
    """ Apply textbox controls to backing storage

    :param dict data: Target dictionary
    :param list fields: List of (dict_key, widget)
    """
    for key, widget in fields:
        if value := widget.text():
            data[key] = xform(value)
        elif key in data:
            del data[key]


def apply_checkbox_fields(data, fields: typing.Iterable[tuple[str, QCheckBox, bool]]):
    """ Apply checkbox controls to backing storage

    :param dict data: Target dictionary
    :param list fields: List of (dict_key, widget, default)
    """
    for key, widget, dfl in fields:
        value = widget.checkState() == Qt.CheckState.Checked
        if value != dfl:
            data[key] = value
        elif key in data:
            del data[key]


def apply_radio_fields(data,
                       fields: typing.Iterable[tuple[str, QRadioButton, bool]]):
    """ Apply radio button controls to backing storage """
    for key, widget, dfl in fields:
        value = widget.isChecked()
        if value != dfl:
            data[key] = value
        elif key in data:
            del data[key]
