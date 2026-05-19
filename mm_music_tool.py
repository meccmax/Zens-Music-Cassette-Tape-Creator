#!/usr/bin/env python3
"""
MM ZenMusic Tool — Misfit Mercenaries
Manages cassette tapes for the Zen's Music DayZ mod.
Downloads YouTube tracks, converts to OGG, and generates config.cpp.

Requirements:
    pip install yt-dlp
    ffmpeg must be installed and on PATH (https://ffmpeg.org/download.html)

Usage:
    python mm_music_tool.py
"""

import csv
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap

# ── paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
MOD_DIR     = os.path.join(SCRIPT_DIR, "MMMusic")
DATA_DIR    = os.path.join(MOD_DIR, "data")
CONFIG_CPP  = os.path.join(MOD_DIR, "config.cpp")
STATE_FILE  = os.path.join(SCRIPT_DIR, "mm_songs.json")

# ── initial song list (your existing 50) ──────────────────────────────────────
DEFAULT_SONGS = [
    {"name": "Metallica - Wherever I May Roam",                  "desc": "From the Black Album.", "dur": 404, "yt": ""},
    {"name": "Metallica - The Unforgiven",                        "desc": "From the Black Album.", "dur": 387, "yt": ""},
    {"name": "Cheap Trick - I Want You To Want Me",               "desc": "Hell yeah",             "dur": 217, "yt": ""},
    {"name": "White Zombie - Thunder Kiss 65",                    "desc": "Hell yeah",             "dur": 238, "yt": ""},
    {"name": "Dire Straits - Sultans of Swing",                   "desc": "Hell yeah",             "dur": 346, "yt": ""},
    {"name": "Ghost - Square Hammer",                             "desc": "Hell yeah",             "dur": 240, "yt": ""},
    {"name": "The Prodigy - Smack My Bitch Up",                   "desc": "Hell yeah",             "dur": 343, "yt": ""},
    {"name": "Oliver Tree - Cowboys Don't Cry",                   "desc": "Hell yeah",             "dur": 190, "yt": ""},
    {"name": "Foo Fighters - Monkey Wrench",                      "desc": "Hell yeah",             "dur": 231, "yt": ""},
    {"name": "Korn - Falling Away From Me",                       "desc": "Hell yeah",             "dur": 291, "yt": ""},
    {"name": "Static-X - Love Dump",                              "desc": "Hell yeah",             "dur": 260, "yt": ""},
    {"name": "Metallica - One",                                   "desc": "Hell yeah",             "dur": 446, "yt": ""},
    {"name": "Audioslave - Cochise",                              "desc": "Hell yeah",             "dur": 222, "yt": ""},
    {"name": "Dr.Dre - Nuthin' But A G Thang",                    "desc": "Hell yeah",             "dur": 238, "yt": ""},
    {"name": "Alice in Chains - Dirt",                            "desc": "Hell yeah",             "dur": 317, "yt": ""},
    {"name": "The Misfits - Scream!",                             "desc": "Hell yeah",             "dur": 154, "yt": ""},
    {"name": "Metallica - No Leaf Clover (S&M)",                  "desc": "Hell yeah",             "dur": 343, "yt": ""},
    {"name": "Static-X - Wisconsin Death Trip",                   "desc": "Hell yeah",             "dur": 189, "yt": ""},
    {"name": "Dire Straits - Money for Nothing",                  "desc": "Hell yeah",             "dur": 246, "yt": ""},
    {"name": "Metallica - Bleeding Me (S&M)",                     "desc": "Hell yeah",             "dur": 542, "yt": ""},
    {"name": "The Offspring - Want you Bad",                      "desc": "Hell yeah",             "dur": 202, "yt": ""},
    {"name": "Alice in Chains - Down in a Hole",                  "desc": "Hell yeah",             "dur": 338, "yt": ""},
    {"name": "The Misfits - Decending Angel",                     "desc": "Hell yeah",             "dur": 226, "yt": ""},
    {"name": "Alice in Chains - Would?",                          "desc": "Hell yeah",             "dur": 217, "yt": ""},
    {"name": "Alice Cooper - Hey Stoopid",                        "desc": "Hell yeah",             "dur": 207, "yt": ""},
    {"name": "Alice Cooper - Feed My Frankenstein",               "desc": "Hell yeah",             "dur": 285, "yt": ""},
    {"name": "Bad Company - Bad Company",                         "desc": "Hell yeah",             "dur": 289, "yt": ""},
    {"name": "Don Henley - Dirty Laundry",                        "desc": "Hell yeah",             "dur": 337, "yt": ""},
    {"name": "Faith No More - We Care a Lot",                     "desc": "Hell yeah",             "dur": 250, "yt": ""},
    {"name": "Genesis - Abacab",                                  "desc": "Hell yeah",             "dur": 424, "yt": ""},
    {"name": "Genesis - Land of Confusion",                       "desc": "Hell yeah",             "dur": 286, "yt": ""},
    {"name": "Genesis - Domino Medley",                           "desc": "Hell yeah",             "dur": 645, "yt": ""},
    {"name": "Ice Cube - Gangsta Rap Made Me Do It",              "desc": "Hell yeah",             "dur": 282, "yt": ""},
    {"name": "Metallica - Wasting My Hate",                       "desc": "Hell yeah",             "dur": 238, "yt": ""},
    {"name": "Pantera - Walk",                                    "desc": "Hell yeah",             "dur": 315, "yt": ""},
    {"name": "Red Hot Chili Peppers - Scar Tissue",               "desc": "Hell yeah",             "dur": 218, "yt": ""},
    {"name": "Gorillaz - Tomorrow Comes Today",                   "desc": "Hell yeah",             "dur": 193, "yt": ""},
    {"name": "Gorillaz - Starshine",                              "desc": "Hell yeah",             "dur": 211, "yt": ""},
    {"name": "Gorillaz - Plastic Beach",                          "desc": "Hell yeah",             "dur": 249, "yt": ""},
    {"name": "Soundgarden - Slaves & Bulldozers",                 "desc": "Hell yeah",             "dur": 419, "yt": ""},
    {"name": "Soundgarden - Jesus Christ Pose",                   "desc": "Hell yeah",             "dur": 354, "yt": ""},
    {"name": "Soundgarden - Searching with my Good Eye Closed",   "desc": "Hell yeah",             "dur": 392, "yt": ""},
    {"name": "Soundgarden - Room a Thousand Years Wide",          "desc": "Hell yeah",             "dur": 247, "yt": ""},
    {"name": "System of a Down - Kill Rock 'n Roll",              "desc": "Hell yeah",             "dur": 148, "yt": ""},
    {"name": "System of a Down - Stealing Society",               "desc": "Hell yeah",             "dur": 178, "yt": ""},
    {"name": "System of a Down - Cigaro",                         "desc": "Hell yeah",             "dur": 131, "yt": ""},
    {"name": "System of a Down - Sad Statue",                     "desc": "Hell yeah",             "dur": 203, "yt": ""},
    {"name": "System of a Down - Old School Hollywood",           "desc": "Hell yeah",             "dur": 176, "yt": ""},
    {"name": "ZZ Top - Legs",                                     "desc": "Hell yeah",             "dur": 274, "yt": ""},
    {"name": "ZZ Top - TV Dinners",                               "desc": "Hell yeah",             "dur": 239, "yt": ""},
]

