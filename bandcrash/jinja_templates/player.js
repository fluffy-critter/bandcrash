
window.addEventListener("load", () => {
    function set_button_state(button, playing) {
        button.classList.add(playing ? "playing" : "paused");
        button.classList.remove(playing ? "paused" : "playing");
    }

    const audio = new Audio();
    const slider = document.querySelector(".slider");
    const play_buttons = document.querySelectorAll(".song_list .play");
    const big_button = document.querySelector(".player .play");
    const player_title = document.querySelector(".player p");
    let last_played = -1;
    let slider_locked = false;

    const cover_art = document.querySelector("#coverart");
    var album_art;
    if (cover_art) {
        album_art = { 'src': cover_art.src, 'srcset': cover_art.srcset };
    } else {
        album_art = { };
    }

    // terrible hack
    const tracklist = document.querySelector('.tracklist');
    const footer = document.querySelector('.madewith');
    function onResize() {
        tracklist.style.height = (footer.offsetTop - tracklist.offsetTop) + "px";
    }
    onResize();
    window.addEventListener("resize", onResize);

    function reset_player() {
        last_played = -1;
        player_title.textContent = play_buttons[0].parentElement.querySelector(".title").textContent;
        audio.src = play_buttons[0].dataset.song;
        cover_art.src = album_art.src;
        cover_art.srcset = album_art.srcset;
        window.setTimeout(() => slider.value = 0, 0);
    }

    reset_player();

    slider.oninput = (event) => {
        slider_locked = true;
        audio.pause();
    };
    slider.onchange = (event) => {
        let time = slider.value / 1000 * audio.duration;
        audio.play();
        audio.currentTime = time;
        slider_locked = false;
    };

    audio.onplay = (event) => {
        set_button_state(big_button, true);
        if (last_played != -1) {
            set_button_state(play_buttons[last_played], true);
        }

        var track_art = play_buttons[last_played].getElementsByClassName('trackart')[0] || album_art;
        if (track_art) {
            cover_art.src = track_art.src;
            cover_art.srcset = track_art.srcset;
        }
    };
    audio.onpause = (event) => {
        set_button_state(big_button, false);
        if (last_played != -1) {
            set_button_state(play_buttons[last_played], false);
        }
    };
    audio.onended = (event) => {
        if (last_played != -1 && last_played + 1 < play_buttons.length) {
            play_buttons[last_played + 1].onclick();
        } else {
            reset_player();
        }
    };
    audio.ontimeupdate = (event) => {
        if (slider_locked == false) {
            slider.value = (audio.currentTime / audio.duration) * 1000;
        }
    };

    big_button.onclick = (event) => {
        if (last_played == -1) {
            play_buttons[0].onclick();
        } else if (audio.paused || audio.ended) {
            audio.play();
        } else {
            audio.pause();
        }
    };

    play_buttons.forEach((e, idx) => {
        e.onclick = function() {
            if (last_played == idx) {
                if (audio.paused || audio.ended) {
                    audio.play();
                } else {
                    audio.pause();
                }
                return;
            }
            audio.pause();
            last_played = idx;
            audio.src = e.dataset.song;
            player_title.textContent = e.parentElement.querySelector(".title").textContent;
            audio.onloadeddata = (event) => {
                audio.play();
                audio.onloadeddata = null;
            };
            play_buttons.forEach(el => {
                set_button_state(el, false);
            });
            set_button_state(e, true);
            set_button_state(big_button, true);
        };
    });
});