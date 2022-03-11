# pyBlamscamp

![CC0 license badge](https://licensebuttons.net/p/zero/1.0/88x31.png)

This is based on [blamscamp](https://github.com/blackle/blamscamp), with an intention towards being a standalone program you run on your computer to automatically encode an album of songs into a bunch of different formats for distribution on various platforms, such as [itch.io](https://itch.io/), or for hosting on your own website.

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

See the [sample album JSON file](https://github.com/fluffy-critter/pyBlamscamp/blob/main/test_album/album.json) for a rough example.

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

## Contributing

Pull requests are welcome! But please note the following:

The generated blamscamp player must not receive any added dependencies. The generator must stay as a single, self-contained file that is as small as reasonably possible. The point is for the generated file to be lightweight. Stick to Vanilla JS.

## License

This software is public domain.