# ── helpers ────────────────────────────────────────────────────────────────────

def clr(code, text): return f"\033[{code}m{text}\033[0m"
def green(t):  return clr("32", t)
def yellow(t): return clr("33", t)
def red(t):    return clr("31", t)
def bold(t):   return clr("1",  t)
def dim(t):    return clr("2",  t)

def fmt_dur(s):
    return f"{s//60}:{s%60:02d}"

def check_deps():
    ok = True
    if not shutil.which("ffmpeg"):
        print(red("✗ ffmpeg not found. Install from https://ffmpeg.org/download.html and add to PATH."))
        ok = False
    try:
        import yt_dlp  # noqa: F401
    except ImportError:
        print(red("✗ yt-dlp not installed. Run: pip install yt-dlp"))
        ok = False
    return ok

def load_songs():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return [dict(s) for s in DEFAULT_SONGS]

def save_songs(songs):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(songs, f, indent=2, ensure_ascii=False)

def ogg_path(slot):
    return os.path.join(DATA_DIR, f"song{slot}.ogg")

def ogg_exists(slot):
    return os.path.isfile(ogg_path(slot))

# ── config.cpp generation ──────────────────────────────────────────────────────

def generate_config(songs):
    lines = [
        "/*",
        "My Addon Builder Included File List:",
        "*.emat;*.edds;*.ptc;*.c;*.imageset;*.layout;*.ogg;*.paa;*.fnt;*.tga;*.xml;*.csv;*.rvmat;*.map;*.html",
        "*/",
        "",
        "class CfgPatches",
        "{",
        "\tclass MMMusic",
        "\t{",
        "\t\trequiredVersion = 0.1;",
        "\t\trequiredAddons[] =",
        "\t\t{",
        '\t\t\t"DZ_Data",',
        '\t\t\t"ZenMusicBase"',
        "\t\t};",
        "\t};",
        "};",
        "",
        "class CfgVehicles",
        "{",
        "\tclass Zen_Cassette_Base;",
        "",
    ]
    for i, s in enumerate(songs):
        n = i + 1
        if s.get("yt"):
            lines.append(f"\t// YouTube: {s['yt']}")
        lines += [
            f"\tclass MM_Cassette_Song{n} : Zen_Cassette_Base",
            "\t{",
            "\t\tscope = 2;",
            f'\t\tdisplayName = "{s["name"]}";',
            f'\t\tdescriptionShort = "{s["desc"]}";',
            f"\t\tplaySeconds = {s['dur']};",
            "\t};",
        ]
    lines += ["};", "", "class CfgSoundShaders", "{", "\tclass Zen_Cassette_SoundShader_Base;", ""]
    for i, s in enumerate(songs):
        n = i + 1
        lines.append(f'\tclass MM_Cassette_Song{n}_SoundShader : Zen_Cassette_SoundShader_Base {{ samples[] = {{ {{ "MMMusic\\data\\song{n}", 1 }} }}; }};')
    lines += ["};", "", "class CfgSoundSets", "{"]
    for i, s in enumerate(songs):
        n = i + 1
        lines.append(f'\tclass MM_Cassette_Song{n}_SoundSet {{ soundShaders[] = {{ "MM_Cassette_Song{n}_SoundShader" }}; }};')
    lines.append("};")
    return "\r\n".join(lines)

