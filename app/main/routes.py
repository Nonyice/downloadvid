import os
import re
import uuid
import logging
from datetime import datetime

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    current_app,
    send_from_directory,
    abort,
)

from flask_login import login_required, current_user

from app import db
from app.main.forms import VideoDownloadForm, DeleteForm
from app.models import Download

import yt_dlp
from yt_dlp.utils import DownloadError

main = Blueprint("main", __name__)

logger = logging.getLogger(__name__)


# ----------------------------------------------------
# PLATFORM DETECTION
# ----------------------------------------------------

def detect_platform(url):

    patterns = {
        "youtube": r"(youtube\.com|youtu\.be)",
        "facebook": r"(facebook\.com|fb\.watch)",
        "instagram": r"(instagram\.com|instagr\.am)",
        "tiktok": r"(tiktok\.com)",
        "twitter": r"(twitter\.com|x\.com)",
        "reddit": r"(reddit\.com)",
        "threads": r"(threads\.net)",
        "vimeo": r"(vimeo\.com)",
        "dailymotion": r"(dailymotion\.com)",
        "pinterest": r"(pinterest\.com)",
        "spotify": r"(spotify\.com)",
        "snapchat": r"(snapchat\.com)",
    }

    for platform, pattern in patterns.items():
        if re.search(pattern, url, re.IGNORECASE):
            return platform

    return "other"


# ----------------------------------------------------
# CLEAN ERROR
# ----------------------------------------------------

def clean_error_message(message):

    text = str(message)

    if "No video formats found" in text:
        return (
            "This video cannot be downloaded. "
            "The platform did not provide any downloadable video format."
        )

    if "Unsupported URL" in text:
        return "Unsupported video link."

    if "Private video" in text:
        return "This video is private."

    if "DRM" in text.upper():
        return (
            "This video is DRM protected and cannot be downloaded."
        )

    if "Sign in" in text:
        return (
            "This video requires authentication."
        )

    if "404" in text:
        return "Video not found."

    return text[:300]


# ----------------------------------------------------
# YT-DLP
# ----------------------------------------------------

def run_yt_dlp(url, output_folder):

    os.makedirs(output_folder, exist_ok=True)

    uid = uuid.uuid4().hex[:10]

    outtmpl = os.path.join(
        output_folder,
        f"{uid}.%(ext)s"
    )

    ydl_opts = {

        "outtmpl": outtmpl,

        "format":
            "bestvideo+bestaudio/best",

        "merge_output_format": "mp4",

        "restrictfilenames": True,

        "quiet": True,

        "no_warnings": True,

        "noplaylist": True,

        "nocheckcertificate": True,

        "geo_bypass": True,

        "retries": 10,

        "fragment_retries": 10,

        "http_headers": {
            "User-Agent":
            (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64)"
            )
        },

        "postprocessors": [
            {
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
            }
        ]
    }

    try:

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(
                url,
                download=True
            )

            if not info:
                raise Exception(
                    "Unable to extract video information."
                )

            title = (
                info.get("title")
                or "Untitled Video"
            )

            filename = ydl.prepare_filename(info)

            base = os.path.splitext(filename)[0]

            if not os.path.exists(filename):

                for ext in (
                    ".mp4",
                    ".mkv",
                    ".mov",
                    ".webm",
                ):

                    possible = base + ext

                    if os.path.exists(possible):
                        filename = possible
                        break

            if not os.path.exists(filename):
                raise Exception(
                    "Downloaded file not found."
                )

            size = os.path.getsize(filename)

            return (
                os.path.basename(filename),
                title.strip()[:1000],
                size
            )

    except DownloadError as e:

        raise Exception(
            clean_error_message(e)
        )

    except Exception as e:

        raise Exception(
            clean_error_message(e)
        )

# ---------------------------------------------------------
# ROUTES
# ---------------------------------------------------------

@main.route('/')
def index():

    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    return render_template('main/index.html')


@main.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():

    form = VideoDownloadForm()

    downloads = (
        Download.query
        .filter_by(user_id=current_user.id)
        .order_by(Download.created_at.desc())
        .limit(20)
        .all()
    )

    delete_form = DeleteForm()

    return render_template(
        'main/dashboard.html',
        form=form,
        downloads=downloads,
        delete_form=delete_form
    )


@main.route('/process', methods=['POST'])
@login_required
def process():

    form = VideoDownloadForm()

    if not form.validate_on_submit():

        flash(
            'Please paste a valid video URL.',
            'danger'
        )

        return redirect(url_for('main.dashboard'))

    url = form.url.data.strip()

    platform = detect_platform(url)

    download_folder = current_app.config['DOWNLOAD_FOLDER']

    record = Download(
        user_id=current_user.id,
        original_url=url,
        platform=platform,
        status='processing',
    )

    db.session.add(record)
    db.session.commit()

    try:

        filename, title, size = run_yt_dlp(
            url,
            download_folder
        )

        record.filename = filename
        record.video_title = title
        record.file_size = size
        record.status = 'done'
        record.completed_at = datetime.utcnow()

        db.session.commit()

        flash(
            f'"{title}" is ready for download.',
            'success'
        )

    except Exception as e:

        record.status = 'failed'
        record.error_message = str(e)

        db.session.commit()

        flash(
            f'Failed to process video: {str(e)}',
            'danger'
        )

    return redirect(url_for('main.dashboard'))


@main.route('/download/<int:download_id>')
@login_required
def download_file(download_id):

    record = Download.query.filter_by(
        id=download_id,
        user_id=current_user.id
    ).first_or_404()

    if record.status != 'done' or not record.filename:
        abort(404)

    folder = current_app.config['DOWNLOAD_FOLDER']

    file_path = os.path.join(
        folder,
        record.filename
    )

    if not os.path.exists(file_path):
        abort(404)

    return send_from_directory(
        folder,
        record.filename,
        as_attachment=True
    )


@main.route('/delete/<int:download_id>', methods=['POST'])
@login_required
def delete_download(download_id):

    record = Download.query.filter_by(
        id=download_id,
        user_id=current_user.id
    ).first_or_404()

    if record.filename:

        path = os.path.join(
            current_app.config['DOWNLOAD_FOLDER'],
            record.filename
        )

        if os.path.exists(path):
            os.remove(path)

    db.session.delete(record)
    db.session.commit()

    flash(
        'Download removed successfully.',
        'info'
    )

    return redirect(url_for('main.dashboard'))


@main.route('/history')
@login_required
def history():

    page = request.args.get(
        'page',
        1,
        type=int
    )

    downloads = (
        Download.query
        .filter_by(user_id=current_user.id)
        .order_by(Download.created_at.desc())
        .paginate(
            page=page,
            per_page=15,
            error_out=False
        )
    )

    delete_form = DeleteForm()

    return render_template(
        "main/history.html",
        downloads=downloads,
        delete_form=delete_form
    )