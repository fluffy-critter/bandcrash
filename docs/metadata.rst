Album metadata specification
============================

The album metadata is a fairly straightforward nested :py:class:`dict` structure that contains the metadata for the album and its tracks.

The CLI and GUI store this as a JSON file; however, when using :doc:`the library <library>` the data can be serialized and deserialized in whatever way makes the most sense for your application.

For the sake of clarity, here is a JSON file that represents a simple album.

.. code-block:: json

    {
       "artist": "My cool band name",
       "year": 2022,
       "title": "Our first album",
       "genre": "blipcore",
       "tracks": [
          {
             "filename": "first track.wav",
             "title": "The first track",
          },
          {
             "filename": "second track.wav",
             "title": "Another track",
             "lyrics": [
                 "We are singing",
                 "Singing a song",
                 "La la la la la"
             ]
          },
          {
             "filename": "third track.wav",
             "title": "Yet another track",
             "preview": false,
             "lyrics": "third track.txt",
             "artist": "Secret guest artist",
             "explicit": true
          }
       ],
       "blamscamp": {
          "foreground": "#7f7f7f",
          "background": "#ff00ff",
          "highlight": "#000000"
       }
    }

Below is a description of the different metadata fields that are used by the encoder.

General notes
-------------

File paths are relative to the encoder's input directory. From the CLI and GUI, this is generally the directory that the JSON file lives in; from the library, it's however the ``input_dir`` is set on the encoder's :py:class:`bandcrash.options.Options`.

Also, note that these metadata fields are only used by Bandcrash itself. The various web player templates may use other fields for their own configuration; see the individual player docs for more information on that.

Album data
----------

* **artist**: The artist for the album as a whole
* **title**: The album's title
* **year**: The release year
* **composer**: The album's composer
* **artwork**: an image file to use for the album's cover art (relative or absolute paths okay)
* **genre**: The default genre for all tracks
* **tracks**: an array of track descriptions, in album order
* **do_mp3**: Whether to build the album in MP3 format
* **do_ogg**: Whether to build the album in Ogg Vorbis format
* **do_flac**: Whether to build the album in FLAC format
* **do_preview**: Whether to build the web preview
* **do_zip**: Whether to build a zip file of each output format
* **do_butler**: Whether to upload the builds to itch.io
* **butler_target**: The itch.io Butler target (e.g. ``"fluffy/songs-of-substance"``)
* **butler_prefix**: Any prefix to add to the Butler channel name (e.g. ``"bonus-"`` will upload the MP3 album as ``"fluffy/songs-of-substance:bonus-mp3"``)

Track data
----------

Each track can include the following metadata values:

* **filename**: The audio file to encode into the final output track (ideally a lossless format, but anything supported by FLAC will work)
* **group**: The grouping of the track; for example, the title of a multi-movement piece.
* **title**: The title of this track, or the name of the movement if it's part of a group.
* **artist**: The specific artist for this track, if different from the album; useful for guest artists (e.g. "Sockpuppet ft. The Richard Donner Party")
* **composer**: The composer of this track
* **cover_of**: If this is a cover song, this is the original performing artist
* **genre**: The genre of this track
* **comment**: A comment to set in the track metadata
* **artwork**: Track-specific cover artwork
* **lyrics**: An array of strings, one line of lyrics per string; alternately, the filename to read lyrics from
* **hidden**: A boolean value; if set to true, hides the track from the web player entirely (defaults to false)
* **preview**: A boolean value; if set to true, generates a preview of this track (defaults to true)
* **explicit**: Whether this track contains explicit content (Defaults to false)

Player configuration
--------------------

Players can be configured via additional metadata added to the top-level album dict and, if supported, to track data. By convention, the player will keep its data sequestered in a dict of its own name; for example, the Blamscamp player keeps its data inside a ``"blamscamp"`` dict on the top-level object.

The configuration for players is shown below.

Blamscamp
^^^^^^^^^

.. autoclass:: bandcrash.players.blamscamp.Player