def write_config(songs):
    os.makedirs(MOD_DIR, exist_ok=True)
    with open(CONFIG_CPP, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(generate_config(songs))
    print(green(f"✓ config.cpp written → {CONFIG_CPP}"))

# ── download + convert ─────────────────────────────────────────────────────────

def get_yt_duration(url):
    """Fetch video duration in seconds via yt-dlp without downloading."""
    import yt_dlp
    opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info.get("duration", 0), info.get("title", "")

def download_and_convert(url, slot):
    """Download audio from YouTube URL and convert to OGG at the given slot."""
    import yt_dlp
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp_template = os.path.join(DATA_DIR, f"_tmp_song{slot}.%(ext)s")
    out_path = ogg_path(slot)

    print(yellow(f"  ↓ Downloading audio…"))
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": tmp_template,
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        downloaded_file = ydl.prepare_filename(info)

    if not os.path.exists(downloaded_file):
        # yt-dlp sometimes changes extension — find it
        base = os.path.join(DATA_DIR, f"_tmp_song{slot}.")
        candidates = [f for f in os.listdir(DATA_DIR) if f.startswith(f"_tmp_song{slot}.")]
        if not candidates:
            raise FileNotFoundError("Downloaded file not found.")
        downloaded_file = os.path.join(DATA_DIR, candidates[0])

    print(yellow(f"  ⚙ Converting to OGG (quality 6)…"))
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", downloaded_file,
         "-c:a", "libvorbis", "-q:a", "6",
         "-ar", "44100", "-ac", "2",
         out_path],
        capture_output=True, text=True
    )
    os.remove(downloaded_file)

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg error:\n{result.stderr[-500:]}")

    size_mb = os.path.getsize(out_path) / 1_048_576
    print(green(f"  ✓ Saved → {out_path} ({size_mb:.1f} MB)"))
    return out_path

# ── UI helpers ─────────────────────────────────────────────────────────────────

def prompt(msg, default=""):
    try:
        val = input(f"  {msg}" + (f" [{default}]" if default else "") + ": ").strip()
        return val if val else default
    except (KeyboardInterrupt, EOFError):
        print()
        return default

def pause():
    try:
        input(dim("  Press Enter to continue…"))
    except (KeyboardInterrupt, EOFError):
        pass

