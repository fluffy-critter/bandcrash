""" Image manipulation routines """

import functools
import io
import os.path

import PIL.Image

from .util import slugify_filename


@functools.lru_cache()
def load_image(in_path: str) -> PIL.Image:
    """ Load an image into memory, pooling it """
    return PIL.Image.open(in_path)


@functools.lru_cache()
def generate_image(in_path: str, size: int) -> PIL.Image:
    """ Given an image path, generate a rendition that fits within the size constraint

    :param str in_path: Path to the file
    :param int size: Maximum size (both width and height)
    """
    image = load_image(in_path)
    out_w = int(min(image.width*size/image.height, size))
    out_h = int(min(image.height*size/image.width, size))
    if out_w > image.width or out_h > image.height:
        out_w = image.width
        out_h = image.height

    return image.resize(size=(out_w, out_h), resample=PIL.Image.LANCZOS)


@functools.lru_cache()
def generate_rendition(in_path: str, out_dir: str, size: int) -> str:
    """ Given an image path and a size, save a rendition to disk

    :param str in_path: Path to the file
    :param str out_dir: Directory to store the file in
    :param int size: Rendition size:

    :returns: a file path
    """

    image = generate_image(in_path, size)
    basename, _ = os.path.splitext(os.path.basename(in_path))
    out_file = slugify_filename(f'{basename}.{size}.jpg')
    image.convert('RGB').save(os.path.join(out_dir, out_file))

    return out_file


@functools.lru_cache()
def generate_blob(in_path: str, size: int, ext: str = "jpeg") -> bytes:
    """ Generate a data blob for a compressed image

    :param str in_path: Path to the file
    :param int size: Maximum rendition size
    :param str format: Output file format

    :returns: In-memory compressed file
    """
    buffer = io.BytesIO()
    generate_image(in_path, size).convert('RGB').save(buffer, format=ext)
    return buffer.getvalue()


def fix_orientation(image: PIL.Image) -> PIL.Image:
    """ adapted from https://stackoverflow.com/a/30462851/318857

        Apply Image.transpose to ensure 0th row of pixels is at the visual
        top of the image, and 0th column is the visual left-hand side.
        Return the original image if unable to determine the orientation.

        As per CIPA DC-008-2012, the orientation field contains an integer,
        1 through 8. Other values are reserved.
    """

    exif_orientation_tag = 0x0112
    exif_transpose_sequences = [
        [],
        [],
        [PIL.Image.FLIP_LEFT_RIGHT],
        [PIL.Image.ROTATE_180],
        [PIL.Image.FLIP_TOP_BOTTOM],
        [PIL.Image.FLIP_LEFT_RIGHT, PIL.Image.ROTATE_90],
        [PIL.Image.ROTATE_270],
        [PIL.Image.FLIP_TOP_BOTTOM, PIL.Image.ROTATE_90],
        [PIL.Image.ROTATE_90],
    ]

    try:
        # pylint:disable=protected-access
        orientation = image._getexif()[exif_orientation_tag]
        sequence = exif_transpose_sequences[orientation]
        return functools.reduce(type(image).transpose, sequence, image)
    except (TypeError, AttributeError, KeyError):
        # either no EXIF tags or no orientation tag
        pass
    return image
