""" Data type conversion functions """

from PySide6 import QtCore


def to_checkstate(val):
    """ Convert a bool to a qt CheckState """
    return QtCore.Qt.Checked if val else QtCore.Qt.Unchecked


def apply_text_fields(data, fields, xform=lambda x: x):
    """ Apply textbox controls to backing storage

    :param dict data: Target dictionary
    :param list fields: List of (dict_key, widget)
    """
    for key, widget in fields:
        if value := widget.text():
            data[key] = xform(value)
        elif key in data:
            del data[key]


def apply_checkbox_fields(data, fields):
    """ Apply checkbox controls to backing storage

    :param dict data: Target dictionary
    :param list fields: List of (dict_key, widget, default)
    """
    for key, widget, dfl in fields:
        value = widget.checkState() == QtCore.Qt.Checked
        if value != dfl:
            data[key] = value
        elif key in data:
            del data[key]
