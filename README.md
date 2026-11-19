# CLIP3

**CLIP3** is a terminal music player with an interactive user interface that is controlled using the keyboard. It is able to play music by navigating to specific folders and importing them. Additionally, you are able to use our Downloader to import music by pasting Youtube or Spotify URL's.

## Project Video

https://www.youtube.com/watch?v=Oq-ToTZjyi4

## Project Report PDF

'CLIP3 Project Report.pdf' in the folder.

[View Full PDF](CLIP3%20Project%20Report.pdf)

## Self Evaluation Form

'CLIP 3 Evaluation 2.xlsx' in the folder.

[View File](CLIP3%20Evaluation%202.xlsx)

## Install


```bash
git clone https://github.com/MatGit-H/CLIP3-Music-Player.git
cd CLIP3-Music-Player
pip install .

```

## Uninstall

```bash
pip uninstall clip3
```


### How to run it:
Command to run the program from anywhere:
```bash
clip3
```


Command to run the program in /CLIP3-Music-Player:
```bash
ui.py          
```
or
```bash
python ui.py     
```

## How to use it

### Playing music from existing folders
1. Press **`K`** to enter File Navigation Mode, where you can use arrow keys to navigate to your chosen folder. (UP/DOWN to move and LEFT/RIGHT to exit/enter)
2. Once you've navigated to your chosen folder you can press **`Enter`** on that folder to add the songs within to the playlist, or press **`Enter`** on each individual song.
3. Exit File Navigation mode by pressing **`K`** again.
4. Press **`N`** to enter playlist navigation mode where you can navigate to your selected song and press **`Enter`** to play it.
5. Pause/Resume by pressing **`Space`**.

### Importing music with the downloader
1. Press ``D`` to focus the downloader and copy and paste a audio/video link (anything supported by yt-dlp or spotify URLs).
2. Press ``Enter`` and it will automatically download the song(s) and show them in the playlist.
3. Press ``Esc`` to un-focus the downloader.

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
| `S` | Info / Settings |
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