def print_header():
    print()
    print(bold("╔══════════════════════════════════════════════════╗"))
    print(bold("║     MM ZenMusic Tool — Misfit Mercenaries        ║"))
    print(bold("╚══════════════════════════════════════════════════╝"))
    print()

def list_songs(songs):
    print()
    total = sum(s["dur"] for s in songs)
    print(bold(f"  {'#':>3}  {'Song':<52}  {'Dur':>6}  OGG"))
    print("  " + "─" * 72)
    for i, s in enumerate(songs):
        slot = i + 1
        exists = "✓" if ogg_exists(slot) else dim("✗")
        yt_tag = " [YT]" if s.get("yt") else ""
        name = (s["name"] + yt_tag)[:52]
        dur = fmt_dur(s["dur"])
        print(f"  {slot:>3}  {name:<52}  {dur:>6}  {exists}")
    print("  " + "─" * 72)
    print(f"  {len(songs)} tapes  ·  total {fmt_dur(total)}")
    print()

# ── actions ────────────────────────────────────────────────────────────────────

def action_list(songs):
    list_songs(songs)
    pause()

def action_add(songs):
    print()
    print(bold("  Add new cassette"))
    print()
    name = prompt("Display name (Artist - Song title)")
    if not name:
        print(red("  Cancelled."))
        return songs

    desc = prompt("Description (in-game text)", "Hell yeah")
    yt   = prompt("YouTube URL (leave blank to skip download)")

    dur = 0
    if yt:
        print(yellow("  Fetching duration from YouTube…"))
        try:
            dur, yt_title = get_yt_duration(yt)
            print(green(f"  ✓ Found: {yt_title} ({fmt_dur(dur)})"))
            if not name:
                name = yt_title
        except Exception as e:
            print(red(f"  Could not fetch duration: {e}"))

    if not dur:
        raw = prompt("Duration in seconds", "240")
        try:
            dur = int(raw)
        except ValueError:
            dur = 240

    songs.append({"name": name, "desc": desc, "dur": dur, "yt": yt})
    slot = len(songs)
    save_songs(songs)
    print(green(f"  ✓ Added as slot {slot} (song{slot}.ogg)"))

    if yt:
        do_dl = prompt("Download & convert now? (y/n)", "y").lower()
        if do_dl == "y":
            try:
                download_and_convert(yt, slot)
                # update duration from actual file
                result = subprocess.run(
                    ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                     "-of", "default=noprint_wrappers=1:nokey=1", ogg_path(slot)],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    actual_dur = round(float(result.stdout.strip()))
                    songs[-1]["dur"] = actual_dur
                    save_songs(songs)
                    print(green(f"  ✓ Duration updated to {fmt_dur(actual_dur)} from file"))
            except Exception as e:
                print(red(f"  Download failed: {e}"))
        write_config(songs)

    return songs

def action_download_missing(songs):
    print()
    missing = [(i+1, s) for i, s in enumerate(songs) if s.get("yt") and not ogg_exists(i+1)]
    if not missing:
        print(green("  All YouTube-linked slots already have OGG files."))
        pause()
        return songs

    print(bold(f"  {len(missing)} slot(s) missing OGG — have YouTube URLs:"))
    for slot, s in missing:
        print(f"    {slot}. {s['name']}")
    print()
    confirm = prompt(f"Download & convert all {len(missing)}? (y/n)", "y").lower()
    if confirm != "y":
        return songs

    for slot, s in missing:
        print()
        print(bold(f"  [{slot}/{len(songs)}] {s['name']}"))
        try:
            download_and_convert(s["yt"], slot)
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", ogg_path(slot)],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                actual_dur = round(float(result.stdout.strip()))
                songs[slot-1]["dur"] = actual_dur
                print(green(f"  ✓ Duration updated to {fmt_dur(actual_dur)}"))
        except Exception as e:
            print(red(f"  ✗ Failed: {e}"))

    save_songs(songs)
    write_config(songs)
    return songs

