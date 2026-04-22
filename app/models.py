import re
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager


def _check_password_strength(password):
    """Raise ValueError listing every unmet rule."""
    errors = []
    if len(password) < 6:
        errors.append("at least 6 characters")
    if not re.search(r'[A-Z]', password):
        errors.append("one uppercase letter (A-Z)")
    if not re.search(r'[a-z]', password):
        errors.append("one lowercase letter (a-z)")
    if not re.search(r'[0-9]', password):
        errors.append("one digit (0-9)")
    if not re.search(r'[!@#$%^&*()\-_=+\[\]{};:\'",.<>/?`~\\|]', password):
        errors.append("one special character (!@#$%^&* ...)")
    if errors:
        raise ValueError("Password must contain: " + ", ".join(errors) + ".")


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(64),  unique=True, nullable=False, index=True)
    email         = db.Column(db.String(120), unique=True, nullable=True,  index=True)
    phone         = db.Column(db.String(30),  unique=True, nullable=True,  index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    downloads     = db.relationship('Download', backref='user', lazy='dynamic')

    def set_password(self, password):
        _check_password_strength(password)          # raises ValueError if weak
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def find_by_identifier(identifier):
        """Look up a user by username, email, or phone — whichever matches."""
        return (
            User.query.filter_by(username=identifier).first() or
            User.query.filter_by(email=identifier).first() or
            User.query.filter_by(phone=identifier).first()
        )

    def __repr__(self):
        return f'<User {self.username}>'


class Download(db.Model):
    __tablename__ = 'downloads'

    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    original_url  = db.Column(db.Text,        nullable=False)
    video_title   = db.Column(db.String(255))
    filename      = db.Column(db.String(255))
    file_size     = db.Column(db.BigInteger)
    platform      = db.Column(db.String(64))
    status        = db.Column(db.String(32), default='pending')  # pending | processing | done | failed
    error_message = db.Column(db.Text)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at  = db.Column(db.DateTime)

    def file_size_human(self):
        if not self.file_size:
            return 'Unknown'
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f'{size:.1f} {unit}'
            size /= 1024
        return f'{size:.1f} TB'

    def __repr__(self):
        return f'<Download {self.id} {self.status}>'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
