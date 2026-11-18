from rich.console import Console
from rich.console import Group
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.align import Align
from rich.table import Table
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
sidebarScrollOffset = 0
max_visible_songs = 20
fileNavShowSongs = True
fileNavEnabled = False

downloaderTextBox = ""
downloaderFocused = False
downloaderErrorBox = ""
active_downloader = None  # downloader running in background, or None
imported_download_ids = set()  # id(song) already added to playlistData

footerOpen = True
settingsOpen = False
playingSong = False
sidebarNavMode = False
sidebarNavMode_I = 0
currentSong = None  # song or None
debugPrint = set()
tempwidth = 0
volume = 50
playlistData = {}  # dict[int, Song]




# LAYOUT CREATOR (MAIN RENDERER)

def create_layout(width, height, count, player, spectrum):
    global footerOpen, volume, settingsIndex, max_visible_songs, sidebarScrollOffset,tempwidth, downloaderErrorBox, downloaderTextBox, currentStyle, settingsIndex, sidebarNavMode, running, sidebarNavMode_I, currentSong, playlistData, debugPrint, settingsOpen, playingSong, audioVis, fileNavScroll, fileNavPath
    layout = Layout()


    # SETTINGS ------------------------------------------------------------------------------------------------
    if settingsOpen:
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body", ratio=1),
        )
        layout["body"].split_row(
            Layout(name="settings", ratio=3),
            Layout(name="info", ratio=2)
        )
        # HEADER (SETTINGS MENU) -----------------------------------------
        header = Table.grid(expand=True)
        header.add_column(justify='left')
        header.add_column(justify="center")
        header.add_column(justify="right")
        hRow = []
        hRow.append("♫ [bold red]CLIP3 [bold white]Music Player ♫     (SETTINGS/INFO)")
        hRow.append("(S) ⚙  / 🛈  ")
        max_width = 20
        filled = int((volume/100)*max_width)
        empty = max_width - filled

        hRow.append(f'🔊 [{'▓'*filled +'░'*empty}]')
        header.add_row(*hRow)

        layout["header"].update(
            Panel(header, box=currentStyle)
        )
        # SETTINGS MENU --------------------------------------------------
        

        contentData = [
            Align.left("Settings:\n\n"),
            Align.left(f"Current Style: \n"),
            Align.left(f"{"[black on white]" if settingsIndex == 0 else ""}{'[✓]' if currentStyle == box.ROUNDED else '[X]'} 1 - Rounded Corners"),
            Align.left(f"{"[black on white]" if settingsIndex == 1 else ""}{'[✓]' if currentStyle == box.ASCII else '[X]'} 2 - ASCII Characters"),
            Align.left(f"{"[black on white]" if settingsIndex == 2 else ""}{'[✓]' if currentStyle == box.DOUBLE else '[X]'} 3 - Double-Lined"),
            Align.left(f"{"[black on white]" if settingsIndex == 3 else ""}{'[✓]' if currentStyle == box.MARKDOWN else '[X]'} 4 - Markdown"),
            Align.left(f"{"[black on white]" if settingsIndex == 4 else ""}{'[✓]' if currentStyle == box.HEAVY else '[X]'} 5 - Heavy"),
            Align.left(f"{"[black on white]" if settingsIndex == 5 else ""}{'[✓]' if currentStyle == box.MINIMAL_HEAVY_HEAD else '[X]'} 6 - MINIMAL 1"),
            Align.left(f"{"[black on white]" if settingsIndex == 6 else ""}{'[✓]' if currentStyle == box.HORIZONTALS else '[X]'} 7 - HORIZONTALS")
        ]
        content = Group(*contentData)
        layout["settings"].update(
            Panel(content,box=currentStyle)
        )
        # INFO MENU -----------------------------------------------------------

        content = Group(
            
            Align.center("\n\n In Normal Mode:\n\n"),
            Align.center("Space | Pause / Resume"),
            Align.center("K | File Nav Mode"),
            Align.center("N | Playlist Nav Mode"),
            Align.center("B | Toggle Footer"),
            Align.center("S | Settings/Info"),
            Align.center("\n\n In File Nav Mode:\n\n"),
            Align.center("UP DOWN | Move UP/DOWN"),
            Align.center("LEFT RIGHT | Exit / Enter Folder"),
            Align.center("Enter | Add Entire Folder or Song to playlist"),
            Align.center("\n\n In Playlist Nav Mode:\n\n"),
            Align.center("UP DOWN | Move UP/DOWN"),
            Align.center("Enter | Play Song"),
            Align.center("\n\n In Downloader \n\n"),
            Align.center("Type/Paste | Adds text to Textbox"),
            Align.center("Enter | Queries URL and adds that to playlist"),
            
            
            
        )

        layout["info"].update(
            Panel(content,box=currentStyle)
        )

        return layout
    # MAIN LAYOUT (NON SETTINGS) ---------------------------------------------------------------------------------------
    else:
        if footerOpen: # perhaps in the future, we add an animation for closing/opening
            layout.split_column(
                Layout(name="header", size=3),
                Layout(name="body", ratio=1),
                Layout(name="footer", size=12)
            )
            layout["footer"].split_row(
                Layout(name="download",ratio=3),
                Layout(name="filenav", ratio=2)
            )
        else:
            layout.split_column(
                Layout(name="header", size=3),
                Layout(name="body", ratio=1),
            )

        layout["body"].split_row(
            Layout(name="player", ratio=3),
            Layout(name="sidebar", ratio=2)
        )

        
        
        # Header ======================================================================================
        header = Table.grid(expand=True)
        header.add_column(justify='left')
        header.add_column(justify="center")
        header.add_column(justify="right")
        hRow = []
        hRow.append("♫ [bold red]CLIP3 [bold white]Music Player ♫")
        hRow.append("(S) ⚙  / 🛈   (B) Collapse Footer")
        max_width = 20
        filled = int((volume/100)*max_width)
        empty = max_width - filled

        hRow.append(f'🔊 [{'▓'*filled +'░'*empty}]')
        header.add_row(*hRow)

        layout["header"].update(
            Panel(header, box=currentStyle)
        )

        # Player ======================================================================================
        max_width = max(10, int(width * 0.3))
        dur = (currentSong.duration or 0) if currentSong else 0
        pos = player.position if (currentSong is not None and player.song is currentSong) else 0.0
        if dur > 0:
            filled = int((pos / dur) * max_width)
        else:
            filled = 0
        filled = max(0, min(filled, max_width))
        progressbar = "█" * filled + "-" * (max_width - filled)
        progress = (pos / dur * 100) if dur > 0 else 0.0
        progress = max(0.0, min(progress, 100.0))

        viz_height = int(height*.5)

        wave_width = max(16, min(max_width, 34))
        wave_height = 4


        if width != tempwidth: # optimization, check if its changed at all, if so then update
            width = max_width
            spectrum = Spectrum(n_bars=(int(max_width*0.7)), fft_size=2048, floor_db=-90.0, attack=0.55, decay=0.12)


        if player.song is not None and not player.paused:
            samples = player.latest(spectrum.fft_size)
            audioVis = [" ".join(row) for row in render_bars(spectrum.update(samples), viz_height)]
            waveVis = waveform(samples, wave_width, wave_height, gain=1.3)
        elif player.song is not None:
            silence = np.zeros((spectrum.fft_size, 2), dtype=np.float32)
            audioVis = [" ".join(row) for row in render_bars(spectrum.update(silence), viz_height)]
            waveVis = waveform(silence, wave_width, wave_height)
        else:
            audioVis = [" ".join(row) for row in render_bars(np.zeros(spectrum.n_bars), viz_height)]
            waveVis = waveform(np.zeros((64, 2), dtype=np.float32), wave_width, wave_height)

        if currentSong is None:
            songText, songArtist, songTime = "Not Playing Any Song", "N/A", "N/A"
        else:
            songText = currentSong.title
            songArtist = currentSong.channel or "N/A"
            songTime = f"{fmt_duration(pos)} / {fmt_duration(dur)}"


        playingIcon = "►" if playingSong else ""
        content = Group(
            Align.center(Group(*audioVis)),
            Align.center(Group(*waveVis)),
            Align.center(Text(f"{songText}", style="bold white")),
            Align.center(Text(f"{songArtist}", style="grey50")),
            Align.center(Text(f"{playingIcon}", style="bold white")),
            Align.center(Text(f"{progressbar}")),
            Align.center(Text(f"{songTime}", style="bold white")),
        )
        layout["player"].update(
            Panel(Align.center(content, vertical="middle"),box=currentStyle))

        # Sidebar Content =================================================================================
        contentData = []
        contentData.append(Align.left(f'{fileNavPath}\n', style='grey50'),)
        contentData.append(Align.center(f'[bold italic white on grey50]#   Title       Artist       Time\n'))
        update_playlist_scroll(height)
    
        
        visible_songs = list(playlistData.items())[sidebarScrollOffset:sidebarScrollOffset + max_visible_songs]
        for index, song in visible_songs:
            title = song.title
            artistname = song.channel or "N/A"
            time = fmt_duration(song.duration)
            displayTitle = title[:18] + ".." if len(title) > 18 else title
            is_current = song is currentSong

            if sidebarNavMode:
                if index == sidebarNavMode_I:
                    if is_current:
                        if playingSong == True:
                            contentData.append(Align.center(f'[white on black][black on light_green][►]  {index} - {displayTitle} - {artistname} - {time}  \n'))
                        else:
                            contentData.append(Align.center(f'[white on black][black on yellow1][||]  {index} - {displayTitle} - {artistname} - {time}  \n'))
                    else:
                        contentData.append(Align.center(f'[black on white]{index} - {displayTitle} - {artistname} - {time}  \n'))
                else:
                    if is_current:
                        if playingSong == True:
                            contentData.append(Align.center(f'[black on light_green][►] {index} - {displayTitle} - {artistname} - {time}\n'))
                        else:
                            contentData.append(Align.center(f'[black on yellow1][||]  {index} - {displayTitle} - {artistname} - {time}\n'))
                    else:
                        contentData.append(Align.center(f'{index} - {displayTitle} - {artistname} - {time}\n', style='bold white'))
            else:
                if is_current:
                    if playingSong == True:
                        contentData.append(Align.center(f'[black on light_green][►] {index} - {displayTitle} - {artistname} - {time}\n'))
                    else:
                        contentData.append(Align.center(f'[black on yellow1][||]  {index} - {displayTitle} - {artistname} - {time}\n'))
                else:
                    contentData.append(Align.center(f'{index} - {displayTitle} - {artistname} - {time}\n', style='bold white'))
        if sidebarNavMode == True:
            contentData.append(Align.center('\nNAV MODE: [↑ ← → ↓] [↵]')) 
        else:
            contentData.append(Align.center('\n(N) Enter Navigation Mode')) 

        
        content = Group(*contentData)
        layout["sidebar"].update(Panel(content, box=currentStyle,title=f"{'[black on white]-=-=- Playlist (N) -=-=-' if sidebarNavMode else 'Playlist (N)'}"))

        # Footer ========================================================================================================
        if footerOpen:
            
            content = Group(   
                Align.left(f'Enter URL to Download: {downloaderErrorBox if len(downloaderTextBox) == 0 else downloaderTextBox}')
            )
            try:
                layout["download"].update(Panel(content, box=currentStyle,title=f"{'[black on white]-=-=- Downloader (D) -=-=- (PRESS ESC TO EXIT)' if downloaderFocused else 'Downloader (D)'}"))
            


                layout["filenav"].update(
                Panel(render_file_nav(),box=currentStyle,title=f"{'[black on white]=-=- File Navigation (K) -=-=' if fileNavEnabled else 'File Navigation (K)'}"))

            except:
                pass # for some reason it was crashing because 'download' wasnt defined even though it should be defined if footerOpen, so idk
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
        content.append("(Empty directory)")

    else:
        visible = fileNavItems[fileNavScroll:fileNavScroll + visibleItems]
        i = fileNavScroll
        for item in visible:
            selected = False
            if i == fileNavIndex:
                selected = True
            if item["type"] == "folder":
                icon = "📁"
            else:
                icon = "♫"
            prefix = "   "
            if selected:
                prefix = " > "
                if fileNavEnabled:
                    prefix = "[black on white] > "
            content.append(f"{prefix}{icon} {item['name']}[white on black]")
            i += 1
 

    content.append(
        f"[I] Show songs: {'ON' if fileNavShowSongs else 'OFF'} [ENTER] ADD"
    )

    return "\n".join(content)

