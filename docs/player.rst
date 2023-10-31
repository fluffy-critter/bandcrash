Using the Web Player
====================

The web player is provided as a folder (and possibly zip file) which contains the preview-quality audio tracks and an HTML interface. You can upload the ``preview/`` directory somewhere and then point an ``<iframe>`` at it. This way you can share your album preview on a website that you manage with whatever tools you prefer.

Hosting options
---------------

itch.io
^^^^^^^

If you're using the :doc:`itch.io uploader <itch>`, they provide a `player embed <https://itch.io/updates/introducing-game-embeds>`_. For example, this code:

.. code-block:: html

    <iframe frameborder="0" src="https://itch.io/embed-upload/8976401?color=333333" allowfullscreen="" width="100%" height="620"><a href="https://fluffy.itch.io/novembeat-2017">Play Novembeat 2017 on itch.io</a></iframe>

renders as:

.. raw:: html

    <iframe frameborder="0" src="https://itch.io/embed-upload/8976401?color=333333" allowfullscreen="" width="100%" height="620"><a href="https://fluffy.itch.io/novembeat-2017">Play Novembeat 2017 on itch.io</a></iframe>

Due to Bandcrash's existing integration with the itch.io uploader (as well as itch.io's pre-existing payments platform), this is likely the easiest approach for most users.

Static file hosting
^^^^^^^^^^^^^^^^^^^

If you have your own HTTP server space, you can upload the directory to your website and then point the ``<iframe>`` to it. For example, if you upload your preview directory to ``https://example.com/my-album/``, then you can embed it as:

.. code-block:: html

   <iframe src="https://example.com/my-album/" width=640 height=480 seamless>
   <a href="my-album/">Listen to my album</a>
   </iframe>

For example:

.. code-block:: html

   <iframe frameborder="0" src="https://cdn.sockpuppet.us/novembeat-2021/" width="100%" height="480" seamless>
   <a href="https://cdn.sockpuppet.us/novembeat-2021/">Lo-Fi Beats to Grind Coffee To</a>
   </iframe>

will look like:

.. raw:: html

   <iframe frameborder="0" src="https://cdn.sockpuppet.us/novembeat-2021/" width="100%" height="480" seamless>
   <a href="https://cdn.sockpuppet.us/novembeat-2021/">Lo-Fi Beats to Grind Coffee To</a>
   </iframe>

Embedding ``iframe``
--------------------

If your website operator allows you to write arbitrary HTML, then all you have to do to embed the player is to insert hosted ``<iframe>`` tag as raw HTML.

However, this isn't totally obvious on every website platform! So here's some quick tips for various popular platforms.

* Squarespace: `Embed blocks <https://support.squarespace.com/hc/en-us/articles/206543617-Embed-Blocks>`_
* Wix.com: `Embedding a site or a widget <https://support.wix.com/en/article/wix-editor-embedding-a-site-or-a-widget>`_
* Wordpress.com: If you have a `plugin-enabled site <https://wordpress.com/support/wordpress-editor/blocks/custom-html-block/#supported-html-tags>`_ you can type ``/html`` to get a raw HTML block

If you know of others, please `let me know about them <https://github.com/fluffy-critter/bandcrash/issues/new>`_ so that I can share it here!