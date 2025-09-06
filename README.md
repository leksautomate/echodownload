# # EchoDownload: Multi-Platform Video Downloader

EchoDownload is a user-friendly desktop application for downloading videos and audio from popular platforms, built with Python and PyQt6. It uses the powerful `yt-dlp` library to handle downloads, with support for multiple formats, quality options, clipboard integration, and convenient file organization.

## Features

- **Cross-platform GUI** (PyQt6) for easy downloading
- **Clipboard integration**: Automatically detects URLs copied to clipboard
- **Download queue**: Add multiple downloads; downloads are processed sequentially
- **Supports MP4 (video) and MP3 (audio) downloads**
- **Platform detection**: Downloads are organized into platform-specific folders
- **Configurable download path**: Choose where files are saved
- **System tray notifications** and optional sound alerts
- **Download history**: View status and details of recent downloads
- **Safe cancellation**: Downloads can be cancelled gracefully

## Installation

1. **Install Python 3.8+** (recommended)
2. **Clone the repository:**
   ```bash
   git clone https://github.com/leksautomate/echodownload.git
   cd echodownload
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   - This includes `PyQt6` and `yt-dlp`.

## Usage

1. **Run the application:**
   ```bash
   python EchoDownload.py
   ```
2. **Download videos or audio:**
   - Copy a video/audio URL (e.g., from YouTube).
   - Paste it in the app, choose format (MP4/MP3), quality, and click "Download".
   - Downloads are saved in folders by platform and format.

3. **Change download folder:**  
   Use the "Change Folder" button to select your preferred location.

4. **Tray notifications:**  
   The app notifies you when downloads finish (with optional sound).

## Configuration & Assets

- Settings are saved in `settings.json`.
- Download history is stored in `history.json`.
- Place `icon.png`, `splash.png`, and `speech.wav` in the main directory for best UI experience.

## Dependencies

See `requirements.txt` for full list.

## Contribution

Pull requests are welcome!  
Please open an issue for feature requests or bug reports.

## License

Specify your license here (e.g., MIT, GPL, etc.)

## Contact & Social

- **YouTube:** [@leksautomate](https://www.youtube.com/@leksautomate)
- **Twitter/X:** [@leksautomate](https://twitter.com/leksautomate)
- **TikTok:** [@leksautomate](https://www.tiktok.com/@leksautomate)

## Credits

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for download engine
- PyQt6 for the GUI framework

---

**Maintainer:** [leksautomate](https://github.com/leksautomate)

