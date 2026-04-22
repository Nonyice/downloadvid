import re
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TelField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Optional
from app.models import User

PASSWORD_RULES = (
    "At least 6 characters, one uppercase (A–Z), one lowercase (a–z), "
    "one digit (0–9), and one special character (!@#$%^&* etc.)"
)

PHONE_REGEX = re.compile(r"^\+[1-9][0-9]{6,14}$")


def validate_password_strength(password):
    """Return list of unmet rules. Empty list = password is valid."""
    errors = []
    if len(password) < 6:
        errors.append("at least 6 characters")
    if not re.search(r'[A-Z]', password):
        errors.append("at least one uppercase letter (A-Z)")
    if not re.search(r'[a-z]', password):
        errors.append("at least one lowercase letter (a-z)")
    if not re.search(r'[0-9]', password):
        errors.append("at least one digit (0-9)")
    if not re.search(r'[!@#$%^&*()\-_=+\[\]{};:\'",.<>/?`~\\|]', password):
        errors.append("at least one special character (!@#$%^&* ...)")
    return errors


class LoginForm(FlaskForm):
    """Login accepts username, email, or phone number interchangeably."""
    identifier = StringField(
        'Username, Email or Phone',
        validators=[DataRequired(), Length(max=120)]
    )
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Keep me signed in')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    """
    Username is always required.
    At least one of email or phone must be provided.
    """
    username  = StringField('Username',      validators=[DataRequired(), Length(3, 64)])
    email     = StringField('Email Address', validators=[Optional(), Email(), Length(max=120)])
    phone     = TelField('Phone Number',     validators=[Optional(), Length(max=30)])
    password  = PasswordField('Password',         validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirm Password', validators=[
        DataRequired(), EqualTo('password', message='Passwords must match.')
    ])
    submit = SubmitField('Create Account')

    def validate(self, extra_validators=None):
        # Email OR phone must be present — username alone is not enough
        if not super().validate(extra_validators):
            return False
        if not self.email.data and not self.phone.data:
            msg = 'Provide at least an email address or a phone number.'
            self.email.errors.append(msg)
            self.phone.errors.append(msg)
            return False
        return True

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('That username is already taken.')

    def validate_email(self, field):
        if field.data:
            if User.query.filter_by(email=field.data).first():
                raise ValidationError('That email is already registered.')

    def validate_phone(self, field):
        if field.data:
            if not PHONE_REGEX.match(field.data):
                raise ValidationError(
                    'Phone must be in international format starting with + and country code, e.g. +2348012345678'
                )
            if User.query.filter_by(phone=field.data).first():
                raise ValidationError('That phone number is already registered.')

    def validate_password(self, field):
        unmet = validate_password_strength(field.data)
        if unmet:
            raise ValidationError('Password must contain: ' + ', '.join(unmet) + '.')