# this func handles all keyboard inputs
def keyboard_worker(player):
    global running, footerOpen, volume, sidebarNavMode, sidebarNavMode_I, playlistData, currentSong, debugPrint, settingsOpen, playingSong, fileNavScroll
    global fileNavPath, fileNavItems, fileNavIndex, fileNavEnabled, currentStyle, downloaderFocused, downloaderTextBox
    global fileNavShowSongs, settingsIndex, debugPrint, running, downloaderErrorBox, active_downloader, height
    with term.cbreak():
        while running:
            key = term.inkey(timeout=0.1)
            
            if not key:
                continue
            if downloaderFocused: # <--------- DOWNLOADER ONLY
                if key.name == "KEY_ESCAPE":
                    downloaderFocused = False
                elif key.name == "BRACKETED_PASTE":
                    pasted_content = key.text
                    downloaderTextBox += pasted_content
                elif key.name == "KEY_BACKSPACE":
                    downloaderTextBox = downloaderTextBox[:-1]
                elif key.name == "KEY_ENTER":
                    if len(downloaderTextBox) < 7:
                        downloaderErrorBox = "[red]Not a Valid URL!"
                        downloaderTextBox = ""
                    elif active_downloader is not None:
                        downloaderErrorBox = "[red]Download already in progress"
                    else:
                        url = downloaderTextBox
                        try:
                            # start() extracts metadata sync then downloads on a daemon thread — no join()
                            dl = Downloader(url)
                            dl.start()
                            active_downloader = dl
                            downloaderTextBox = ""
                            downloaderErrorBox = "[yellow]Downloading…"
                        except Exception as e:
                            active_downloader = None
                            downloaderErrorBox = "[red]Not a Valid URL!"
                            downloaderTextBox = ""
                            debugPrint.add(f"download start failed: {e}")
                else:
                    if not key.is_sequence and key.isprintable():
                        downloaderTextBox += key
                
            else:    # <--------- EVERYTHING EXCEPT DOWNLOADER NOW

                if key.lower() == "b":
                    footerOpen = not footerOpen
                elif key.lower() == "i":
                    if fileNavEnabled:
                        fileNavShowSongs = not fileNavShowSongs
                        fileNavIndex = 0
                        refresh_file_nav()
                elif key.lower() == "k":
                    if settingsOpen == False:
                        downloaderFocused = False
                        sidebarNavMode = False
                        fileNavEnabled = not fileNavEnabled

                elif key.lower() == "n":
                    if settingsOpen == False:
                        if fileNavEnabled:
                            fileNavEnabled = False
                        sidebarNavMode = not sidebarNavMode
                        downloaderFocused = False
                elif key.lower() == "s":
                    settingsOpen = not settingsOpen
                    sidebarNavMode = False
                    downloaderFocused = False
                elif key.lower() == "d":
                    downloaderFocused = not downloaderFocused
                    sidebarNavMode = False
                    fileNavEnabled = False
                elif key.lower() == " ": # Space bar -> Plays song
                    if player.song is not None: # Song active toggle pause
                        player.toggle_pause()
                        playingSong = not player.paused
                    elif currentSong is not None and currentSong.local_path: # Opening from local path
                        try:
                            player.play(currentSong)
                            playingSong = True
                        except Exception as e:
                            debugPrint.add(f"play failed: {e}")
                            playingSong = False
                elif key.name == "KEY_UP":
                    if settingsOpen:
                        if settingsIndex > 0:
                            settingsIndex -= 1
                    else:
                        if fileNavEnabled and footerOpen:
                            if fileNavIndex > 0:
                                fileNavIndex -= 1

                            update_file_nav_scroll()

                        elif sidebarNavMode:
                            
                            if sidebarNavMode_I > 0:
                                sidebarNavMode_I -= 1
                            update_playlist_scroll(height)

                        else:
                            if volume < 100:
                                volume += 5
                                player.set_volume(volume / 100)

                elif key.name == "KEY_DOWN":
                    if settingsOpen:
                        if settingsIndex < 20:
                            settingsIndex += 1
                    else:
                        if fileNavEnabled and footerOpen:
                            if fileNavIndex < len(fileNavItems) - 1:
                                fileNavIndex += 1

                            update_file_nav_scroll()

                        elif sidebarNavMode:
                            if sidebarNavMode_I < len(playlistData) - 1:
                                sidebarNavMode_I += 1
                            update_playlist_scroll(height)
                            

                        else:
                            if volume > 0:
                                volume -= 5
                                player.set_volume(volume / 100)
                elif key.name == "KEY_LEFT":
                    if fileNavEnabled:
                        parent = os.path.dirname(fileNavPath)
                        if parent != fileNavPath:
                            fileNavPath = parent
                            fileNavScroll = 0
                            fileNavIndex = 0
                            refresh_file_nav()

                elif key.name == "KEY_RIGHT":
                    if fileNavEnabled and fileNavItems:
                        selected = fileNavItems[fileNavIndex]
                        
                        if selected["type"] == "folder":
                            fileNavPath = selected["path"]
                            fileNavIndex = 0
                            fileNavScroll = 0
                            refresh_file_nav()
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
                        elif fileNavEnabled and fileNavItems:
                            selected = fileNavItems[fileNavIndex]

                            if selected["type"] == "folder":
                                folderData = get_folder_data(selected["path"])
                                debugPrint.add(f"importing {selected['name']}")
                                next_index = next_playlist_index()
                                for song in folderData.values():
                                    playlistData[next_index] = song
                                    next_index += 1
                                debugPrint.add(f"len of playlistdata {len(playlistData)} ")
                            elif selected["type"] == "song":
                                song = get_song_data(selected["path"])
                                playlistData[next_playlist_index()] = song
                                debugPrint.add(f"added song {song.title}")

