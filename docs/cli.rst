Using the CLI
=============

Installation
------------

The preferred way to install the CLI is using ``pip``::

   pip install bandcrash

See ``bandcrash --help`` for detailed help on the CLI.

Album setup
-----------

You can bootstrap an album JSON file with::

   bandcrash --init input_dir

where ``input_dir`` is where you've kept a bunch of .wav files for your album tracks. This will generate a file named ``album.json`` by default, although you can override this name using the ``--json`` parameter.

Next, see :doc:`the metadata format <metadata>` for additional information on what goes inside this JSON file.

Encoding
--------

Run Bandcrash with::

   bandcrash input_dir/album.json output_dir

and it will automatically encode the album based on its settings and, if so configured, upload to itch.io.

If you want to override the encoder arguments, remember to put them in quotes; for example::

   bandcrash --mp3-encoder-args="-q:3 -joint_stereo:0"

Uploading to itch
-----------------

If you plan on uploading your albums to `itch.io <https://itch.io>`_, it is highly recommended that you install `butler <https://itch.io/docs/butler/>`_ (ideally from `the itch app <https://itch.io/app>`_). After doing this, add ``butler`` to your path (either by adding its directory to your ``PATH`` environment variable or by putting a symlink to the binary somewhere useful). You can also specify the Butler path at runtime using ``--butler-path``.

.. TIP::
   If you're using the Itch app, you can find the binary by going to Butler in your library, clicking the gear icon, then selecting "Manage" and looking at the ``Show in Finder/Explorer`` button.

After that, run ``butler login`` to connect Butler to itch.
