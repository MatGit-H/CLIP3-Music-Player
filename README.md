# CLIP3

**CLIP3** is a terminal music player with an interactive user interface that is controlled using the keyboard. It is able to play music by navigating to specific folders and importing them. Additionally, you are able to use our Downloader to import music by pasting Youtube or Spotify URL's.

## Project Video

https://www.youtube.com/watch?v=Oq-ToTZjyi4

## Install


```bash
git clone https://github.com/MatGit-H/CLIP3-Music-Player.git
cd CLIP3-Music-Player
pip install .
```


### How to run it:
Command to run the program (in /CLIP3-Music-Player):
```bash
ui.py          
```

## How to use it

### Playing music from existing folders
1. Run `ui.py` in \CLIP3-Music-Player.
2. Press **`K`** to enter File Navigation Mode, where you can use arrow keys to navigate to your chosen folder
3. Once you've navigated to your chosen folder you can press **`Enter`** on that folder to add all songs to the playlist, or press **`Enter`** on each individual song.
4. Now you can play the songs from the playlist (on the right) by hitting **`Space`** to toggle Pause/Unpause.
5. You can navigate to any song from the playlist by pressing **`N`** to enter Playlist Navigation Mode and control it with arrow keys and **`Enter`**

### Importing music with the downloader
1. Press ``D`` to focus the downloader and copy and paste a audio/video link (anything supported by yt-dlp or spotify URLs).
2. Press ``Enter`` and it will automatically download the songs and show them in the playlist.

---

## Controls

### Normal mode

| Key | Action |
|-----|--------|
| `Space` | Pause / Resume |
| `K` | Enter File Navigation Mode |
| `N` | Enter Playlist Navigation Mode |
| `B` | Collapse / Expand Footer |
| `↑` / `↓` | Volume up / down |
| `I` | Info / Settings |
| `Esc` | Quit |

### File Navigation mode (K)

| Key | Action |
|-----|--------|
| `K` | Exit/Enter Playlist Navigation Mode |
|  `↑` / `↓` | Move UP/DOWN |
| `←` / `→`  | Exit Folder / Enter Folder |
| `Enter` | Add Song / Entire Folder to current playlist |

### Playlist Navigation mode (N)

| Key | Action |
|-----|--------|
| `N` | Exit/Enter Playlist Navigation Mode |
|  `↑` `↓` | Move UP/DOWN |
| `Enter` | Play Song |

---
## License

MIT — see `pyproject.toml`.
