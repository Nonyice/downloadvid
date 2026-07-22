from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length, URL


class VideoDownloadForm(FlaskForm):

    url = StringField(
        'Video URL',
        validators=[
            DataRequired(),
            URL(),
            Length(max=2048),
        ],
        render_kw={
            "placeholder": (
                "Paste any supported video link..."
            )
        }
    )

    submit = SubmitField('Download Video')


class DeleteForm(FlaskForm):
    pass