# pyBlamscamp

![CC0 license badge](https://licensebuttons.net/p/zero/1.0/88x31.png)

This is based on [blamscamp](https://github.com/blackle/blamscamp), with an intention towards being a standalone program you run on your computer to automatically encode an album of songs into a bunch of different formats for distribution on various platforms, such as [itch.io](https://itch.io/), or for hosting on your own website.

To use it, you'll need to install LAME, oggenc, and FLAC; on macOS you can install these via [homebrew](https://brew.sh/), on Linux you can use your system's package manager, and on Windows you're on your own.

You'll also need to install [Python](https://python.org), after which you can install pyBlamscamp with:

```
pip install blamscamp
```

`blamscamp --help` should guide you the rest of the way there.

## Building an album

Make a directory with all of your source audio files and artwork and so on. Create a JSON file named `album.json` (which can be overridden) that looks something like this:

```json
{
    "artist": "The artist of the album",
    "title": "The title of the album",
    "bg_color": "black",
    "fg_color": "white",
    "highlight_color": "#cc00ff",
    "artwork": "album_cover.jpg",
    "tracks": [{
        "filename": "the first track.wav",
        "title": "The First Track",
        "artwork": "track1_cover.jpg",
        "lyrics": ["This is the first line",
            "This is the second line",
            "This is the third line",
            "",
            "This is the second verse",
            "This song just keeps getting worse"],
        "hidden": false,
        "preview": true
    }]
}
```

Basically, the top-level album contains the following properties (all optional):

* `artist`: The artist for the album as a whole
* `title`: The album's title
* `bg_color`, `fg_color`, `highlight_color`: The color theme for the player
* `artwork`: an image file to use for the album's cover art
* `tracks`: an array of track descriptions, in album order

Each track element contains:

* `title`: The title of the track
* `artist`: The artist of this track, if different from the album as a whole
* `artwork`: Track-specific cover art (e.g. for a single)
* `lyrics`: An array of strings, one line of lyrics per string; alternately, this can be the name of a text file to read the lyrics from
* `hidden`: A boolean for whether to hide this track from the web player entirely (e.g. a purchase bonus); defaults to `false`
* `preview`: A boolen for whether to generate a preview for the web player; defaults to `true`

See the [sample album JSON file](https://github.com/fluffy-critter/pyBlamscamp/blob/main/test_album/album.json) for a rough example.

## Contributing

Pull requests are welcome! But please note the following:

The generated blamscamp player must not receive any added dependencies. The generator must stay as a single, self-contained file that is as small as reasonably possible. The point is for the generated file to be lightweight. Stick to Vanilla JS.

## License

This software is public domain.
