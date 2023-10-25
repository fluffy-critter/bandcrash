# Bandcrash (formerly pyBlamscamp)

Bandcrash is a standalone program that automatically encodes an album of songs into a bunch of different formats for distribution on various platforms, such as [itch.io](https://itch.io/), or for hosting on your own website. The embedded player is originally based on the one from [blamscamp](https://github.com/blackle/blamscamp) by [@blackle](https://github.com/blackle), although it has been pretty thoroughly modified at this point.

[See it in action](https://fluffy.itch.io/novembeat-2021)!

[![Documentation Status](https://readthedocs.org/projects/bandcrash/badge/?version=latest)](https://bandcrash.readthedocs.io/en/latest/?badge=latest)

## Features

* Output as mp3, ogg, FLAC, and web preview (HTML5+mp3 at a lower bitrate)
* Optionally upload everything to your page on itch using [butler](https://itch.io/docs/butler/)
* High-quality encoding and metadata, with support for cover songs, per-track artwork, embedded lyrics, and more
* Web player also supports per-track artwork

## Usage

Please see [the online documentation](https://bandcrash.readthedocs.io) for installation and usage instructions.
## Contributing

Pull requests are welcome! But please note the following:

The generated web player must not receive any added dependencies. The generator must stay as a single, self-contained file that is as small as reasonably possible. The point is for the generated file to be lightweight. Stick to Vanilla JS.

### Development environment notes

If you are developing under Windows, you will probably need to use a POSIX environment under Windows (such as [msys](https://www.msys2.org) or [Git Bash](https://git-scm.com)) rather than WSL.

If you are developing under macOS, please use a `universal2` build of Python (such as the ones installable from [python.org](https://python.org)) and you need to ensure that you've created your environment against that (e.g. `poetry env use /usr/local/bin/python3.11`).

### Roadmap

See the [github issues](https://github.com/fluffy-critter/bandcrash/issues) for details, but roughly:

* Local GUI and/or web UI to make setting up the `album.json` easier (and easier installation, especially on Windows!)
* Various player improvements
* Easy embedding into websites (opengraph et al)

## FAQ

### How is this different from blamscamp, scritch, etc.?

[Blamscamp](https://suricrasia.online/blamscamp/) and [scritch](https://torcado.itch.io/scritch-editor) are both great programs for publishing album previews on itch.io and other websites! However, their functionality is only to bundle already-encoded audio files into a web-based player. They don't do the difficult work of encoding and tagging your files, which can be an extremely tedious and error-prone process. Bandcrash's intention is to make the process of encoding and uploading your albums easier to as many stores as possible.

### Why was it renamed?

Back when this project started, it was named pyBlamscamp as the intention was to be basically a Python version of the blamscamp GUI which would also handle encoding steps for you, but it very quickly drifted away from that and became something else. Unfortunately, the similarity of the names was incredibly confusing.

Currently the only connection between Bandcrash and blamscamp is that Bandcrash uses a highly-modified version of blamscamp's web player. They serve different goals.

### Why run it locally instead of as a web app?

You already have your large .wav files on your local hard drive. Your local drive is also a good place to keep your previous encoding results. Your local computer also has a lot more space available than a typical cloud server, doesn't have to juggle cloud storage credentials, doesn't have to worry about the security of the server running the encoder app, the cost of running servers or paying for cloud storage, and so on.

Basically, it's easier for everyone.

Sometimes local apps are just Better™.

## Credits

* Main code: [@fluffy-critter](https://github.com/fluffy-critter)
* Original player code and this project's name: [@blackle](https://github.com/blackle)
