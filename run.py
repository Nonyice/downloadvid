import os
from app import create_app, db
from app.models import User, Download

app = create_app(os.environ.get('FLASK_ENV', 'default'))


@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Download=Download)


@app.cli.command('init-db')
def init_db():
    """Create all database tables."""
    with app.app_context():
        db.create_all()
        print('Database tables created successfully.')


if __name__ == '__main__':
    app.run(debug=True)
