# Bandcrash

Bandcrash is a standalone program that automatically encodes an album of songs into a bunch of different formats for distribution on various platforms, such as [itch.io](https://itch.io/), or for hosting on your own website.

[See it in action](https://fluffy.itch.io/transitions)!

[![Documentation Status](https://readthedocs.org/projects/bandcrash/badge/?version=latest)](https://bandcrash.readthedocs.io/en/latest/?badge=latest)

## Features

* Output as mp3, ogg, FLAC, and web preview (HTML5+mp3 at a lower bitrate)
* Optionally upload everything to your page on itch using [butler](https://itch.io/docs/butler/)
* High-quality encoding and metadata, with support for cover songs, per-track artwork, embedded lyrics, and more
* Web player also supports per-track artwork

## Installation

For the CLI version, the best approach is to install it with [pipx](https://pipx.pypa.io/):

    pipx install bandcrash

On Windows, Apple Silicon-based Macs, and Intel machines running Ubuntu-based Linux, the best source for the GUI is [the itch.io store](https://fluffy.itch.io/bandcrash).

If you are fine with launching the GUI from the terminal, the easiest option is to install it with:

    pipx install 'bandcrash[gui]'

and then launch it with `bandcrash-gui`.

Otherwise, you'll probably need to build it from source.

### Building from source

You'll need to install a supported version of [Python](https://python.org/) (3.13 recommended) and [poetry](https://python-poetry.org) (which may also require installing [pipx](https://pipx.pypa.io/)).

To build bandcrash, you should only need to run `make`, after which you will be able to run bandcrash from the project directory:

    poetry run bandcrash       # CLI version
    poetry run bandcrash-gui   # GUI version

To build a standalone GUI application, you can run `make app` and the application will (hopefully) end up in the `dist` subdirectory.

## Usage

See [the online documentation](https://bandcrash.readthedocs.io/) for detailed usage instructions.

## Contributing

### Development environment notes

If you are developing under Windows, you will probably need to use a POSIX environment under Windows (such as [msys](https://www.msys2.org) or [Git Bash](https://git-scm.com)) rather than WSL.

### Roadmap

See the [github issues](https://github.com/fluffy-critter/bandcrash/issues) for details, but roughly:

* Local GUI and/or web UI to make setting up the `album.json` easier (and easier installation, especially on Windows!)
* Various player improvements
* Easy embedding into websites (opengraph et al)

## FAQ

### How is this different from blamscamp, scritch, etc.?

[Blamscamp](https://suricrasia.online/blamscamp/) and [scritch](https://torcado.itch.io/scritch-editor) are both great programs for publishing previews of already-encoded on itch.io and other websites! However, their functionality is only to bundle prepared audio files into a web-based player, and they don't presently handle encoding or tagging, two things that are historically tedious and difficult to do well.

Bandcrash is a full end-to-end system for preparing an album for both sale and preview online in a variety of formats.

### What about Faircamp?

[Faircamp](https://simonrepp.com/faircamp/) does handle the end-to-end encoding and processing and builds a quite beautiful static website! If you just want to build a site to host your music and handle your own payments, it's totally usable for that.

Bandcrash is for people who want to be able to host their downloads and web-based preview on existing marketplaces such as [itch.io](https://itch.io/), [gumroad](https://gumroad.com/), [ko-fi](https://ko-fi.com/), etc., or who want to be able to embed their preview on their website under their own terms, rather than being beholden to a specific static site template.

### What player does Bandcrash use?

At present, it defaults to using [Camptown](https://github.com/fluffy-critter/camptown), a player built specifically for Bandcrash. However, I do plan on eventually making it possible to choose from a variety of player engines, including Blamscamp and Scritch.

### What happened to pyBlamscamp?

Back when this project started, it was named pyBlamscamp as the intention was to be basically a Python version of the blamscamp GUI which would also handle encoding steps for you, but it very quickly drifted away from that and became something else.

For a while, Bandcrash used a fork of the blamscamp player, but at this point that has been entirely removed.

### Why make a local GUI instead instead of a web app?

You already have your large .wav files on your local hard drive. Your local drive is also a good place to keep your previous encoding results. Your local computer also has a lot more space available than a typical cloud server, doesn't have to juggle cloud storage credentials, doesn't have to worry about the security of the server running the encoder app, the cost of running servers or paying for cloud storage, and so on.

Basically, it's easier for everyone.

Sometimes local apps are just Better™.

That said, Bandcrash is also embeddable as a library, so someone could conceivably build a web-based system that uses it for encoding and tagging files.

## Credits

* Main code: [@fluffy-critter](https://github.com/fluffy-critter)
* Original player code and this project's name: [@blackle](https://github.com/blackle)
