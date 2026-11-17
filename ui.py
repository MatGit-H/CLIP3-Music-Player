from rich.console import Console
from rich.console import Group
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.align import Align
from rich.table import Table
from rich import print as rprint
from rich import box
from blessed import Terminal
import threading
from mutagen import File
import os
from Decoder import probe_duration
from Downloader import Downloader
from Player import Player
from shared.song import Song, SongStatus
from Visualizer import Spectrum, render_bars, waveform
import numpy as np

term = Terminal()
console = Console()
running = True
count = 0

currentStyle = box.ROUNDED
settingsIndex = 0

fileNavPath = os.getcwd()

fileNavItems = []
fileNavIndex = 0
fileNavScroll = 0

fileNavShowSongs = True

fileNavEnabled = False

downloaderTextBox = ""
downloaderFocused = False
downloaderErrorBox = ""
active_downloader = None  # Downloader running in background, or None
imported_download_ids = set()  # id(song) already added to playlistData

footerOpen = True
settingsOpen = False
playingSong = False
sidebarNavMode = False
sidebarNavMode_I = 0
currentSong = None  # Song | None
debugPrint = set()

volume = 50
playlistData = {}  # dict[int, Song]

# False = needs a redraw. Player panel is always refreshed each frame.
layout_rendered = False
header_rendered = False
sidebar_rendered = False
footer_rendered = False
settings_rendered = False
_layout_key = None     # last (settingsOpen, footerOpen) structure
_idle_viz_rows = None  # cached blank/decayed bars when not playing
_idle_wave_rows = None  # cached blank waveform when not playing

# Once rendered we wont render it again until the layout changes. This is to reduce flickering and improve performance. -Ryan 
def mark_unrendered(*, layout=False, header=False, sidebar=False, footer=False, settings=False):
    global layout_rendered, header_rendered, sidebar_rendered, footer_rendered, settings_rendered
    if layout:
        layout_rendered = False
    if header:
        header_rendered = False
    if sidebar:
        sidebar_rendered = False
    if footer:
        footer_rendered = False
    if settings:
        settings_rendered = False


# Since we will be using the Song object from downloader i wont pass in duration in formatted form so i will add formatter here. -Ryan
def fmt_duration(seconds):
    if seconds is None:
        return "0:00"
    s = int(seconds)
    return f"{s // 60}:{s % 60:02d}"


def next_playlist_index():
    return max(playlistData.keys(), default=-1) + 1

# Autoplay while background worker downloads this checks using Song Object's states and adds to playlistData if the song is ready and has a local path. -Ryan
def autoplay(player):
    global active_downloader, playlistData, currentSong, playingSong
    global downloaderErrorBox, imported_download_ids

    dl = active_downloader
    if dl is None:
        return

    for song in dl.songs.values():
        if song.status != SongStatus.READY or not song.local_path:
            continue
        sid = id(song)
        if sid in imported_download_ids:
            continue
        playlistData[next_playlist_index()] = song
        imported_download_ids.add(sid)
        mark_unrendered(sidebar=True)
        debugPrint.add(
            f"downloaded: {song.title} | {song.channel} | {song.local_path}"
        )
        if player.song is None:
            try:
                currentSong = song
                player.play(song)
                playingSong = True
                mark_unrendered(sidebar=True, header=True)
            except Exception as e:
                debugPrint.add(f"autoplay failed: {e}")

    alive = dl._thread is not None and dl._thread.is_alive()
    if not alive:
        errors = [
            s for s in dl.songs.values()
            if s.status == SongStatus.ERROR
        ]
        if errors:
            downloaderErrorBox = f"[red]Download finished with {len(errors)} error(s)"
        else:
            downloaderErrorBox = "[green]Download complete"
        active_downloader = None
        mark_unrendered(footer=True)


def build_settings_layout():
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body", ratio=1),
    )
    layout["body"].split_row(
        Layout(name="settings", ratio=3),
        Layout(name="info", ratio=2),
    )
    return layout


