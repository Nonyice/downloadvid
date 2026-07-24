import os
import re
import uuid
import glob
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

main = Blueprint('main', __name__)


# ---------------------------------------------------------
# PLATFORM DETECTION
# ---------------------------------------------------------

def detect_platform(url):
    patterns = {
        'tiktok': r'tiktok\.com',
        'instagram': r'instagram\.com|instagr\.am',
        'youtube': r'youtube\.com|youtu\.be',
        'facebook': r'facebook\.com|fb\.watch',
        'twitter': r'twitter\.com|x\.com',
        'snapchat': r'snapchat\.com',
        'vimeo': r'vimeo\.com',
        'dailymotion': r'dailymotion\.com',
        'reddit': r'reddit\.com',
        'pinterest': r'pinterest\.com',
        'threads': r'threads\.net',
        'spotify': r'spotify\.com',
    }

    for platform, pattern in patterns.items():
        if re.search(pattern, url, re.IGNORECASE):
            return platform

    return 'other'


# ---------------------------------------------------------
# CLEAN ERROR MESSAGES
# ---------------------------------------------------------

def clean_error_message(error_text):
    error_text = str(error_text)

    if 'DRM' in error_text.upper():
        return (
            'This video appears to be DRM protected and cannot be downloaded. '
            'Streaming platforms with encryption are not supported.'
        )

    if 'Unsupported URL' in error_text:
        return 'This video link is not supported.'

    if 'Requested format is not available' in error_text:
        return 'No downloadable video format was found.'

    if 'Private video' in error_text:
        return 'This video is private.'

    if 'Sign in' in error_text:
        return 'This video requires login or authentication.'

    if '404' in error_text:
        return 'Video not found.'

    return error_text[:300]


# ---------------------------------------------------------
# DOWNLOAD LOGIC
# ---------------------------------------------------------

def run_yt_dlp(url, output_dir):

    os.makedirs(output_dir, exist_ok=True)

    uid = uuid.uuid4().hex[:10]

    outtmpl = os.path.join(
        output_dir,
        f'{uid}_%(title).80s.%(ext)s'
    )

    ydl_opts = {
        'outtmpl': outtmpl,

        'format': 'bestvideo+bestaudio/best',

        'merge_output_format': 'mp4',

        'restrictfilenames': True,

        'quiet': True,
        'no_warnings': True,

        'noplaylist': True,

        'nocheckcertificate': True,

        'retries': 10,
        'fragment_retries': 10,

        'geo_bypass': True,

        'http_headers': {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/122.0 Safari/537.36'
            )
        },

        'extractor_args': {
            'tiktok': {
                'webpage_download': ['false']
            }
        },

        'postprocessors': [
            {
                'key': 'FFmpegVideoConvertor',
                'preferredformat': 'mp4',
            }
        ],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            if not info:
                raise Exception('Unable to extract video information.')

            title = info.get('title', 'video')
            filename = ydl.prepare_filename(info)

            # If the expected filename isn't found, search for any file
            # with the same base name regardless of extension.
            if not os.path.exists(filename):
                base = os.path.splitext(filename)[0]
                matches = glob.glob(base + ".*")
                if matches:
                    filename = matches[0]

            # Final fallback: use the newest file in the download folder.
            if not os.path.exists(filename):
                downloaded_files = [
                    os.path.join(output_dir, f)
                    for f in os.listdir(output_dir)
                    if os.path.isfile(os.path.join(output_dir, f))
                ]

                if downloaded_files:
                    filename = max(downloaded_files, key=os.path.getmtime)

            if not os.path.exists(filename):
                raise Exception("Downloaded file could not be located.")

            size = os.path.getsize(filename)

            return (
                os.path.basename(filename),
                title,
                size
            )

    except DownloadError as e:
        raise Exception(clean_error_message(str(e)))

    except Exception as e:
        raise Exception(clean_error_message(str(e)))


@main.route('/process', methods=['GET', 'POST'])
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

        error_message = clean_error_message(str(e))

        record.status = 'failed'
        record.error_message = error_message

        db.session.commit()

        flash(
            f'Failed to process video: {error_message}',
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