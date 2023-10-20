""" Make universal2 builds of certain platform-dependent wheels.

1. Download the wheels with:

poetry run python3 -m pip download --only-binary=:all: --platform macosx_10_10_x86_64 Pillow
poetry run python3 -m pip download --only-binary=:all: --platform macosx_11_0_arm64 Pillow

2. run this script with (x86file) (armfile) (outfile)

3. install the wheel locally with

poetry run python3 -m pip install whatever.whl


 """
import sys

from delocate.fuse import fuse_wheels

fuse_wheels(*sys.argv[1:])