# other functions


# Since we will be using the Song object from downloader i wont pass in duration in formatted form so i will add formatter here. -Ryan
# yep thats fine -Mat
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
        debugPrint.add(
            f"downloaded: {song.title} | {song.channel} | {song.local_path}"
        )
        if player.song is None:
            try:
                currentSong = song
                player.play(song)
                playingSong = True
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

def update_file_nav_scroll():
    global fileNavScroll, fileNavIndex

    visibleItems = 5 # 5 to have better scrolling (prioritizing the visibility of upcoming folders)

    if fileNavIndex < fileNavScroll:
        fileNavScroll = fileNavIndex

    elif fileNavIndex >= fileNavScroll + visibleItems:
        fileNavScroll = fileNavIndex - visibleItems + 1

def update_playlist_scroll(height): # unfortunately couldnt get it to render it based on the terminal height
    global max_visible_songs, sidebarNavMode_I, sidebarScrollOffset

    max_visible_songs = 15 if footerOpen else 25

    max_scroll = max(0, len(playlistData) - max_visible_songs)

    if sidebarNavMode_I < sidebarScrollOffset:
        sidebarScrollOffset = sidebarNavMode_I

    elif sidebarNavMode_I >= sidebarScrollOffset + max_visible_songs:
        sidebarScrollOffset = sidebarNavMode_I - max_visible_songs + 1

    sidebarScrollOffset = max(0, min(sidebarScrollOffset, max_scroll))
