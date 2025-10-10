from flask import Flask
from config import Config
from database import db
from sqlalchemy import text

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

@app.route('/')
def index():
    return '<h1>Hello, Flask with SQLAlchemy and SQL Server!</h1>'

@app.route('/test-db')
def test_db():
    try:
        db.session.execute(text('SELECT 1'))
        return '✅ Database connection successful!'
    except Exception as e:
        return f'❌ Database connection failed: {e}'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)