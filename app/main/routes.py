def run_yt_dlp(url, output_dir):
    """
    Download a video using yt-dlp and return:
        filename, title, size
    """

    os.makedirs(output_dir, exist_ok=True)

    uid = uuid.uuid4().hex[:10]

    outtmpl = os.path.join(
        output_dir,
        f"{uid}_%(title).80s.%(ext)s"
    )

    ydl_opts = {
        # Output
        "outtmpl": outtmpl,

        # Download highest quality available
        "format": "bestvideo+bestaudio/best",

        # Merge into MP4 if ffmpeg exists
        "merge_output_format": "mp4",

        # One video only
        "noplaylist": True,

        # Cleaner filenames
        "restrictfilenames": True,

        # Logging
        "quiet": True,
        "no_warnings": True,

        # Network reliability
        "retries": 10,
        "fragment_retries": 10,
        "socket_timeout": 30,

        # SSL
        "nocheckcertificate": True,

        # Geo bypass
        "geo_bypass": True,

        # Browser-like request
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/138.0 Safari/537.36"
            )
        },

        # Optional:
        # Uncomment if using exported cookies.txt
        #
        # "cookiefile": os.path.join(
        #     current_app.root_path,
        #     "cookies.txt"
        # ),

        # Convert videos when possible
        "postprocessors": [{
            "key": "FFmpegVideoConvertor",
            "preferedformat": "mp4",
        }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(url, download=True)

            if info is None:
                raise Exception("Unable to retrieve video information.")

            title = info.get("title", "Untitled Video")

            filename = ydl.prepare_filename(info)

            if not os.path.exists(filename):

                base = os.path.splitext(filename)[0]

                for ext in (
                    ".mp4",
                    ".mkv",
                    ".webm",
                    ".mov",
                    ".m4a",
                    ".mp3"
                ):
                    possible = base + ext

                    if os.path.exists(possible):
                        filename = possible
                        break

            if not os.path.exists(filename):
                raise Exception("Downloaded file could not be located.")

            filesize = os.path.getsize(filename)

            return (
                os.path.basename(filename),
                title,
                filesize,
            )

    except DownloadError as e:
        raise Exception(clean_error_message(str(e)))

    except Exception as e:
        raise Exception(clean_error_message(str(e)))