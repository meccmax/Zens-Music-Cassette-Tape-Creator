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

# ── default song list (empty — users import their own tracks) ──────────────────────────
DEFAULT_SONGS = []

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

def parse_config_cpp(path):
    """Parse an existing config.cpp and return a list of song dicts."""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    pattern = re.compile(
        r'(?://\s*YouTube:\s*(https?://\S+)\s*\n\s*)?' 
        r'class MM_Cassette_Song(\d+)\s*:\s*Zen_Cassette_Base\s*\{[^}]*?' 
        r'displayName\s*=\s*"([^"]+)"\s*;\s*' 
        r'descriptionShort\s*=\s*"([^"]+)"\s*;\s*' 
        r'playSeconds\s*=\s*(\d+)\s*;',
        re.DOTALL
    )
    songs = []
    for m in pattern.finditer(content):
        songs.append((int(m.group(2)), {
            "name": m.group(3),
            "desc": m.group(4),
            "dur":  int(m.group(5)),
            "yt":   m.group(1) or "",
        }))
    songs.sort(key=lambda x: x[0])
    return [s for _, s in songs]

def load_songs():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    # First run — no json yet
    print()
    print(bold("  No mm_songs.json found — first run setup"))
    print()
    print("  Options:")
    print("  1. Start fresh (empty mod)")
    print("  2. Import from existing config.cpp")
    print()
    choice = prompt("Choose", "1")
    if choice.strip() == "2":
        default_cfg = CONFIG_CPP if os.path.exists(CONFIG_CPP) else ""
        cfg_path = prompt("Path to config.cpp", default_cfg)
        if os.path.exists(cfg_path):
            try:
                songs = parse_config_cpp(cfg_path)
                save_songs(songs)
                print(green(f"  ✓ Imported {len(songs)} songs from config.cpp"))
                return songs
            except Exception as e:
                print(red(f"  ✗ Failed to parse config: {e}"))
                print(yellow("  Starting with empty list instead."))
        else:
            print(yellow("  File not found. Starting with empty list."))
    songs = list(DEFAULT_SONGS)
    save_songs(songs)
    return songs

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

def action_import_config(songs):
    """Import/merge songs from an existing config.cpp into the current list."""
    print()
    if songs:
        print(yellow(f"  Warning: you already have {len(songs)} song(s) loaded."))
        mode = prompt("  (r)eplace all or (a)ppend new songs only", "r").lower()
    else:
        mode = "r"

    default_cfg = CONFIG_CPP if os.path.exists(CONFIG_CPP) else ""
    cfg_path = prompt("Path to config.cpp", default_cfg)
    if not os.path.exists(cfg_path):
        print(red("  File not found."))
        pause()
        return songs

    try:
        imported = parse_config_cpp(cfg_path)
    except Exception as e:
        print(red(f"  Failed to parse config.cpp: {e}"))
        pause()
        return songs

    if not imported:
        print(red("  No songs found in that file."))
        pause()
        return songs

    if mode == "r":
        songs = imported
        print(green(f"  ✓ Replaced with {len(songs)} songs from config.cpp"))
    else:
        existing_names = {s["name"].lower() for s in songs}
        added = [s for s in imported if s["name"].lower() not in existing_names]
        songs.extend(added)
        print(green(f"  ✓ Appended {len(added)} new song(s) ({len(imported) - len(added)} already existed)"))

    save_songs(songs)
    write_config(songs)
    pause()
    return songs

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

def action_bulk_import(songs, csv_path=None):
    print()
    if csv_path is None:
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


# ── build CSV from URL list ──────────────────────────────────────────────────────────────────

URLS_FILE = os.path.join(SCRIPT_DIR, "mm_url_list.txt")
URL_OUT    = os.path.join(SCRIPT_DIR, "mm_bulk_import.csv")

def _clean_yt_title(raw_title):
    """
    Convert a raw YouTube video title into a clean "Artist - Song" display name.
    Strips common suffixes like (Official Video), [Lyrics], etc.
    """
    import re as _re
    # Remove bracketed/parenthesised noise
    cleaned = _re.sub(
        r'[\[\(](?:official\s*(?:music\s*)?(?:video|audio|lyric(?:s)?|4k|hd)?|'
        r'lyrics?|visualizer|ft\.?.*?|feat\.?.*?|remastered.*?|\d{4}.*?)[\]\)]',
        '', raw_title, flags=_re.IGNORECASE
    )
    # Strip trailing punctuation / whitespace
    cleaned = _re.sub(r'[\s\-\|]+$', '', cleaned).strip()
    return cleaned or raw_title.strip()

