# MM ZenMusic Tool
### Misfit Mercenaries — DayZ Cassette Tape Manager

A command-line tool for managing custom cassette tapes for the [Zen's Music](https://steamcommunity.com/sharedfiles/filedetails/?id=3412251200) DayZ mod. Add new tapes, download audio directly from YouTube, convert to OGG, check for duplicates, and export a ready-to-pack `config.cpp` — all from one menu.

---

## Features

- **Add tapes** individually or in bulk via CSV
- **Download audio from YouTube** automatically using `yt-dlp`
- **Convert to OGG** at the correct format for DayZ using `ffmpeg`
- **Auto-fetches duration** from YouTube so you don't have to time tracks manually
- **Duplicate detection** — catches same YouTube URL or similar song names
- **Renumbers OGG files** automatically when you delete a slot
- **Exports `config.cpp`** with all three required sections (`CfgVehicles`, `CfgSoundShaders`, `CfgSoundSets`) in sync

---

## Requirements

**Python 3.7+**

Install the Python dependency:
```
pip install yt-dlp
```

Install ffmpeg and add it to your PATH:
- **Windows:** `winget install ffmpeg` (then restart your terminal)
- **Linux/macOS:** `sudo apt install ffmpeg` / `brew install ffmpeg`

---

## Setup

1. Clone or download this repo
2. Place `mm_music_tool.py` next to your `MMMusic` mod folder:

```
your_folder/
├── mm_music_tool.py
├── mm_songs.json          ← created automatically on first run
└── MMMusic/
    ├── config.cpp
    └── data/
        ├── song1.ogg
        ├── song2.ogg
        └── ...
```

3. Run the tool:
```
python mm_music_tool.py
```

---

## Menu Options

```
1.  List all cassettes
2.  Add new cassette
3.  Bulk import from CSV
4.  Generate blank CSV template
5.  Edit existing cassette
6.  Remove cassette
7.  Check for duplicates
8.  Download one track from YouTube
9.  Download all missing tracks
10. OGG file status
11. Export config.cpp
12. Quit
```

### Adding a single tape
Choose **option 2**. Enter the display name, description, and a YouTube URL. The tool fetches the duration automatically and asks if you want to download the track immediately.

### Bulk importing from a CSV
Choose **option 4** first to generate a blank `mm_bulk_import.csv` template, then fill it out:

```csv
name,desc,dur,yt
Pantera - Walk,Hell yeah,,https://www.youtube.com/watch?v=...
Slayer - Raining Blood,Hell yeah,,https://www.youtube.com/watch?v=...
Tool - Sober,Hell yeah,285,
```

- Leave `dur` blank if you have a YouTube URL — duration is fetched automatically
- Leave `yt` blank if you're providing the OGG file yourself — fill in `dur` manually
- Lines starting with `#` are treated as comments and ignored

Then choose **option 3** to import. The tool previews all tracks before committing, fetches missing durations, and offers to download everything in one go.

### Downloading tracks
- **Option 8** — download or re-download a single slot. If no YouTube URL is set, it will ask for one.
- **Option 9** — batch downloads all slots that have a YouTube URL but no OGG file yet.

Audio is downloaded at best available quality and converted to OGG (Vorbis, quality 6, 44.1kHz stereo).

### Checking for duplicates
**Option 7** runs two checks:
- **Same YouTube video ID** — catches duplicate URLs even if formatted differently
- **Similar display names** — normalises and compares names to catch things like "Metallica - One" listed twice

### Removing a tape
**Option 6** removes the slot and automatically renumbers all OGG files on disk to keep slots contiguous (e.g. removing slot 10 renames `song11.ogg → song10.ogg`, `song12.ogg → song11.ogg`, etc.), then regenerates `config.cpp`.

### Exporting config.cpp
**Option 11** (or triggered automatically after most edits) writes a fresh `config.cpp` to `MMMusic/config.cpp` with all class definitions in sync.

---

## File Structure

Your song list is saved to `mm_songs.json` alongside the script. Each entry stores:

| Field | Description |
|-------|-------------|
| `name` | Display name shown in-game on the cassette |
| `desc` | Short description shown in-game |
| `dur` | Track duration in seconds (used for `playSeconds`) |
| `yt` | YouTube URL (stored as a comment in config.cpp, used for downloading) |

OGG files are stored as `MMMusic/data/song1.ogg`, `song2.ogg`, etc. Slot number = file number = class number, so they must stay in sync. The tool handles this automatically.

---

## Packing the Mod

After adding your tapes and exporting `config.cpp`, pack your mod as normal using the DayZ Tools addon builder. Make sure your file list includes `*.ogg`.

---

## Notes

- This tool is built for the **Misfit Mercenaries** server but works with any ZenMusic mod setup — just adjust the class prefix in the script if needed (`MM_Cassette_Song` → your prefix)
- YouTube downloading is for personal/server use. Respect copyright and only use tracks you have rights to
- The tool requires an internet connection to fetch durations and download tracks