def action_download_one(songs):
    list_songs(songs)
    raw = prompt("Enter slot number to download/re-download")
    try:
        slot = int(raw)
        assert 1 <= slot <= len(songs)
    except (ValueError, AssertionError):
        print(red("  Invalid slot."))
        pause()
        return songs

    s = songs[slot - 1]
    if not s.get("yt"):
        yt = prompt("No YouTube URL set. Enter one now (or blank to cancel)")
        if not yt:
            return songs
        s["yt"] = yt
        save_songs(songs)

    print()
    print(bold(f"  Downloading slot {slot}: {s['name']}"))
    try:
        download_and_convert(s["yt"], slot)
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", ogg_path(slot)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            actual_dur = round(float(result.stdout.strip()))
            songs[slot-1]["dur"] = actual_dur
            save_songs(songs)
            print(green(f"  ✓ Duration updated to {fmt_dur(actual_dur)}"))
        write_config(songs)
    except Exception as e:
        print(red(f"  ✗ Failed: {e}"))
    pause()
    return songs

def action_edit(songs):
    list_songs(songs)
    raw = prompt("Enter slot number to edit")
    try:
        slot = int(raw)
        assert 1 <= slot <= len(songs)
    except (ValueError, AssertionError):
        print(red("  Invalid slot."))
        pause()
        return songs

    s = songs[slot - 1]
    print()
    print(bold(f"  Editing slot {slot}"))
    print(dim(f"  Leave blank to keep current value"))
    print()

    new_name = prompt(f"Display name", s["name"])
    new_desc = prompt(f"Description", s["desc"])
    raw_dur  = prompt(f"Duration (seconds)", str(s["dur"]))
    new_yt   = prompt(f"YouTube URL", s.get("yt",""))

    try:
        new_dur = int(raw_dur)
    except ValueError:
        new_dur = s["dur"]

    s["name"] = new_name
    s["desc"] = new_desc
    s["dur"]  = new_dur
    s["yt"]   = new_yt

    save_songs(songs)
    write_config(songs)
    print(green(f"  ✓ Slot {slot} updated."))
    pause()
    return songs

def action_delete(songs):
    list_songs(songs)
    raw = prompt("Enter slot number to remove")
    try:
        slot = int(raw)
        assert 1 <= slot <= len(songs)
    except (ValueError, AssertionError):
        print(red("  Invalid slot."))
        pause()
        return songs

    s = songs[slot - 1]
    confirm = prompt(f"Remove slot {slot} '{s['name']}'? This cannot be undone. (yes/n)", "n")
    if confirm.lower() != "yes":
        print("  Cancelled.")
        pause()
        return songs

    songs.pop(slot - 1)

    # Rename OGG files to keep slots contiguous
    print(yellow("  Renumbering OGG files…"))
    for i in range(slot, len(songs) + 1):
        old = ogg_path(i + 1)
        new = ogg_path(i)
        if os.path.exists(old):
            if os.path.exists(new):
                os.remove(new)
            os.rename(old, new)
            print(dim(f"    song{i+1}.ogg → song{i}.ogg"))

    save_songs(songs)
    write_config(songs)
    print(green(f"  ✓ Slot {slot} removed. {len(songs)} tapes remain."))
    pause()
    return songs

def action_export(songs):
    write_config(songs)
    pause()

def action_status(songs):
    print()
    print(bold("  OGG file status"))
    print()
    missing_yt = []
    missing_no_yt = []
    present = []
    for i, s in enumerate(songs):
        slot = i + 1
        if ogg_exists(slot):
            present.append(slot)
        elif s.get("yt"):
            missing_yt.append((slot, s))
        else:
            missing_no_yt.append((slot, s))

    print(f"  {green(str(len(present)))} OGG files present")
    if missing_yt:
        print(f"  {yellow(str(len(missing_yt)))} missing — have YouTube URL (run 'Download missing')")
        for slot, s in missing_yt:
            print(dim(f"    {slot}. {s['name']}"))
    if missing_no_yt:
        print(f"  {red(str(len(missing_no_yt)))} missing — no YouTube URL set")
        for slot, s in missing_no_yt:
            print(dim(f"    {slot}. {s['name']}"))
    print()
    pause()

# ── bulk import ────────────────────────────────────────────────────────────────

CSV_TEMPLATE = os.path.join(SCRIPT_DIR, "mm_bulk_import.csv")
CSV_HEADERS  = ["name", "desc", "dur", "yt"]
CSV_EXAMPLE  = [
    ["Pantera - Cemetery Gates",   "Hell yeah", "", "https://www.youtube.com/watch?v=J6SJoQFbmAk"],
    ["Slayer - Raining Blood",     "Hell yeah", "", "https://www.youtube.com/watch?v=zJ_GBfzpOaU"],
    ["Nine Inch Nails - Hurt",     "Hell yeah", "", ""],
]