def action_urls_to_csv(songs):
    import yt_dlp as _ydl
    print()
    print(bold("  Build CSV from YouTube URL list"))
    print()
    print(dim(f"  Put one YouTube URL per line in a text file."))
    print(dim(f"  Default location: {URLS_FILE}"))
    print()

    url_path = prompt("Path to URL list file", URLS_FILE)
    if not os.path.exists(url_path):
        # Offer to create it
        create = prompt(f"File not found. Create it at {url_path}? (y/n)", "y").lower()
        if create == "y":
            with open(url_path, "w", encoding="utf-8") as f:
                f.write("# Paste one YouTube URL per line. Lines starting with # are ignored.\n")
            print(green(f"  \u2713 Created {url_path} — add your URLs then run this option again."))
        pause()
        return songs

    with open(url_path, "r", encoding="utf-8") as f:
        raw_lines = f.readlines()

    urls = []
    for line in raw_lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Strip playlist params — keep only the video URL
        clean = re.sub(r'[?&]list=[^&]*', '', line).strip()
        # Convert youtu.be short links to full URLs (only if not already a full URL)
        clean = re.sub(r'(?<!https://)youtu\.be/([A-Za-z0-9_-]{11})', r'https://www.youtube.com/watch?v=\1', clean)
        # Also handle plain youtu.be without any preceding https://
        if clean.startswith("youtu.be/"):
            clean = "https://www.youtube.com/watch?v=" + clean[9:9+11]
        if "youtube.com/watch?v=" in clean or "youtu.be/" in clean:
            urls.append(clean)
        else:
            print(yellow(f"  Skipping unrecognised line: {line[:60]}"))

    if not urls:
        print(red("  No valid YouTube URLs found in file."))
        pause()
        return songs

    print(bold(f"  Found {len(urls)} URL(s) — fetching titles and durations..."))
    print()

    rows = []
    failed = []
    opts = {"quiet": True, "no_warnings": True, "skip_download": True}

    with _ydl.YoutubeDL(opts) as ydl:
        for i, url in enumerate(urls, 1):
            try:
                info  = ydl.extract_info(url, download=False)
                title = _clean_yt_title(info.get("title", ""))
                dur   = info.get("duration", 0)

                # Try to build "Artist - Title" from metadata if available
                artist = info.get("artist") or info.get("creator") or ""
                track  = info.get("track") or ""
                if artist and track:
                    display = f"{artist} - {track}"
                else:
                    display = title

                rows.append({"name": display, "desc": "Hell yeah", "dur": dur, "yt": url})
                status = green("\u2713")
                print(f"  {status} [{i}/{len(urls)}] {display[:65]}")
            except Exception as e:
                failed.append((url, str(e)))
                print(red(f"  \u2717 [{i}/{len(urls)}] {url[:60]}"))
                print(dim(f"         {str(e)[:80]}"))

    print()
    if not rows:
        print(red("  No tracks fetched successfully."))
        pause()
        return songs

    # Write CSV
    out_path = prompt("Save CSV to", URL_OUT)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name", "desc", "dur", "yt"])
        for r in rows:
            w.writerow([r["name"], r["desc"], r["dur"], r["yt"]])

    print()
    print(green(f"  \u2713 CSV written with {len(rows)} track(s) \u2192 {out_path}"))
    if failed:
        print(yellow(f"  {len(failed)} URL(s) failed:"))
        for url, err in failed:
            print(yellow(f"    \u00b7 {url}"))

    print()
    do_import = prompt("Import this CSV into your song list now? (y/n)", "y").lower()
    if do_import == "y":
        songs = action_bulk_import(songs, csv_path=out_path)

    return songs


# ── OGG slot repair ──────────────────────────────────────────────────────────────────