def refresh_file_nav():
    global fileNavItems, fileNavIndex, fileNavPath

    fileNavItems = []

    try:
        entries = os.listdir(fileNavPath)

        folders = []
        songs = []

        for entry in entries:
            fullPath = os.path.join(fileNavPath, entry)

            if os.path.isdir(fullPath):
                folders.append({"name": entry,"path": fullPath,"type": "folder"})

            elif fileNavShowSongs and entry.lower().endswith((".mp3", ".wav", ".flac", ".ogg", ".m4a", ".opus", ".webm")):
                songs.append({"name": entry,"path": fullPath,"type": "song"})

        folders.sort(key=lambda x: x["name"].lower())
        songs.sort(key=lambda x: x["name"].lower())

        fileNavItems = folders + songs

        if fileNavItems:
            fileNavIndex = min(fileNavIndex, len(fileNavItems) - 1)
        else:
            fileNavIndex = 0

    except PermissionError:
        fileNavItems = []



refresh_file_nav()
player = Player() # Player object should be accessible by keyboard worker so I created here and will pass it to keyboardworker as an argument -Ryan
player.set_volume(volume / 100)
spectrum = Spectrum(n_bars=32, fft_size=2048, floor_db=-90.0, attack=0.55, decay=0.12)
keyboardThread = threading.Thread(target=keyboard_worker, args=(player,), daemon=True)
keyboardThread.start()

try:
    with Live(console=console, refresh_per_second=10, screen=True,vertical_overflow='crop') as live:
        while running:

            count += 1
            if count >= 500:
                count = 0
            size = console.size
            
            width = size.width
            
            height = size.height
            autoplay(player)
            layout = create_layout(width, height, count, player, spectrum)
            live.update(layout, refresh=True)


except KeyboardInterrupt:
    running = False  # let keyboard_worker leave inkey loop and exit term.cbreak() without this after quitting my terminal would be messed up and I would have to reset it. -Ryan
    player.close()
    keyboardThread.join(timeout=1.0) # This fully waits for the keyboard thread to exit before exiting the program. -Ryan
    # uncomment this for debugprint after exit
    # for x in debugPrint: 
    #     print(x)

    print("CLIP3 exited successfully")
    raise SystemExit(0)