def action_export_template(songs):
    print()
    with open(CSV_TEMPLATE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(CSV_HEADERS)
        w.writerow(["# name: display name shown in-game", "# desc: short description", "# dur: seconds (leave blank to auto-fetch)", "# yt: YouTube URL (leave blank if no download)"])
        for row in CSV_EXAMPLE:
            w.writerow(row)
    print(green(f"  ✓ Template written → {CSV_TEMPLATE}"))
    print(dim(  f"  Fill it out then use 'Bulk import from CSV' to add all tracks at once."))
    print(dim(  f"  Leave 'dur' blank if you have a YouTube URL — duration is fetched automatically."))
    print(dim(  f"  Leave 'yt' blank if you don't want to download (dur must be filled in then)."))
    print()
    pause()

def action_bulk_import(songs):
    print()
    csv_path = prompt("Path to CSV file", CSV_TEMPLATE)
    if not os.path.exists(csv_path):
        print(red(f"  File not found: {csv_path}"))
        pause()
        return songs

    rows = []
    skipped = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):
            name = row.get("name", "").strip()
            if not name or name.startswith("#"):
                continue
            desc = row.get("desc", "Hell yeah").strip() or "Hell yeah"
            yt   = row.get("yt",   "").strip()
            try:
                dur = int(row.get("dur", "").strip())
            except (ValueError, AttributeError):
                dur = 0
            if not dur and not yt:
                skipped.append(f"  row {i}: '{name}' — no duration and no YouTube URL, skipped")
                continue
            rows.append({"name": name, "desc": desc, "dur": dur, "yt": yt})

    if not rows:
        print(red("  No valid rows found in CSV."))
        for s in skipped:
            print(yellow(s))
        pause()
        return songs

    print()
    print(bold(f"  Found {len(rows)} track(s) to import:"))
    for r in rows:
        dur_str = fmt_dur(r["dur"]) if r["dur"] else dim("(fetch from YT)")
        yt_str  = green("YT") if r["yt"] else dim("no URL")
        print(f"    {r['name'][:55]:<55}  {dur_str}  {yt_str}")
    if skipped:
        print()
        print(yellow(f"  {len(skipped)} row(s) skipped:"))
        for s in skipped:
            print(yellow(s))

    print()
    confirm = prompt(f"Add all {len(rows)} to your cassette list? (y/n)", "y").lower()
    if confirm != "y":
        print("  Cancelled.")
        pause()
        return songs

    # Phase 1: fetch missing durations
    needs_dur = [r for r in rows if not r["dur"] and r["yt"]]
    if needs_dur:
        print()
        print(bold(f"  Fetching durations for {len(needs_dur)} track(s)…"))
        for r in needs_dur:
            try:
                dur, _ = get_yt_duration(r["yt"])
                r["dur"] = dur
                print(green(f"  ✓ {r['name'][:50]} → {fmt_dur(dur)}"))
            except Exception as e:
                r["dur"] = 180
                print(yellow(f"  ⚠ {r['name'][:50]} — could not fetch ({e}), defaulting to 3:00"))

    # Phase 2: append to songs list
    start_slot = len(songs) + 1
    for r in rows:
        songs.append({"name": r["name"], "desc": r["desc"], "dur": r["dur"], "yt": r["yt"]})

    save_songs(songs)
    print()
    print(green(f"  ✓ {len(rows)} cassette(s) added (slots {start_slot}–{len(songs)})"))

    # Phase 3: offer to download all YouTube tracks
    has_yt = [(len(songs) - len(rows) + i, r) for i, r in enumerate(rows) if r["yt"]]
    if has_yt:
        print()
        do_dl = prompt(f"Download & convert {len(has_yt)} YouTube track(s) now? (y/n)", "y").lower()
        if do_dl == "y":
            failed = []
            for slot, r in has_yt:
                print()
                print(bold(f"  [{slot}/{len(songs)}] {r['name']}"))
                try:
                    download_and_convert(r["yt"], slot)
                    result = subprocess.run(
                        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                         "-of", "default=noprint_wrappers=1:nokey=1", ogg_path(slot)],
                        capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        actual_dur = round(float(result.stdout.strip()))
                        songs[slot - 1]["dur"] = actual_dur
                        print(green(f"  ✓ Duration updated to {fmt_dur(actual_dur)}"))
                except Exception as e:
                    print(red(f"  ✗ Failed: {e}"))
                    failed.append(r["name"])

            save_songs(songs)
            if failed:
                print()
                print(yellow(f"  {len(failed)} download(s) failed — retry with 'Download one track':"))
                for n in failed:
                    print(yellow(f"    · {n}"))

    write_config(songs)
    pause()
    return songs