def action_repair_slots(songs):
    """
    Shift all OGG files from a given slot onwards up or down by N positions.
    Use this when OGG files are offset from the json/config metadata.
    """
    print()
    print(bold("  OGG slot repair"))
    print()
    print(dim("  Use this when OGG files are misaligned with your song list."))
    print(dim("  Example: song80.ogg plays the wrong track because an extra file"))
    print(dim("  was inserted, shifting everything from slot 80 onwards up by 1."))
    print()

    # Show current OGG count for reference
    ogg_files = sorted(
        [f for f in os.listdir(DATA_DIR) if f.startswith("song") and f.endswith(".ogg")],
        key=lambda f: int(re.search(r'\d+', f).group())
    )
    print(f"  OGG files on disk: {bold(str(len(ogg_files)))} "
          f"(song{re.search(r'\d+', ogg_files[0]).group()} "
          f"\u2192 song{re.search(r'\d+', ogg_files[-1]).group()})")
    print(f"  Songs in list:     {bold(str(len(songs)))}")
    print()

    try:
        from_slot = int(prompt("Shift OGGs starting from slot number"))
        direction = prompt("Direction: (u)p to higher numbers or (d)own to lower numbers", "d").lower()
        amount    = int(prompt("Shift by how many slots", "1"))
    except ValueError:
        print(red("  Invalid input."))
        pause()
        return songs

    if direction not in ("u", "d"):
        print(red("  Enter u or d."))
        pause()
        return songs

    shift = amount if direction == "u" else -amount

    # Find all OGGs at or beyond from_slot
    affected = []
    for f in ogg_files:
        n = int(re.search(r'\d+', f).group())
        if n >= from_slot:
            affected.append(n)

    if not affected:
        print(yellow(f"  No OGG files found at slot {from_slot} or above."))
        pause()
        return songs

    # Check for collisions at destination
    destinations = [n + shift for n in affected]
    min_dest = min(destinations)
    if min_dest < 1:
        print(red(f"  Shift would move files to slot {min_dest} which is invalid."))
        pause()
        return songs

    print()
    print(bold(f"  Will shift {len(affected)} OGG file(s) "
               f"(slots {min(affected)}-{max(affected)}) "
               f"{'up' if shift > 0 else 'down'} by {abs(shift)}"))
    print(dim(f"  song{min(affected)}.ogg \u2192 song{min(affected)+shift}.ogg  ...  "
              f"song{max(affected)}.ogg \u2192 song{max(affected)+shift}.ogg"))
    print()
    confirm = prompt("Proceed? This renames files on disk. (yes/n)", "n").lower()
    if confirm != "yes":
        print("  Cancelled.")
        pause()
        return songs

    # Rename in the right order to avoid clobbering:
    # shifting UP  → rename highest first (descending)
    # shifting DOWN → rename lowest first (ascending)
    ordered = sorted(affected, reverse=(shift > 0))

    errors = []
    renamed = 0
    for n in ordered:
        old = ogg_path(n)
        new = ogg_path(n + shift)
        if not os.path.exists(old):
            continue
        try:
            if os.path.exists(new):
                os.remove(new)
            os.rename(old, new)
            renamed += 1
        except Exception as e:
            errors.append(f"song{n}.ogg: {e}")

    print()
    if errors:
        print(red(f"  {len(errors)} error(s):"))
        for err in errors:
            print(red(f"    {err}"))
    print(green(f"  \u2713 Renamed {renamed} file(s)."))

    # Verify alignment
    present  = sum(1 for i in range(len(songs)) if ogg_exists(i + 1))
    print(green(f"  \u2713 OGGs now matching song list: {present}/{len(songs)}"))
    print()
    pause()
    return songs


# ── export trader / types files ──────────────────────────────────────────────────────

COLLECTIBLE_JSON = os.path.join(SCRIPT_DIR, "Collectible.json")
TYPES_XML        = os.path.join(SCRIPT_DIR, "mm_music_types.xml")

def action_export_collectible(songs):
    import json as _json
    print()
    n = len(songs)
    data = {
        "m_Version": 12,
        "DisplayName": "Collectible",
        "Icon": "Deliver",
        "Color": "FBFCFEFF",
        "IsExchange": 0,
        "InitStockPercent": 100,
        "Items": [
            {
                "ClassName": "MM_Cassette_Song1",
                "MaxPriceThreshold": 10582,
                "MinPriceThreshold": 10582,
                "SellPricePercent": 60,
                "MaxStockThreshold": 1,
                "MinStockThreshold": 1,
                "QuantityPercent": 100,
                "SpawnAttachments": [],
                "Variants": [f"MM_Cassette_Song{i}" for i in range(2, n + 1)]
            }
        ]
    }
    out = prompt("Save Collectible.json to", COLLECTIBLE_JSON)
    with open(out, "w", encoding="utf-8") as f:
        _json.dump(data, f, indent="\t")
    print(green(f"  \u2713 Collectible.json written with {n} cassettes \u2192 {out}"))
    pause()

