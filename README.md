# pyBlamscamp

![CC0 license badge](https://licensebuttons.net/p/zero/1.0/88x31.png)

This is based on [blamscamp](https://github.com/blackle/blamscamp), with an intention towards being a standalone program you run on your computer to automatically encode an album of songs into a bunch of different formats for distribution on various platforms, such as [itch.io](https://itch.io/), or for hosting on your own website.

To use it, you'll need to install LAME, oggenc, and FLAC; on macOS you can install these via [homebrew](https://brew.sh/), on Linux you can use your system's package manager, and on Windows you're on your own.

You'll also need to install [Python](https://python.org), after which you can install pyBlamscamp with:

```
pip install pyBlamscamp
```

`blamscamp --help` should guide you the rest of the way there.

See the [sample album JSON file](test_album/album.json) for a rough example of how to format the album spec file. Supported attributes are (currently):

* `artist`: The name of the artist (can be overriddedn per-track)
* `title`: The title of the album or track
* `year`: The release year
* `lyrics`: The lyrics of the track, in the form of an array of lines
* `hidden`: Whether a track should be hidden from the web player entirely (default: `false`)
* `preview`: Whether a track should be played in the player (default: `true`)

## Contributing

Pull requests are welcome! But please note the following:

The generated blamscamp player must not receive any added dependencies. The generator must stay as a single, self-contained file that is as small as reasonably possible. The point is for the generated file to be lightweight. Stick to Vanilla JS.

## License

This software is public domain.