def build_main_layout(show_footer):
    layout = Layout()
    if show_footer:
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body", ratio=1),
            Layout(name="footer", size=12),
        )
        layout["footer"].split_row(
            Layout(name="download", ratio=3),
            Layout(name="filenav", ratio=2),
        )
    else:
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body", ratio=1),
        )
    layout["body"].split_row(
        Layout(name="player", ratio=3),
        Layout(name="sidebar", ratio=2),
    )
    return layout


def render_header_panel(settings_mode=False):
    header = Table.grid(expand=True)
    header.add_column(justify="left")
    header.add_column(justify="center")
    header.add_column(justify="right")
    if settings_mode:
        left = "♫ [bold red]CLIP3 [bold white]Music Player ♫     (SETTINGS/INFO)"
        mid = "(S) ⚙/🛈  "
    else:
        left = "♫ [bold red]CLIP3 [bold white]Music Player ♫"
        mid = "(S) ⚙  / 🛈   (B) Collapse Footer"
    max_width = 20
    filled = int((volume / 100) * max_width)
    empty = max_width - filled
    header.add_row(left, mid, f"🔊 [{'▓' * filled + '░' * empty}]")
    return Panel(header, box=currentStyle)


def render_settings_panels():
    contentData = [
        Align.left("Settings Here: (placeholder)\n\n"),
        Align.left("Current Style: \n"),
        Align.left(f"{'[black on white]' if settingsIndex == 0 else ''}{'[✓]' if currentStyle == box.ROUNDED else '[X]'} 1 - Rounded Corners"),
        Align.left(f"{'[black on white]' if settingsIndex == 1 else ''}{'[✓]' if currentStyle == box.ASCII else '[X]'} 2 - ASCII Characters"),
        Align.left(f"{'[black on white]' if settingsIndex == 2 else ''}{'[✓]' if currentStyle == box.DOUBLE else '[X]'} 3 - Double-Lined"),
        Align.left(f"{'[black on white]' if settingsIndex == 3 else ''}{'[✓]' if currentStyle == box.MARKDOWN else '[X]'} 4 - Markdown"),
        Align.left(f"{'[black on white]' if settingsIndex == 4 else ''}{'[✓]' if currentStyle == box.HEAVY else '[X]'} 5 - Heavy"),
        Align.left(f"{'[black on white]' if settingsIndex == 5 else ''}{'[✓]' if currentStyle == box.MINIMAL_HEAVY_HEAD else '[X]'} 6 - MINIMAL 1"),
        Align.left(f"{'[black on white]' if settingsIndex == 6 else ''}{'[✓]' if currentStyle == box.HORIZONTALS else '[X]'} 7 - HORIZONTALS"),
    ]
    settings_panel = Panel(Group(*contentData), box=currentStyle)
    info = Group(
        Align.center("\n\n IN NORMAL MODE: ARROW KEYS FOR VOLUME (top right) \n\n"),
        Align.center("\n\n IN NORMAL MODE: [B] FOR BOTTOM BAR TOGGLE \n\n"),
        Align.center("\n\n IN NORMAL MODE: [SPACE] FOR PLAYING SONG \n\n"),
        Align.center("\n\n SIDEBAR NAV MODE: PRESS [N] "),
        Align.center("\nARROW KEYS TO MOVE AROUND, ENTER TO SELECT SONG \n"),
    )
    info_panel = Panel(info, box=currentStyle)
    return settings_panel, info_panel


