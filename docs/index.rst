Bandcrash
=========

Bandcrash is a system for automatically encoding and tagging music albums for download and/or purchase without being stuck on any particular hosting provider or storefront. It generates high-quality MP3, Ogg Vorbis, and FLAC renditions, and an easily-embedded web preview player that can be uploaded to your static hosting site or CDN of choice. Additionally, it can optionally generate ``.bin`` and ``.cue`` files for CD replication with services such as `Kunaki <https://kunaki.com/>`__.

It is written in Python, and provides a CLI, an optional Qt-based GUI frontend, and a library which can potentially be embedded into other applications, including web services.

Usage
-----

Your usage depends on whether you're using the :doc:`graphical interface <gui>` or :doc:`command-line interface <cli>`.

You might also want to learn about :doc:`itch album setup <itch>`, and if you're building a web service, look at :doc:`integrating the library <library>`.

If you want to embed the player on your own website, :doc:`there's a doc for that too <player>`.

.. toctree::
    :hidden:

    gui
    cli
    itch
    library
    player
    metadata
