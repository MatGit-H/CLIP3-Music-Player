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

footerOpen = True
settingsOpen = False
playingSong = False
sidebarNavMode = False
sidebarNavMode_I = 1
currentSong = {}
debugPrint = set()

volume = 50
playlistData = dict()
def create_layout(width, height, count):
    global footerOpen, volume, settingsIndex, downloaderTextBox, currentStyle, settingsIndex, sidebarNavMode, running, sidebarNavMode_I, currentSong, playlistData, debugPrint, settingsOpen, playingSong, audioVis, fileNavScroll, fileNavPath
    layout = Layout()
    if settingsOpen:
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body", ratio=1),
        )
        layout["body"].split_row(
            Layout(name="settings", ratio=3),
            Layout(name="info", ratio=2)
        )
        # HEADER (SETTINGS MENU) -------------------------------------------------------------------------------
        header = Table.grid(expand=True)
        header.add_column(justify='left')
        header.add_column(justify="center")
        header.add_column(justify="right")
        hRow = []
        hRow.append("♫ [bold red]CLIP3 [bold white]Music Player ♫     (SETTINGS/INFO)")
        hRow.append("(S) ⚙/🛈  ")
        max_width = 20
        filled = int((volume/100)*max_width)
        empty = max_width - filled

        hRow.append(f'🔊 [{'▓'*filled +'░'*empty}]')
        header.add_row(*hRow)

        layout["header"].update(
            Panel(header, box=currentStyle)
        )
        # SETTINGS MENU ---------------------------------------------------------------------------------------------------
        

        # if settingsIndex == 0:
        #     currentStyle = box.ROUNDED
        # elif settingsIndex == 1:
        #     currentStyle = box.ASCII
        # elif settingsIndex == 2:
        #     currentStyle = box.DOUBLE
        # elif settingsIndex == 3:
        #     currentStyle = box.MARKDOWN
        # elif settingsIndex == 4:
        #     currentStyle = box.HEAVY
        # elif settingsIndex == 5:
        #     currentStyle = box.MINIMAL_HEAVY_HEAD
        # elif settingsIndex == 6:
        #     currentStyle = box.SIMPLE_HEAAD
        # elif settingsIndex == 7:
        #     currentStyle = box.HORIZONTALS
        contentData = [
            Align.left("Settings Here: (placeholder)\n\n"),
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
        # INFO MENU ------------------------------------------------------------------------------------------------------

        content = Group(
            
            Align.center("\n\n IN NORMAL MODE: ARROW KEYS FOR VOLUME (top right) \n\n"),
            Align.center("\n\n IN NORMAL MODE: [B] FOR BOTTOM BAR TOGGLE \n\n"),
            Align.center("\n\n IN NORMAL MODE: [SPACE] FOR PLAYING SONG \n\n"),
            Align.center("\n\n SIDEBAR NAV MODE: PRESS [N] "),
            Align.center("\nARROW KEYS TO MOVE AROUND, ENTER TO SELECT SONG \n")
            
        )

        layout["info"].update(
            Panel(content,box=currentStyle)
        )

        return layout
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
        max_width = int(width * 0.3)

        filled = int((0 / 700) * max_width)
        empty = max_width - filled

        progressbar = '▓'*filled +'.'*empty




        audioVis = []


        # random audio vis for placeholder, ryan feel free to delete this when implementing your visualizaiton
        audioVis.append("[                                                    ]")
        audioVis.append("[                                                    ]")
        audioVis.append("[                                                    ]")
        audioVis.append("[                                                    ]")
        audioVis.append("[                                                    ]")
        audioVis.append("[                                                    ]")
        audioVis.append("[                                                    ]")
        audioVis.append("[                                                    ]")
        audioVis.append("[                                                    ]")
        audioVis.append("[                                                    ]")
        audioVis.append("[                                                    ]")
        audioVis.append("[                                                    ]")
        audioVis.append("[                   AUDIO VIS HERE                   ]")
        audioVis.append("[                                                    ]")
        audioVis.append("[                                                    ]")
        audioVis.append("[                                                    ]")
        audioVis.append("[                                                    ]")
        audioVis.append("[                                                    ]")
        audioVis.append("[                                                    ]")

        if len(currentSong) < 2:
            songText = "Not Playing Any Song"
            songArtist = "N/A"
            songTime = "N/A"
        else:
            songText = list(currentSong)[0]
            songArtist = list(currentSong)[1]
            songTime = list(currentSong)[2]

        playingIcon = "►" if playingSong else "❚❚"
        content = Group(
            
            Align.center(Group(*audioVis)),
            Align.center(Text(f"{songText}", style="bold white")),
            Align.center(Text(f"{songArtist}", style="grey50")),
            # Align.left(Text(f"{playingIcon}", style="bold white")),
            Align.left(Text(f"{playingIcon} {songTime}", style="bold white")),
            Align.center(Text(f'{progressbar}\n')),
        )
        layout["player"].update(
            Panel(Align.center(content, vertical="bottom"),box=currentStyle))

        # Sidebar Content =================================================================================
        
        # playlist data is {index: (title, artistname, time)}

        contentData = []
        # Header for playlist
        contentData.append(Align.left(f'{fileNavPath}\n', style='grey50'),)
        contentData.append(Align.center(f'[bold italic white on grey50]#   Title       Artist       Time\n'))
        # playlist dict
        
        # 
        # if len(currentSong) < 2:
        #     currentSong = list(playlistData.values())[0] # ---------------------- <
        #
        #    Align.center(f'[black on light_green]>>> 2 - Testsong1 - ArtistName 3:39 ', style='white'),
        for index, (title, artistname, time) in playlistData.items():
            if len(title) > 18:
                displayTitle = title[:18]+'..'
            else:
                displayTitle = title
            
            if index >= len(playlistData.values()):
                pass
            # CLEAR PLAYLIST

            if sidebarNavMode:
                if index == sidebarNavMode_I:
                    if (title, artistname, time) == currentSong:
                        if playingSong == True:
                            contentData.append(Align.center(f'[white on black][black on light_green][►]  {index} - {displayTitle} - {artistname} - {time}  \n'))
                        else:
                            contentData.append(Align.center(f'[white on black][black on yellow1][||]  {index} - {displayTitle} - {artistname} - {time}  \n'))
                    else:
                        contentData.append(Align.center(f'[black on white]{index} - {displayTitle} - {artistname} - {time}  \n'))
                    
                else:
                    if (title, artistname, time) == currentSong:
                        if playingSong == True:
                            contentData.append(Align.center(f'[black on light_green][►] {index} - {displayTitle} - {artistname} - {time}\n'))
                        else:
                            contentData.append(Align.center(f'[black on yellow1][||]  {index} - {displayTitle} - {artistname} - {time}\n'))
                    else:
                        contentData.append(Align.center(f'{index} - {displayTitle} - {artistname} - {time}\n', style='bold white'))
            else:
                if (title, artistname, time) == currentSong:
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
                Align.left(f'Enter URL to Download: {downloaderTextBox}')
            )

            layout["download"].update(Panel(content, box=currentStyle,title=f"{'[black on white]-=-=- Downloader (D) -=-=-' if downloaderFocused else 'Downloader (D)'}"))



            layout["filenav"].update(
                Panel(render_file_nav(),box=currentStyle,title=f"{'[black on white]=-=- File Navigation (K) -=-=' if fileNavEnabled else 'File Navigation (K)'}"))


        return layout

