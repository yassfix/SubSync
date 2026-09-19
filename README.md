# SubSync

A simple desktop app that syncs subtitles to your videos with one click. It's a friendly GUI for [`ffsubsync`](https://github.com/smacke/ffsubsync), built with Python and [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter).

<!-- Add a screenshot: ![SubSync screenshot](docs/screenshot.png) -->

## Features

- **Batch sync** – pick a folder, tick the videos you want, and sync them all at once.
- **Smart matching** – pairs videos with subtitles by episode number (`S01E02`, `1x02`), or by identical filename.
- **Manual mode** – choose one video and one subtitle yourself.
- **Safe** – originals are backed up before anything is changed.
- **Smooth** – progress bar, live log, and a UI that never freezes.

**Supported files:** videos `.mp4` `.mkv` `.avi` `.mov` `.flv` `.wmv` · subtitles `.srt` `.vtt`

## Requirements

- Python 3.8+
- [FFmpeg](https://ffmpeg.org/download.html) on your `PATH` (or placed next to the script)
- `ffsubsync` and `customtkinter`

## Installation

```bash
git clone https://github.com/yassfix/SubSync.git
cd SubSync
pip install customtkinter ffsubsync
python subsync.py
```

## How to use

**Directory Mode**
1. Click **Browse Folder** and select the folder with your videos and subtitles.
2. Tick the videos you want to sync.
3. Click **SYNC SELECTED VIDEOS**.

Each original subtitle is copied to `old_subtitles/`, and the synced one is saved next to the video with the same name (e.g. `Show.S01E02.mkv` → `Show.S01E02.srt`).

**Manual Single File**
1. Select a video and a subtitle.
2. Click **SYNC THIS FILE**.

The original is backed up to `original_subs/` and the subtitle file is replaced with the synced version.

## Build an .exe (Windows)

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile --collect-all customtkinter ^
  --add-binary "ffmpeg.exe;." --add-binary "ffprobe.exe;." subsync.py
```

`ffsubsync` is called as an external command, so it still needs to be installed on the machine running the app.

## Good to know

- Directory Mode scans only the chosen folder, not subfolders.
- Syncing the same files twice overwrites the earlier backup, so keep a copy if you want the very first original.

## Credits

Powered by [ffsubsync](https://github.com/smacke/ffsubsync), [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter), and [FFmpeg](https://ffmpeg.org/).

## License

MIT
