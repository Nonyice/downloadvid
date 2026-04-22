import os
import re
import uuid
from datetime import datetime
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, current_app, send_from_directory, abort)
from flask_login import login_required, current_user
from app import db
from app.main.forms import VideoDownloadForm, DeleteForm
from app.models import Download

main = Blueprint('main', __name__)


def detect_platform(url):
    patterns = {
        'tiktok':    r'tiktok\.com',
        'instagram': r'instagram\.com|instagr\.am',
        'youtube':   r'youtube\.com|youtu\.be',
        'facebook':  r'facebook\.com|fb\.watch',
        'twitter':   r'twitter\.com|x\.com',
        'snapchat':  r'snapchat\.com',
    }
    for platform, pattern in patterns.items():
        if re.search(pattern, url, re.IGNORECASE):
            return platform
    return 'other'


def run_yt_dlp(url, output_dir):
    import yt_dlp
    uid = uuid.uuid4().hex[:10]
    outtmpl = os.path.join(output_dir, f'{uid}_%(title).60s.%(ext)s')
    ydl_opts = {
        'outtmpl': outtmpl,
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'merge_output_format': 'mp4',
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {
            'tiktok': {'webpage_download': ['0']},
        },
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get('title', 'video')
        filename = ydl.prepare_filename(info)
        if not os.path.exists(filename):
            base = os.path.splitext(filename)[0]
            for ext in ['.mp4', '.mkv', '.webm']:
                if os.path.exists(base + ext):
                    filename = base + ext
                    break
        size = os.path.getsize(filename) if os.path.exists(filename) else 0
        return os.path.basename(filename), title, size


@main.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('main/index.html')


@main.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    form = VideoDownloadForm()
    downloads = (Download.query
                 .filter_by(user_id=current_user.id)
                 .order_by(Download.created_at.desc())
                 .limit(20).all())
    delete_form = DeleteForm()
    return render_template('main/dashboard.html', form=form, downloads=downloads, delete_form=delete_form)


@main.route('/process', methods=['POST'])
@login_required
def process():
    form = VideoDownloadForm()
    if not form.validate_on_submit():
        flash('Please paste a valid video URL.', 'danger')
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
        filename, title, size = run_yt_dlp(url, download_folder)
        record.filename = filename
        record.video_title = title
        record.file_size = size
        record.status = 'done'
        record.completed_at = datetime.utcnow()
        db.session.commit()
        flash(f'"{title}" stripped and ready to download!', 'success')
    except Exception as e:
        record.status = 'failed'
        record.error_message = str(e)
        db.session.commit()
        flash(f'Failed to process video: {str(e)}', 'danger')
    return redirect(url_for('main.dashboard'))


@main.route('/download/<int:download_id>')
@login_required
def download_file(download_id):
    record = Download.query.filter_by(
        id=download_id, user_id=current_user.id
    ).first_or_404()
    if record.status != 'done' or not record.filename:
        abort(404)
    folder = current_app.config['DOWNLOAD_FOLDER']
    return send_from_directory(folder, record.filename, as_attachment=True)


@main.route('/delete/<int:download_id>', methods=['POST'])
@login_required
def delete_download(download_id):
    record = Download.query.filter_by(
        id=download_id, user_id=current_user.id
    ).first_or_404()
    if record.filename:
        path = os.path.join(current_app.config['DOWNLOAD_FOLDER'], record.filename)
        if os.path.exists(path):
            os.remove(path)
    db.session.delete(record)
    db.session.commit()
    flash('Download record removed.', 'info')
    return redirect(url_for('main.dashboard'))


@main.route('/history')
@login_required
def history():
    page = request.args.get('page', 1, type=int)
    downloads = (Download.query
                 .filter_by(user_id=current_user.id)
                 .order_by(Download.created_at.desc())
                 .paginate(page=page, per_page=15, error_out=False))
    delete_form = DeleteForm()
    return render_template("main/history.html", downloads=downloads, delete_form=delete_form)