def render_player_panel(width, player, spectrum):
    global _idle_viz_rows, _idle_wave_rows
    max_width = max(10, int(width * 0.3))
    dur = (currentSong.duration or 0) if currentSong else 0
    pos = player.position if (currentSong is not None and player.song is currentSong) else 0.0
    if dur > 0:
        filled = int((pos / dur) * max_width)
    else:
        filled = 0
    filled = max(0, min(filled, max_width))
    progressbar = "▓" * filled + "." * (max_width - filled)

    viz_height = 7
    wave_width = max(16, min(max_width, 34))
    wave_height = 3

    def _spaced(rows):
        # air out the bar column so it feels less concentrated
        return [" ".join(row) for row in rows]

    if player.song is not None and not player.paused:
        samples = player.latest(spectrum.fft_size)
        audioVis = _spaced(render_bars(spectrum.update(samples), viz_height))
        waveVis = waveform(samples, wave_width, wave_height, gain=1.3)
        _idle_viz_rows = audioVis
        _idle_wave_rows = waveVis
    elif player.song is not None:
        # paused: decay bars; flatten wave
        silence = np.zeros((spectrum.fft_size, 2), dtype=np.float32)
        audioVis = _spaced(render_bars(spectrum.update(silence), viz_height))
        waveVis = waveform(silence, wave_width, wave_height)
        _idle_viz_rows = audioVis
        _idle_wave_rows = waveVis
    else:
        if _idle_viz_rows is None:
            _idle_viz_rows = _spaced(render_bars(np.zeros(spectrum.n_bars), viz_height))
        if _idle_wave_rows is None:
            _idle_wave_rows = waveform(np.zeros((64, 2), dtype=np.float32), wave_width, wave_height)
        audioVis = _idle_viz_rows
        waveVis = _idle_wave_rows

    if currentSong is None:
        songText, songArtist, songTime = "Not Playing Any Song", "N/A", "N/A"
    else:
        songText = currentSong.title
        songArtist = currentSong.channel or "N/A"
        songTime = f"{fmt_duration(pos)} / {fmt_duration(dur)}"

    playingIcon = "►" if playingSong else "❚❚"
    content = Group(
        Align.center(Group(*audioVis)),
        Align.center(Group(*waveVis)),
        Align.center(Text(f"{songText}", style="bold white")),
        Align.center(Text(f"{songArtist}", style="grey50")),
        Align.left(Text(f"{playingIcon} {songTime}", style="bold white")),
        Align.center(Text(f"{progressbar}\n")),
    )
    return Panel(Align.center(content, vertical="bottom"), box=currentStyle)


def render_sidebar_panel():
    contentData = [
        Align.left(f"{fileNavPath}\n", style="grey50"),
        Align.center("[bold italic white on grey50]#   Title       Artist       Time\n"),
    ]
    for index, song in playlistData.items():
        title = song.title
        artistname = song.channel or "N/A"
        time = fmt_duration(song.duration)
        displayTitle = title[:18] + ".." if len(title) > 18 else title
        is_current = song is currentSong

        if sidebarNavMode and index == sidebarNavMode_I:
            if is_current:
                if playingSong:
                    contentData.append(Align.center(f"[white on black][black on light_green][►]  {index} - {displayTitle} - {artistname} - {time}  \n"))
                else:
                    contentData.append(Align.center(f"[white on black][black on yellow1][||]  {index} - {displayTitle} - {artistname} - {time}  \n"))
            else:
                contentData.append(Align.center(f"[black on white]{index} - {displayTitle} - {artistname} - {time}  \n"))
        elif is_current:
            if playingSong:
                contentData.append(Align.center(f"[black on light_green][►] {index} - {displayTitle} - {artistname} - {time}\n"))
            else:
                contentData.append(Align.center(f"[black on yellow1][||]  {index} - {displayTitle} - {artistname} - {time}\n"))
        else:
            contentData.append(Align.center(f"{index} - {displayTitle} - {artistname} - {time}\n", style="bold white"))

    if sidebarNavMode:
        contentData.append(Align.center("\nNAV MODE: [↑ ← → ↓] [↵]"))
    else:
        contentData.append(Align.center("\n(N) Enter Navigation Mode"))

    title = "[black on white]-=-=- Playlist (N) -=-=-" if sidebarNavMode else "Playlist (N)"
    return Panel(Group(*contentData), box=currentStyle, title=title)


