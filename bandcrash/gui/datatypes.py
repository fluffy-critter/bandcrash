""" Data type conversion functions """

from PySide6.QtCore import Qt


def to_checkstate(val):
    """ Convert a bool to a qt CheckState """
    return Qt.CheckState.Checked if val else Qt.CheckState.Unchecked


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
        value = widget.checkState() == Qt.CheckState.Checked
        if value != dfl:
            data[key] = value
        elif key in data:
            del data[key]
