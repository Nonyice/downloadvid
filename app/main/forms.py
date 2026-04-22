from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length


class VideoDownloadForm(FlaskForm):
    url = StringField(
        'Video URL',
        validators=[
            DataRequired(),
            Length(max=2048),
        ],
        render_kw={"placeholder": "Paste a TikTok, Instagram, YouTube, Facebook link..."}
    )
    submit = SubmitField('Strip & Download')


class DeleteForm(FlaskForm):
    """Empty form — used solely to carry CSRF token on delete actions."""
    pass