def render_download_panel():
    content = Group(
        Align.left(
            f"Enter URL to Download: {downloaderErrorBox if len(downloaderTextBox) == 0 else downloaderTextBox}"
        )
    )
    title = "[black on white]-=-=- Downloader (D) -=-=-" if downloaderFocused else "Downloader (D)"
    return Panel(content, box=currentStyle, title=title)


def render_filenav_panel():
    title = "[black on white]=-=- File Navigation (K) -=-=" if fileNavEnabled else "File Navigation (K)"
    return Panel(render_file_nav(), box=currentStyle, title=title)


def sync_layout(live, layout, width, player, spectrum):
    global layout_rendered, header_rendered, sidebar_rendered, footer_rendered, settings_rendered, _layout_key

    show_footer = footerOpen
    key = ("settings",) if settingsOpen else ("main", show_footer)

    if layout is None or key != _layout_key or not layout_rendered:
        layout = build_settings_layout() if settingsOpen else build_main_layout(show_footer)
        _layout_key = key
        layout_rendered = True
        # new structure → all panels need a first paint
        header_rendered = sidebar_rendered = footer_rendered = settings_rendered = False
        live.update(layout, refresh=True)

    if settingsOpen:
        if not header_rendered:
            layout["header"].update(render_header_panel(settings_mode=True))
            header_rendered = True
        if not settings_rendered:
            settings_panel, info_panel = render_settings_panels()
            layout["settings"].update(settings_panel)
            layout["info"].update(info_panel)
            settings_rendered = True
    else:
        if not header_rendered:
            layout["header"].update(render_header_panel(settings_mode=False))
            header_rendered = True
        # player every frame (progress + viz)
        layout["player"].update(render_player_panel(width, player, spectrum))
        if not sidebar_rendered:
            layout["sidebar"].update(render_sidebar_panel())
            sidebar_rendered = True
        if show_footer and not footer_rendered:
            layout["download"].update(render_download_panel())
            layout["filenav"].update(render_filenav_panel())
            footer_rendered = True

    live.refresh()
    return layout

def get_folder_data(folder_path):
    playlist = {}

    supported = (".mp3", ".wav", ".flac", ".ogg", ".m4a", ".opus", ".webm")

    try:
        filenames = sorted(os.listdir(folder_path))
    except Exception:
        debugPrint.add("something went wrong in get_folder_data")
        return playlist

    for filename in filenames:
        filepath = os.path.join(folder_path, filename)

        if not os.path.isfile(filepath):
            continue

        if not filename.lower().endswith(supported):
            continue

        playlist[len(playlist)] = get_song_data(filepath)

    return playlist


def get_song_data(filepath):
    filename = os.path.splitext(os.path.basename(filepath))[0]

    title = filename
    artist = None
    duration = None

    try:
        audio = File(filepath, easy=True)

        if audio:
            title = audio.get("title", [title])[0] or title
            artist = audio.get("artist", [None])[0] or None

            if audio.info:
                duration = float(audio.info.length)

    except Exception as e:
        debugPrint.add(f"Error reading {filename}: {e}")

    if duration is None:
        duration = probe_duration(filepath)

    # Downloader saves as Title--Channel.ext — slice artist from the stem stuff we did from grader bro its string slicing -Ryan
    if artist is None:
        sep = filename.find("--")
        if sep != -1:
            title = filename[:sep].strip()
            artist = filename[sep + 2:].strip() or None

    return Song(
        title=title,
        page_url="",
        channel=artist,
        duration=duration,
        local_path=filepath,
        source="local",
        status=SongStatus.READY,
    )