def get_folder_data(folder_path):
    playlist = {}

    supported = (".mp3", ".wav", ".flac", ".ogg", ".m4a", ".opus")

    try:
        filenames = sorted(os.listdir(folder_path))
    except:
        debugPrint.add("something went wrong in get_folder_data")

    for filename in filenames:
        filepath = os.path.join(folder_path, filename)

        if not os.path.isfile(filepath):
            continue

        if not filename.lower().endswith(supported):
            continue # ends

        title = os.path.splitext(filename)[0]
        artist = "N/A"
        duration = "0:00"

        try:
            audio = File(filepath, easy=True)

            if audio:
                title = audio.get("title", [title])[0] or title
                artist = audio.get("artist", ["N/A"])[0] or "N/A"

                if audio.info:
                    seconds = int(audio.info.length)
                    duration = f"{seconds // 60}:{seconds % 60:02d}"

        except Exception as e:
            debugPrint.add(f"Error reading {filename}: {e}")

        playlist[len(playlist)] = (title, artist, duration)

    return playlist
def get_song_data(filepath):
    filename = os.path.splitext(os.path.basename(filepath))[0]

    title = filename
    artist = "N/A"
    duration = "0:00"

    try:
        audio = File(filepath, easy=True)

        if audio:
            title = audio.get("title", [title])[0] or title
            artist = audio.get("artist", ["N/A"])[0] or "N/A"

            if audio.info:
                seconds = int(audio.info.length)
                duration = f"{seconds // 60}:{seconds % 60:02d}"

    except Exception as e:
        debugPrint.add(f"Error reading {filename}: {e}")

    return (title, artist, duration)
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
def keyboard_worker():
    global running, footerOpen, volume, sidebarNavMode, sidebarNavMode_I, playlistData, currentSong, debugPrint, settingsOpen, playingSong, fileNavScroll
    global fileNavPath, fileNavItems, fileNavIndex, fileNavEnabled, currentStyle, downloaderFocused, downloaderTextBox
    global fileNavShowSongs, settingsIndex
    with term.cbreak():
        while running:
            key = term.inkey(timeout=0.1)
            
            if not key:
                continue
            if downloaderFocused:
                if key.name == "KEY_ESCAPE":
                    downloaderFocused = False
                elif key.name == "BRACKETED_PASTE":
                    pasted_content = key.text
                    downloaderTextBox += pasted_content
                else:
                    downloaderTextBox += key.lower()
            else:       
                if key.lower() == "b":
                    footerOpen = not footerOpen
                elif key.lower() == "i":
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
                elif key.lower() == " ":
                    playingSong = not playingSong
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
                            sidebarNavMode_I -= 1

                        else:
                            if volume < 100:
                                volume += 5

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
                            sidebarNavMode_I += 1

                        else:
                            if volume > 0:
                                volume -= 5
                elif key.name == "KEY_LEFT":
                    if fileNavEnabled:
                        parent = os.path.dirname(fileNavPath)
                        refresh_file_nav()
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
                        if sidebarNavMode:
                            playingSong = True
                            currentSong = playlistData[sidebarNavMode_I]
                        
                        elif fileNavEnabled and fileNavItems:
                            selected = fileNavItems[fileNavIndex]

                            if selected["type"] == "folder":
                                folderData = get_folder_data(selected["path"])
                                debugPrint.add(f"importing {selected['name']}")
                                next_index = max(playlistData.keys(), default=0) + 1

                                for song in folderData.values():
                                    playlistData[next_index] = (song[0],song[1],song[2])
                                    next_index += 1

                                debugPrint.add(f"len of playlistdata {len(playlistData)} ")
                            elif selected["type"] == "song":
                                song = get_song_data(selected["path"])
                                next_index = max(playlistData.keys(), default=0) + 1
                                playlistData[next_index] = song
                                debugPrint.add(f"added song {song[0]} (please work)")

def update_file_nav_scroll():
    global fileNavScroll, fileNavIndex

    visibleItems = 5 # 5 to have better scrolling (prioritizing the visibility of upcoming folders)

    if fileNavIndex < fileNavScroll:
        fileNavScroll = fileNavIndex

    elif fileNavIndex >= fileNavScroll + visibleItems:
        fileNavScroll = fileNavIndex - visibleItems + 1
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

            elif fileNavShowSongs and entry.lower().endswith((".mp3", ".wav", ".flac", ".ogg", ".m4a",'.opus')):
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
keyboardThread = threading.Thread(target=keyboard_worker,daemon=True)
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
            
            layout = create_layout(width, height,count)
            live.update(layout, refresh=True)


except KeyboardInterrupt:
    for x in debugPrint:
        print(x)
    print("CLIP3 exited successfully")
    exit(0)