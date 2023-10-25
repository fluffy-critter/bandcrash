Using the Web Player
====================

The web player is provided as a folder (and possibly zip file) which contains the preview-quality audio tracks and an HTML interface.

If you have your own web space, you can upload the directory to your website and then embed it using an ``<iframe>`` tag. For example, if you upload your ``preview/`` directory as ``my-album/``, then you can embed it as:

.. code-block:: html

   <iframe src="my-album/" width=640 height=480 seamless>
   <a href="my-album/">Listen to my album</a>
   </iframe>

If you know the URL, you can also embed it from anywhere else; for example:

.. code-block:: html

   <iframe src="https://cdn.sockpuppet.us/novembeat-2021/" width=640 height=480 seamless>
   <a href="https://cdn.sockpuppet.us/novembeat-2021/">Lo-Fi Beats to Grind Coffee To</a>
   </iframe>

will look like:

.. raw:: html

   <iframe src="https://cdn.sockpuppet.us/novembeat-2021/" width=640 height=480 seamless>
   <a href="https://cdn.sockpuppet.us/novembeat-2021/">Lo-Fi Beats to Grind Coffee To</a>
   </iframe>

Player configuration
--------------------

TODO