def render_file_nav():
    global fileNavItems, fileNavIndex, fileNavPath, fileNavEnabled
    global fileNavScroll, fileNavShowSongs

    content = []

    visibleItems = 8

    content.append(f"📁 {fileNavPath}")

    

    if len(fileNavItems) == 0:
        if not fileNavShowSongs:
            content.append("(No subfolders — press I to show songs)")
        else:
            content.append("(Empty directory)")

    else:
        visible = fileNavItems[fileNavScroll:fileNavScroll + visibleItems]
        i = fileNavScroll
        for item in visible:
            selected = (i == fileNavIndex)
            icon = "📁" if item["type"] == "folder" else "♫"
            label = f"{icon} {item['name']}"
            if selected and fileNavEnabled:
                content.append(f"[black on white] > {label}[/]")
            elif selected:
                content.append(f" > {label}")
            else:
                content.append(f"   {label}")
            i += 1

    content.append(
        f"[I] Songs: {'ON' if fileNavShowSongs else 'OFF'}  [→/Enter] Open  [A] Add folder/song"
    )

    return "\n".join(content)
def keyboard_worker(player):
    global running, footerOpen, volume, sidebarNavMode, sidebarNavMode_I, playlistData, currentSong, debugPrint, settingsOpen, playingSong, fileNavScroll
    global fileNavPath, fileNavItems, fileNavIndex, fileNavEnabled, currentStyle, downloaderFocused, downloaderTextBox
    global fileNavShowSongs, settingsIndex, debugPrint, running, downloaderErrorBox, active_downloader
    with term.cbreak():
        while running:
            key = term.inkey(timeout=0.1)
            
            if not key:
                continue
            if downloaderFocused:
                if key.name == "KEY_ESCAPE":
                    downloaderFocused = False
                    mark_unrendered(footer=True)
                elif key.name == "BRACKETED_PASTE":
                    pasted_content = key.text
                    downloaderTextBox += pasted_content
                    mark_unrendered(footer=True)
                elif key.name == "KEY_BACKSPACE":
                    downloaderTextBox = downloaderTextBox[:-1]
                    mark_unrendered(footer=True)
                elif key.name == "KEY_ENTER":
                    if len(downloaderTextBox) < 7:
                        downloaderErrorBox = "[red]Not a Valid URL!"
                        downloaderTextBox = ""
                        mark_unrendered(footer=True)
                    elif active_downloader is not None:
                        downloaderErrorBox = "[red]Download already in progress"
                        mark_unrendered(footer=True)
                    else:
                        url = downloaderTextBox
                        try:
                            # start() extracts metadata sync then downloads on a daemon thread — no join()
                            dl = Downloader(url)
                            dl.start()
                            active_downloader = dl
                            downloaderTextBox = ""
                            downloaderErrorBox = "[yellow]Downloading…"
                            mark_unrendered(footer=True)
                        except Exception as e:
                            active_downloader = None
                            downloaderErrorBox = "[red]Not a Valid URL!"
                            downloaderTextBox = ""
                            debugPrint.add(f"download start failed: {e}")
                            mark_unrendered(footer=True)
                else:
                    if not key.is_sequence and key.isprintable():
                        downloaderTextBox += key
                        mark_unrendered(footer=True)
                
            else:       
                if key.lower() == "b":
                    footerOpen = not footerOpen
                    mark_unrendered(layout=True)
                elif key.lower() == "i":
                    if fileNavEnabled:
                        fileNavShowSongs = not fileNavShowSongs
                        fileNavIndex = 0
                        fileNavScroll = 0
                        refresh_file_nav()
                        mark_unrendered(footer=True)
                elif key.lower() == "k":
                    if settingsOpen == False:
                        downloaderFocused = False
                        sidebarNavMode = False
                        fileNavEnabled = not fileNavEnabled
                        mark_unrendered(footer=True, sidebar=True)
                elif key.lower() == "n":
                    if settingsOpen == False:
                        if fileNavEnabled:
                            fileNavEnabled = False
                        sidebarNavMode = not sidebarNavMode
                        downloaderFocused = False
                        mark_unrendered(sidebar=True, footer=True)
                elif key.lower() == "s":
                    settingsOpen = not settingsOpen
                    sidebarNavMode = False
                    downloaderFocused = False
                    mark_unrendered(layout=True, settings=True, header=True)
                elif key.lower() == "d":
                    downloaderFocused = not downloaderFocused
                    sidebarNavMode = False
                    fileNavEnabled = False
                    mark_unrendered(footer=True, sidebar=True)
                elif key.lower() == "a":
                    if fileNavEnabled and footerOpen and fileNavItems:
                        add_file_nav_selection()
                elif key.lower() == " ": # Space bar -> Plays song
                    if player.song is not None: # Song active toggle pause
                        player.toggle_pause()
                        playingSong = not player.paused
                        mark_unrendered(sidebar=True)
                    elif currentSong is not None and currentSong.local_path: # Opening from local path
                        try:
                            player.play(currentSong)
                            playingSong = True
                            mark_unrendered(sidebar=True)
                        except Exception as e:
                            debugPrint.add(f"play failed: {e}")
                            playingSong = False
                elif key.name == "KEY_UP":
                    if settingsOpen:
                        if settingsIndex > 0:
                            settingsIndex -= 1
                            mark_unrendered(settings=True)
                    else:
                        if fileNavEnabled and footerOpen:
                            if fileNavIndex > 0:
                                fileNavIndex -= 1
                            update_file_nav_scroll()
                            mark_unrendered(footer=True)
                        elif sidebarNavMode:
                            sidebarNavMode_I -= 1
                            mark_unrendered(sidebar=True)
                        else:
                            if volume < 100:
                                volume += 5
                                player.set_volume(volume / 100)
                                mark_unrendered(header=True)
                elif key.name == "KEY_DOWN":
                    if settingsOpen:
                        if settingsIndex < 20:
                            settingsIndex += 1
                            mark_unrendered(settings=True)
                    else:
                        if fileNavEnabled and footerOpen:
                            if fileNavIndex < len(fileNavItems) - 1:
                                fileNavIndex += 1
                            update_file_nav_scroll()
                            mark_unrendered(footer=True)
                        elif sidebarNavMode:
                            sidebarNavMode_I += 1
                            mark_unrendered(sidebar=True)
                        else:
                            if volume > 0:
                                volume -= 5
                                player.set_volume(volume / 100)
                                mark_unrendered(header=True)
                elif key.name == "KEY_LEFT":
                    if fileNavEnabled:
                        parent = os.path.dirname(fileNavPath)
                        if parent != fileNavPath:
                            fileNavPath = parent
                            fileNavScroll = 0
                            fileNavIndex = 0
                            refresh_file_nav()
                            mark_unrendered(footer=True, sidebar=True)
                elif key.name == "KEY_RIGHT":
                    if fileNavEnabled and fileNavItems:
                        enter_file_nav_folder()
                elif key.name == "KEY_ENTER":
                    debugPrint.add(f"{playingSong},{currentSong}")
                    
                    if settingsOpen:
                        if settingsIndex == 0:
                            currentStyle = box.ROUNDED
                        elif settingsIndex == 1:
                            currentStyle = box.ASCII
                        elif settingsIndex == 2:
                            currentStyle = box.DOUBLE
                        elif settingsIndex == 3:
                            currentStyle = box.MARKDOWN
                        elif settingsIndex == 4:
                            currentStyle = box.HEAVY
                        elif settingsIndex == 5:
                            currentStyle = box.MINIMAL_HEAVY_HEAD
                        elif settingsIndex == 6:
                            currentStyle = box.HORIZONTALS
                        mark_unrendered(settings=True, header=True, layout=True)

                    else:
                        if sidebarNavMode:
                            if sidebarNavMode_I in playlistData:
                                song = playlistData[sidebarNavMode_I]
                                currentSong = song
                                if song.local_path:
                                    try:
                                        player.play(song)
                                        playingSong = True
                                    except Exception as e:
                                        debugPrint.add(f"play failed: {e}")
                                        playingSong = False
                                else:
                                    debugPrint.add(f"no local_path: {song.title}")
                                    playingSong = False
                                mark_unrendered(sidebar=True)
                        elif fileNavEnabled and fileNavItems:
                            selected = fileNavItems[fileNavIndex]
                            if selected["type"] == "folder":
                                enter_file_nav_folder()
                            elif selected["type"] == "song":
                                add_file_nav_selection()

