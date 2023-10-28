""" Blamscamp player backend """

import logging
import os.path

import jinja2

LOGGER = logging.getLogger(__name__)

try:
    from PySide6.QtWidgets import QWidget

    from ...gui import widgets

    class AlbumEditor(QWidget):
        """ Album editor for Blamscamp """

        def __init__(self):
            super().__init__()

            LOGGER.debug("bandcrash.AlbumEditor.__init__")

            layout = widgets.FlowLayout(self)
            layout.setSpacing(0)
            layout.setContentsMargins(0, 0, 0, 0)

            self.foreground = widgets.ColorPicker(self, "Foreground")
            self.background = widgets.ColorPicker(self, "Background")
            self.highlight = widgets.ColorPicker(self, "Highlight")
            layout.addWidget(self.foreground)
            layout.addWidget(self.background)
            layout.addWidget(self.highlight)
            self.setLayout(layout)

            self.album = {}
            self.data = {}

        @property
        def mapping(self):
            return (
                (self.foreground, 'foreground', '#000000'),
                (self.background, 'background', '#ffffff'),
                (self.highlight, 'highlight', '#7f0000')
            )

        def reset(self, album):
            """ Reset the values from the album's storage """
            LOGGER.debug("bandcrash.AlbumEditor.reset")

            self.album = album
            self.data = self.album.get("blamscamp", {})

            for widget, key, dfl in self.mapping:
                widget.setName(self.data.get(key, dfl))

        def apply(self):
            """ Apply the values to the album """
            LOGGER.debug("bandcrash.AlbumEditor.apply")

            for widget, key, dfl in self.mapping:
                if widget.name() != dfl:
                    self.data[key] = widget.name()
                elif key in self.data:
                    del self.data[key]

            if self.data:
                self.album['blamscamp'] = self.data
            elif 'blamscamp' in self.album:
                del self.album['blamscamp']

except ImportError:
    pass


class Player:
    @property
    def name(self):
        """ Get the player's name """
        return 'blamscamp'

    @property
    def art_rendition_sizes(self):
        """ Gets the rendition sizes needed for artworks """
        return {"1x": 150, "2x": 300}

    @property
    def album_gui(self):
        """ Gets the album GUI layout """
        return (
            ('foreground', 'color', '#000000'),
            ('background', 'color', '#ffffff'),
            ('highlight', 'color', '#7f0000'),
        )

    @property
    def track_gui(self):
        """ Gets the track GUI layout """
        return None

    @staticmethod
    def convert(album, output_dir, protections, **vars):
        """ Given album data and an output directory, generate the player """

        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

        for tmpl in ('index.html', 'player.js', 'player.css'):
            template = env.get_template(tmpl)
            with open(os.path.join(output_dir, tmpl), 'w', encoding='utf8') as outfile:
                LOGGER.debug("generating %s", tmpl)
                outfile.write(template.render(
                    album=album,
                    blamscamp=album.get('blamscamp', {}),
                    **vars))
                protections.add(tmpl)