# ── main menu ──────────────────────────────────────────────────────────────────


# ── duplicate checker ──────────────────────────────────────────────────────────────────

def _yt_video_id(url):
    """Extract YouTube video ID from a URL, or return None."""
    if not url:
        return None
    m = re.search(r'(?:v=|youtu\.be/|/embed/|/shorts/)([A-Za-z0-9_-]{11})', url)
    return m.group(1) if m else url.strip().lower()

def _norm_name(name):
    """Lowercase + strip punctuation/filler for fuzzy name matching."""
    n = name.lower()
    n = re.sub(r'[^\w\s]', "", n)
    n = re.sub(r'\b(the|a|an|official|audio|video|lyrics?|remastered)\b', "", n)
    n = re.sub(r'\s+', " ", n).strip()
    return n

def action_check_duplicates(songs):
    print()
    print(bold("  Duplicate check"))
    print()

    yt_seen, yt_dupes = {}, []
    for i, s in enumerate(songs):
        vid = _yt_video_id(s.get("yt", ""))
        if not vid:
            continue
        if vid in yt_seen:
            yt_dupes.append((yt_seen[vid] + 1, i + 1, vid,
                             songs[yt_seen[vid]]["name"], s["name"]))
        else:
            yt_seen[vid] = i

    name_seen, name_dupes = {}, []
    for i, s in enumerate(songs):
        key = _norm_name(s["name"])
        if key in name_seen:
            name_dupes.append((name_seen[key] + 1, i + 1,
                               songs[name_seen[key]]["name"], s["name"]))
        else:
            name_seen[key] = i

    any_found = False

    if yt_dupes:
        any_found = True
        print(red(f"  {len(yt_dupes)} duplicate YouTube URL(s):"))
        for slot_a, slot_b, vid, name_a, name_b in yt_dupes:
            print(f"    Slots {slot_a} & {slot_b} point to the same video ({vid})")
            print(dim(f"      {slot_a}: {name_a}"))
            print(dim(f"      {slot_b}: {name_b}"))
        print()

    if name_dupes:
        any_found = True
        print(yellow(f"  {len(name_dupes)} similar name(s) found:"))
        for slot_a, slot_b, name_a, name_b in name_dupes:
            print(f"    Slots {slot_a} & {slot_b} look like the same song")
            print(dim(f"      {slot_a}: {name_a}"))
            print(dim(f"      {slot_b}: {name_b}"))
        print()

    if not any_found:
        print(green("  No duplicates found — all clear!"))
        print()
    else:
        print(dim("  Use 'Remove cassette' to delete any unwanted duplicates."))
        print()

    pause()

MENU = [
    ("List all cassettes",              action_list),
    ("Add new cassette",                action_add),
    ("Bulk import from CSV",            action_bulk_import),
    ("Generate blank CSV template",     action_export_template),
    ("Edit existing cassette",          action_edit),
    ("Remove cassette",                 action_delete),
    ("Check for duplicates",            action_check_duplicates),
    ("Download one track from YouTube", action_download_one),
    ("Download all missing tracks",     action_download_missing),
    ("OGG file status",                 action_status),
    ("Export config.cpp",               action_export),
    ("Quit",                            None),
]

def main():
    if not check_deps():
        sys.exit(1)

    os.makedirs(DATA_DIR, exist_ok=True)
    songs = load_songs()

    while True:
        print_header()
        print(f"  Songs: {bold(str(len(songs)))}  ·  "
              f"OGGs present: {bold(str(sum(1 for i in range(len(songs)) if ogg_exists(i+1))))}")
        print()
        for i, (label, _) in enumerate(MENU):
            print(f"  {dim(str(i+1)+'.')} {label}")
        print()

        raw = prompt("Choose option")
        try:
            choice = int(raw) - 1
            assert 0 <= choice < len(MENU)
        except (ValueError, AssertionError):
            continue

        label, fn = MENU[choice]
        if fn is None:
            print("\n  Bye!\n")
            break

        result = fn(songs)
        if result is not None:
            songs = result

if __name__ == "__main__":
    main()