def enter_file_nav_folder():
    global fileNavPath, fileNavIndex, fileNavScroll, fileNavItems
    if not fileNavItems:
        return
    selected = fileNavItems[fileNavIndex]
    if selected["type"] != "folder":
        return
    fileNavPath = selected["path"]
    fileNavIndex = 0
    fileNavScroll = 0
    refresh_file_nav()
    mark_unrendered(footer=True, sidebar=True)


def add_file_nav_selection():
    global playlistData
    if not fileNavItems:
        return
    selected = fileNavItems[fileNavIndex]
    if selected["type"] == "folder":
        folderData = get_folder_data(selected["path"])
        debugPrint.add(f"importing {selected['name']}")
        next_index = next_playlist_index()
        for song in folderData.values():
            playlistData[next_index] = song
            next_index += 1
        debugPrint.add(f"len of playlistdata {len(playlistData)} ")
        mark_unrendered(sidebar=True)
    elif selected["type"] == "song":
        song = get_song_data(selected["path"])
        playlistData[next_playlist_index()] = song
        debugPrint.add(f"added song {song.title}")
        mark_unrendered(sidebar=True)


def update_file_nav_scroll():
    global fileNavScroll, fileNavIndex

    visibleItems = 8  # must match render_file_nav()

    if fileNavIndex < fileNavScroll:
        fileNavScroll = fileNavIndex

    elif fileNavIndex >= fileNavScroll + visibleItems:
        fileNavScroll = fileNavIndex - visibleItems + 1


