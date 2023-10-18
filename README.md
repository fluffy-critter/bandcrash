# Bandcrash (formerly pyBlamscamp)

Bandcrash is a standalone program that automatically encodes an album of songs into a bunch of different formats for distribution on various platforms, such as [itch.io](https://itch.io/), or for hosting on your own website. The embedded player is originally based on the one from [blamscamp](https://github.com/blackle/blamscamp) by [@blackle](https://github.com/blackle), although it has been pretty thoroughly modified at this point.

[See it in action](https://fluffy.itch.io/novembeat-2021)!

## Features

* Output as mp3, ogg, FLAC, and web preview (HTML5+mp3 at a lower bitrate)
* Optionally upload everything to your page on itch using [butler](https://itch.io/docs/butler/)
* High-quality encoding and metadata, with support for cover songs, per-track artwork, embedded lyrics, and more
* Web player also supports per-track artwork

## Usage

To use it, you'll need to install LAME, oggenc, and FLAC; on macOS you can install these via [homebrew](https://brew.sh/), on Linux you can use your system's package manager, and on Windows you're on your own.

### Command-line

For the command-line version, the suggested approach is to install [Python](https://python.org), after which you can install Bandcrash with:

```
pip install bandcrash
```

`bandcrash --help` will provide a lot more detailed information. For the most part you should be able to just do:

```
bandcrash input_dir output_dir
```

and the rest will Just Work™.

### GUI

If you want to build the GUI locally, install [Python](https://python.org/), [poetry](https://python-poetry.org/), and `make` (from your favorite F/OSS package repository). After that you can run:

```
make app
```

after which the application will be built in the `dist/` directory.

### Use as a library

Bandcrash can also be used as a Python library in order to embed it into a web service or the like. Currently this isn't documented or particularly elegant, but the basic idea is:

1. Load your album metadata into a Python `dict` structure (e.g. by doing `json.loads` on a JSON file or the like)
2. Create a `concurrent.futures.ThreadPoolExecutor` and a `collections.defaultdict(list)` to store its futures
3. Use `bandcrash.args.parse_args([])` to generate an options set, and then populate it accordingly
4. Call `bandcrash.process(options, album_data, threadpool, futures_dict`
5. Wait for all of the futures in the `futures_dict` to complete

The `futures_dict` is a mapping from process step &rarr; list of futures, and is fully populated after `process()` returns. You can use something like `list(itertools.chain(*futures_dict.values()))` to collapse it into a single list of futures if you don't care about tracking individual stages in the pipeline.

It is also fine (and, in fact, preferable) to share a `ThreadPoolExecutor` across multiple concurrent batches.

Consult `bandcrash/cli.py` and `bandcrash/gui.py` for more thorough usage examples.

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
bandcrash --init input_dir output_dir
```

which will try to guess the track order and titles from the audio files in `input_dir`.

Basically, the top-level album contains the following properties (all optional):

* `artist`: The artist for the album as a whole
* `title`: The album's title
* `year`: The release year
* `composer`: The album's composer
* `artwork`: an image file to use for the album's cover art (relative or absolute paths okay)
* `bg_color`, `fg_color`, `highlight_color`: The color theme for the player
* `genre`: The default genre for all tracks
* `tracks`: an array of track descriptions, in album order
* `do_mp3`: Whether to build the album in MP3 format
* `do_ogg`: Whether to build the album in Ogg Vorbis format
* `do_flac`: Whether to build the album in FLAC format
* `do_preview`: Whether to build the web preview
* `do_zip`: Whether to build a zip file of each output format
* `do_butler`: Whether to upload the builds to itch.io
* `butler_target`: The itch.io Butler target (e.g. `"fluffy/songs-of-substance"`)
* `butler_prefix`: Any prefix to add to the Butler channel name (e.g. `"bonus-"` will upload it as `"fluffy/songs-of-substance:bonus-mp3"`)

And each track contains (all optional except `filename`):

* `filename`: The audio file to encode into the final output track (ideally wav or aif)
* `group`: The title of the track's grouping (i.e. a work with multiple movements)
* `title`: The title of the track
* `artist`: The performing artist of this track
* `composer`: The composer of this track
* `cover_of`: The original artist that this track is a cover of, if any
* `genre`: The genre of this track
* `artwork`: Track-specific cover art
* `lyrics`: An array of strings, one line of lyrics per string; alternately, the name of a text file to read the lyrics from (relative or absolute paths okay)
* `hidden`: A boolean for whether to hide this track from the web player entirely (e.g. a purchase bonus); defaults to `false`
* `preview`: A boolen for whether to generate a preview for the web player; defaults to `true`
* `about`: Detailed commentary about the track

See the [sample album JSON file](https://github.com/fluffy-critter/Bandcrash/blob/main/tests/album/album.json) for a rough example.

## Publishing to Itch

Here's the process for publishing an album to [itch.io](https://itch.io):

1. Install [butler](https://itch.io/docs/butler/) and log in with `butler login`
1. [Create a new project](https://itch.io/game/new)
2. Set it as a "soundtrack," with the kind of project being "HTML"
3. Set your pricing, add preview artwork, etc., and save. Don't do any uploading from this interface.
4. Run `bandcrash` with a `-b user/project` flag; for example:

    ```sh
    bandcrash novembeat-2021/wav novembeat-2021/out -b fluffy/novembeat-2021
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
<iframe src="/path/to/album/" width=640 height=360></iframe>
```

## Contributing

Pull requests are welcome! But please note the following:

The generated web player must not receive any added dependencies. The generator must stay as a single, self-contained file that is as small as reasonably possible. The point is for the generated file to be lightweight. Stick to Vanilla JS.

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
