""" Version information

This one might be outdated but exists for the sake of builds that don't run
through Make (e.g. readthedocs)
"""

try:
    from .__build_version__ import __version__
except ImportError:
    __version__ = "0.6.0"
