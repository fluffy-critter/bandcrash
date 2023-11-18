itch.io setup
=============

If you want to publish an album to `itch.io <https://itch.io/>`_, you need to create a new project from `your dashboard <https://itch.io/dahsboard>`_. The steps are fairly straightforward:

#. Create a `new project <https://itch.io/game/new>`_

#. Set the project to be a "soundtrack," with the kind of project being "HTML," and set your pricing and such how you want it

   .. image:: project-settings.png
      :scale: 33 %
      :alt: A new project on itch.io

#. Configure your Bandcrash album with your Butler target, which is in the form ``username/project-name``. For example, if your album URL is ``https://fluffy.itch.io/my-album``, the target will be ``fluffy/my-album``.

#. Save the project

#. Have Bandcrash do an encode and upload (or manually upload the .zip files if you haven't setup Butler)

#. Wait a few minutes, then reload the project page. You should now see some existing uploads, named (for example) ``my-album-html.zip``, ``my-album-mp3.zip``, and so on.

#. Set the ``html`` version with "This file will be played in the browser." Set the other versions to be of type "Soundtrack."

#. Set your embed options:

   * Mobile friendly

   * Automatically start on page load

   * Disable scrollbars

   .. image:: embed-settings.png
      :scale: 33 %
      :alt: Recommended embed settings

Set up the rest of your project as you'd like it to be, and also verify that the project is still set to "soundtrack" and "HTML," as sometimes this gets reset on the first upload.

Now you should be able to preview your album and make sure everything's working, and once it's how you like it, set the status to "Public" and wait for the praise and fat stacks to roll in!
