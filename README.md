# pyBlamscamp

![CC0 license badge](https://licensebuttons.net/p/zero/1.0/88x31.png)

pyBlamscamp is a standalone program that automatically encodes an album of songs into a bunch of different formats for distribution on various platforms, such as [itch.io](https://itch.io/), or for hosting on your own website. The embedded player is originally based on the one from [Blamscamp](https://github.com/blackle/blamscamp), although it has been pretty thoroughly modified at this point.

[See it in action](https://fluffy.itch.io/novembeat-2021)!

## Features

* Output as mp3, ogg, FLAC, and web preview (HTML5+mp3 at a lower bitrate)
* Optionally upload everything to your page on itch using [butler](https://itch.io/docs/butler/)
* High-quality encoding and metadata, with support for cover songs, per-track artwork, embedded lyrics, and more
* Web player also supports per-track artwork

## Usage

To use it, you'll need to install LAME, oggenc, and FLAC; on macOS you can install these via [homebrew](https://brew.sh/), on Linux you can use your system's package manager, and on Windows you're on your own.

You'll also need to install [Python](https://python.org), after which you can install pyBlamscamp with:

```
pip install blamscamp
```

`blamscamp --help` will provide a lot more detailed information. For the most part you should be able to just do:

```
blamscamp input_dir output_dir
```

and the rest will Just Work™.

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

You can also automatically generate a stub `album.json` file with:

```
blamscamp --init input_dir output_dir
```

which will try to guess the track order and titles from the audio files in `input_dir`.

Basically, the top-level album contains the following properties (all optional):

* `artist`: The artist for the album as a whole
* `title`: The album's title
* `year`: The release year
* `artwork`: an image file to use for the album's cover art (relative or absolute paths okay)
* `bg_color`, `fg_color`, `highlight_color`: The color theme for the player
* `genre`: The default genre for all tracks
* `tracks`: an array of track descriptions, in album order

And each track contains (all optional except `filename`):

* `filename`: The audio file to encode into the final output track (ideally wav or aif)
* `title`: The title of the track
* `artist`: The performing artist of this track
* `cover_of`: The original artist that this track is a cover of, if any
* `genre`: The genre of this track
* `artwork`: Track-specific cover art
* `lyrics`: An array of strings, one line of lyrics per string; alternately, the name of a text file to read the lyrics from (relative or absolute paths okay)
* `hidden`: A boolean for whether to hide this track from the web player entirely (e.g. a purchase bonus); defaults to `false`
* `preview`: A boolen for whether to generate a preview for the web player; defaults to `true`
* `about`: Detailed commentary about the track

See the [sample album JSON file](https://github.com/fluffy-critter/pyBlamscamp/blob/main/tests/album/album.json) for a rough example.

## Publishing to Itch

Here's the process for publishing an album to [itch.io](https://itch.io):

1. Install [butler](https://itch.io/docs/butler/) and log in with `butler login`
1. [Create a new project](https://itch.io/game/new)
2. Set it as a "soundtrack," with the kind of project being "HTML"
3. Set your pricing, add preview artwork, etc., and save. Don't do any uploading from this interface.
4. Run `blamscamp` with a `-b user/project` flag; for example:

    ```sh
    blamscamp novembeat-2021/wav novembeat-2021/out -b fluffy/novembeat-2021
    ```
5. Wait a moment for itch to finish processing; you can use `butler status user/project` (e.g. `butler status fluffy/novembeat-2021`)
6. Reload your project edit page; you should now have a few targets, such as `preview`, `mp3`, etc.
7. Set the `preview` target to "This file will be played in the browser". Set all the other targets to "soundtrack" and, optionally, change the display name.
8. View the project page, and when you're ready to publish, publish!

### Recommended "embed options"

* Set it to "embed in page" with "manually set size"
* Enable "mobile friendly" (with orientation "default") and "automatically start on page load"
* Disable "fullscreen button" and "enable scrollbars"

## Publishing to other sites

If you have a website of your own, upload the `preview` directory to your site somewhere, and then embed it using an iframe, e.g.

```html
<iframe src="/path/to/album" width=640 height=360></iframe>
```

You can also embed the itch version on another website; go to the itch page, right-click the frame, and then your browser should provide some option for "show only this frame" or "open frame in tab" or the like. This should give you a URL that you can embed on another site, such as `https://v6p9d9t4.ssl.hwcdn.net/html/5375791-530391/index.html`, which you can embed with:

```html
<iframe src="https://v6p9d9t4.ssl.hwcdn.net/html/5375791-530391/index.html" width=640 height=360></iframe>
```

although note that this URL may disappear or be otherwise unsupported.

## Contributing

Pull requests are welcome! But please note the following:

The generated blamscamp player must not receive any added dependencies. The generator must stay as a single, self-contained file that is as small as reasonably possible. The point is for the generated file to be lightweight. Stick to Vanilla JS.

### Roadmap

See the [github issues](https://github.com/fluffy-critter/pyBlamscamp/issues) for details, but roughly:

* Local GUI and/or web UI to make setting up the `album.json` easier (and easier installation, especially on Windows!)
* Improved player
* Easy embedding into  websites

## License

This software is public domain.
