Using the Web Player
====================

The web player is provided as a folder (and possibly zip file) which contains the preview-quality audio tracks and an HTML interface. You can upload the ``preview/`` directory somewhere and then point an ``<iframe>`` at it. Most website creators will allow you to embed an iframe.

itch.io
-------

If you're using the :doc:`itch.io uploader <itch>`, they also provide a `player embed <https://itch.io/updates/introducing-game-embeds>`_. For example, this code:

.. code-block:: html

    <iframe frameborder="0" src="https://itch.io/embed-upload/8976401?color=333333" allowfullscreen="" width="720" height="620"><a href="https://fluffy.itch.io/novembeat-2017">Play Novembeat 2017 on itch.io</a></iframe>

renders as:

.. raw:: html

    <iframe frameborder="0" src="https://itch.io/embed-upload/8976401?color=333333" allowfullscreen="" width="720" height="620"><a href="https://fluffy.itch.io/novembeat-2017">Play Novembeat 2017 on itch.io</a></iframe>

Self-hosting
------------

If you have your own HTTP server space, you can upload the directory to your website and then embed it using an ``<iframe>`` tag. For example, if you upload your preview directory as ``my-album/``, then you can embed it as:

.. code-block:: html

   <iframe src="my-album/" width=640 height=480 seamless>
   <a href="my-album/">Listen to my album</a>
   </iframe>

If you know the URL, you can also embed it from anywhere else; for example:

.. code-block:: html

   <iframe frameborder="0" src="https://cdn.sockpuppet.us/novembeat-2021/" width=640 height=480 seamless>
   <a href="https://cdn.sockpuppet.us/novembeat-2021/">Lo-Fi Beats to Grind Coffee To</a>
   </iframe>

will look like:

.. raw:: html

   <iframe frameborder="0" src="https://cdn.sockpuppet.us/novembeat-2021/" width=640 height=480 seamless>
   <a href="https://cdn.sockpuppet.us/novembeat-2021/">Lo-Fi Beats to Grind Coffee To</a>
   </iframe>

