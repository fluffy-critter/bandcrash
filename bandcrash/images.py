""" Image manipulation routines """

import functools
import io
import logging
import os.path

import PIL.Image

from .util import slugify_filename

LOGGER = logging.getLogger(__name__)


def get_encoder_args(ext):
    """ Get the encoder arguments for a filetype """
    if ext.lower() in ('jpg', 'jpeg'):
        return {'quality': 99, 'subsampling': 0}
    if ext.lower() in ('webp'):
        return {'quality': 95}
    return {}


def load_image(in_path: str) -> PIL.Image.Image:
    """ Load an image into memory, pooling it """
    if not os.path.isfile(in_path):
        raise FileNotFoundError(f"Couldn't find image {in_path}")
    return PIL.Image.open(in_path)


def generate_image(in_path: str, size: int) -> PIL.Image.Image:
    """ Given an image path, generate a rendition that fits within the size constraint

    :param str in_path: Path to the file
    :param int size: Maximum size (both width and height)
    """
    image = load_image(in_path)
    out_w = int(min(image.width*size/image.height, size))
    out_h = int(min(image.height*size/image.width, size))
    if out_w > image.width or out_h > image.height:
        return image

    return image.resize(size=(out_w, out_h), resample=PIL.Image.Resampling.LANCZOS)


def generate_rendition(in_path: str, out_dir: str, size: int) -> tuple[str, int, int]:
    """ Given an image path and a size, save a rendition to disk

    :param str in_path: Path to the file
    :param str out_dir: Directory to store the file in
    :param int size: Rendition size:

    :returns: a tuple of file path, width, height
    """

    image = generate_image(in_path, size)
    basename, _ = os.path.splitext(os.path.basename(in_path))

    if image.mode in ('RGBA', 'LA', 'P'):
        ext = 'webp'
        mode = 'RGBA'
    else:
        ext = 'jpg'
        mode = 'RGB'

    out_file = slugify_filename(f'{basename}.{image.height}.{ext}')
    image.convert(mode).save(os.path.join(
        out_dir, out_file), **get_encoder_args(ext))
    LOGGER.info("Wrote image %s", out_file)

    return out_file, image.width, image.height


def make_blob(image: PIL.Image.Image, ext='jpeg') -> bytes:
    """ Convert an image rendition to compressed bytes """
    buffer = io.BytesIO()
    image.convert('RGB').save(buffer, format=ext, **get_encoder_args(ext))
    return buffer.getvalue()


def fix_orientation(image: PIL.Image.Image) -> PIL.Image.Image:
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
        [PIL.Image.Transpose.FLIP_LEFT_RIGHT],
        [PIL.Image.Transpose.ROTATE_180],
        [PIL.Image.Transpose.FLIP_TOP_BOTTOM],
        [PIL.Image.Transpose.FLIP_LEFT_RIGHT, PIL.Image.Transpose.ROTATE_90],
        [PIL.Image.Transpose.ROTATE_270],
        [PIL.Image.Transpose.FLIP_TOP_BOTTOM, PIL.Image.Transpose.ROTATE_90],
        [PIL.Image.Transpose.ROTATE_90],
    ]

    try:
        # pylint:disable=protected-access
        orientation = image.getexif()[exif_orientation_tag]
        sequence = exif_transpose_sequences[orientation]
        return functools.reduce(type(image).transpose, sequence, image)
    except (TypeError, AttributeError, KeyError):
        # either no EXIF tags or no orientation tag
        pass
    return image


@functools.lru_cache()
def known_extensions():
    """ Get a list of known image file extensions """
    # adapted from https://stackoverflow.com/a/71114152/318857
    exts = PIL.Image.registered_extensions()
    return {ex for ex, f in exts.items() if f in PIL.Image.OPEN}