def action_export_types(songs):
    print()
    n = len(songs)
    template = (
        '    <type name="MM_Cassette_Song{n}">\n'
        '        <nominal>0</nominal>\n'
        '        <lifetime>14400</lifetime>\n'
        '        <restock>0</restock>\n'
        '        <min>0</min>\n'
        '        <quantmin>-1</quantmin>\n'
        '        <quantmax>-1</quantmax>\n'
        '        <cost>100</cost>\n'
        '        <flags count_in_cargo="0" count_in_hoarder="0" count_in_map="1" count_in_player="0" crafted="0" deloot="0"/>\n'
        '    </type>'
    )
    lines = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', '<types>']
    for i in range(1, n + 1):
        lines.append(template.format(n=i))
    lines.append('</types>')
    out = prompt("Save mm_music_types.xml to", TYPES_XML)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(green(f"  \u2713 mm_music_types.xml written with {n} entries \u2192 {out}"))
    pause()

def action_export_all_server_files(songs):
    """Export config.cpp, Collectible.json, and mm_music_types.xml in one go."""
    print()
    print(bold("  Exporting all server files..."))
    print()
    write_config(songs)
    import json as _json
    n = len(songs)

    # Collectible.json
    data = {
        "m_Version": 12,
        "DisplayName": "Collectible",
        "Icon": "Deliver",
        "Color": "FBFCFEFF",
        "IsExchange": 0,
        "InitStockPercent": 100,
        "Items": [
            {
                "ClassName": "MM_Cassette_Song1",
                "MaxPriceThreshold": 10582,
                "MinPriceThreshold": 10582,
                "SellPricePercent": 60,
                "MaxStockThreshold": 1,
                "MinStockThreshold": 1,
                "QuantityPercent": 100,
                "SpawnAttachments": [],
                "Variants": [f"MM_Cassette_Song{i}" for i in range(2, n + 1)]
            }
        ]
    }
    with open(COLLECTIBLE_JSON, "w", encoding="utf-8") as f:
        _json.dump(data, f, indent="\t")
    print(green(f"  \u2713 Collectible.json \u2192 {COLLECTIBLE_JSON}"))

    # types XML
    template = (
        '    <type name="MM_Cassette_Song{n}">\n'
        '        <nominal>0</nominal>\n'
        '        <lifetime>14400</lifetime>\n'
        '        <restock>0</restock>\n'
        '        <min>0</min>\n'
        '        <quantmin>-1</quantmin>\n'
        '        <quantmax>-1</quantmax>\n'
        '        <cost>100</cost>\n'
        '        <flags count_in_cargo="0" count_in_hoarder="0" count_in_map="1" count_in_player="0" crafted="0" deloot="0"/>\n'
        '    </type>'
    )
    lines = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', '<types>']
    for i in range(1, n + 1):
        lines.append(template.format(n=i))
    lines.append('</types>')
    with open(TYPES_XML, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(green(f"  \u2713 mm_music_types.xml \u2192 {TYPES_XML}"))
    print()
    print(green(f"  \u2713 All done! {n} cassettes across all 3 files."))
    pause()

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
    ("Build CSV from YouTube URL list",  action_urls_to_csv),
    ("Generate blank CSV template",     action_export_template),
    ("Edit existing cassette",          action_edit),
    ("Remove cassette",                 action_delete),
    ("Check for duplicates",            action_check_duplicates),
    ("Download one track from YouTube", action_download_one),
    ("Download all missing tracks",     action_download_missing),
    ("OGG file status",                 action_status),
    ("Export config.cpp",               action_export),
    ("Export Collectible.json",          action_export_collectible),
    ("Export mm_music_types.xml",        action_export_types),
    ("Export ALL server files",          action_export_all_server_files),
    ("Import from existing config.cpp", action_import_config),
    ("Repair OGG slot alignment",        action_repair_slots),
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