def refresh_file_nav():
    global fileNavItems, fileNavIndex, fileNavPath, fileNavScroll

    fileNavItems = []

    try:
        entries = os.listdir(fileNavPath)

        folders = []
        songs = []

        for entry in entries:
            fullPath = os.path.join(fileNavPath, entry)

            if os.path.isdir(fullPath):
                folders.append({"name": entry, "path": fullPath, "type": "folder"})

            elif fileNavShowSongs and entry.lower().endswith((".mp3", ".wav", ".flac", ".ogg", ".m4a", ".opus", ".webm")):
                songs.append({"name": entry, "path": fullPath, "type": "song"})

        folders.sort(key=lambda x: x["name"].lower())
        songs.sort(key=lambda x: x["name"].lower())

        fileNavItems = folders + songs

        if fileNavItems:
            fileNavIndex = min(fileNavIndex, len(fileNavItems) - 1)
        else:
            fileNavIndex = 0
            fileNavScroll = 0

    except PermissionError:
        fileNavItems = []
        fileNavIndex = 0
        fileNavScroll = 0



refresh_file_nav()
player = Player() # Player object should be accessible by keyboard worker so I created here and will pass it to keyboardworker as an argument -Ryan
player.set_volume(volume / 100)
# Fewer bars + smaller FFT = less CPU; attack/decay keep motion smooth
spectrum = Spectrum(n_bars=17, fft_size=2048, floor_db=-70.0, attack=0.55, decay=0.12)
keyboardThread = threading.Thread(target=keyboard_worker, args=(player,), daemon=True)
keyboardThread.start()

layout = None
try:
    with Live(console=console, refresh_per_second=10, screen=True, vertical_overflow="crop") as live:
        while running:
            count += 1
            if count >= 500:
                count = 0
            autoplay(player)
            width = console.size.width
            layout = sync_layout(live, layout, width, player, spectrum)


except KeyboardInterrupt:
    running = False  # let keyboard_worker leave inkey loop and exit term.cbreak() without this after quitting my terminal would be messed up and I would have to reset it. -Ryan
    player.close()
    keyboardThread.join(timeout=1.0) # This fully waits for the keyboard thread to exit before exiting the program. -Ryan
    for x in debugPrint:
        print(x)
    print("CLIP3 exited successfully")
    raise SystemExit(0)