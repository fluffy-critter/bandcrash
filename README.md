# Bandcrash

Bandcrash is a standalone program that automatically encodes an album of songs into a bunch of different formats for distribution on various platforms, such as [itch.io](https://itch.io/), or for hosting on your own website.

[See it in action](https://fluffy.itch.io/transitions)!

[![Documentation Status](https://readthedocs.org/projects/bandcrash/badge/?version=latest)](https://bandcrash.readthedocs.io/en/latest/?badge=latest)

## Features

* Output as mp3, ogg, FLAC, and web preview (HTML5+mp3 at a lower bitrate)
* Optionally upload everything to your page on itch using [butler](https://itch.io/docs/butler/)
* High-quality encoding and metadata, with support for cover songs, per-track artwork, embedded lyrics, and more
* Web player also supports per-track artwork
* Build master files (bin/cue) for disc-at-once CD replication

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

If you are developing under Windows, you will probably need to use a POSIX environment under Windows (such as [msys](https://www.msys2.org) or [Git Bash](https://git-scm.com)) rather than WSL, as WSL can only produce Linux binaries.

## FAQ

### How is this different from blamscamp, scritch, etc.?

[Blamscamp](https://suricrasia.online/blamscamp/) and [scritch](https://torcado.itch.io/scritch-editor) are both great programs for publishing previews of already-encoded albums on itch.io and other websites! However, their functionality is only to bundle prepared audio files into a web-based player, and they don't presently handle encoding or tagging, two things that are historically tedious and difficult to do well.

Additionally, since they are ephemeral web-based applications, they do not lend themselves well for things where you might want to make tweaks and adjustments down the road, as you have to restart the player creation process from scratch each time.

Bandcrash is a full end-to-end system for preparing an album for both sale and preview online in a variety of formats, and it also will automatically upload and update complete albums for both preview and download to itch.io.

Additionally, it can be used to master CDs for disc replication with services such as [Kunaki](https://kunaki.com/) or anything else that accepts disc-at-once `.bin`/`.cue` files.

### What about Faircamp?

[Faircamp](https://faircamp.org/) does handle the end-to-end encoding and processing and builds a quite beautiful static website! If you just want to build a site to host your music and handle your own payments, it's totally usable for that.

Bandcrash is for people who want to be able to host their downloads and web-based preview on existing marketplaces such as [itch.io](https://itch.io/) and [ko-fi](https://ko-fi.com/), or who want to be able to embed their preview on their website under their own terms, rather than using a predetermined static site setup.

Additionally, Bandcrash works on only a single album at a time, rather than having to maintain and build an entire website all at once, so you don't need all of your music content to live in one place.

Neither approach is superior to the other, and both have pluses and minuses, but it's a difference in opinion. Both of them work well, they're just different designs with different goals.

### What player does Bandcrash use?

At present, it defaults to using [Camptown](https://github.com/fluffy-critter/camptown), a player built specifically for Bandcrash. However, I do plan on eventually making it possible to choose from a variety of player engines, including Blamscamp and Scritch.

### What happened to pyBlamscamp?

Back when this project started, it was named pyBlamscamp as the intention was to be basically a Python version of the blamscamp GUI which would also handle encoding steps for you, but it very quickly drifted away from that and became something else.

For a while, Bandcrash used a fork of the blamscamp player, but at this point that has been entirely removed.

### Why make a local GUI instead instead of a web app?

You already have your large .wav files on your local hard drive. Your local drive is also a good place to keep your previous encoding results. Your local computer also has a lot more space available than a typical cloud server, doesn't have to juggle cloud storage credentials, doesn't have to worry about the security of the server running the encoder app, the cost of running servers or paying for cloud storage, and so on.

Basically, it's easier for everyone.

Sometimes local apps are just Better™.

That said, Bandcrash is also embeddable as a library, so someone could conceivably build a web-based system that uses it for encoding and tagging files. If someone builds such a thing, please make it so that you can import and export the raw album data files!

## Credits

* Main code: [@fluffy-critter](https://github.com/fluffy-critter)
* Original player code and this project's name: [@blackle](https://github.com/blackle)
