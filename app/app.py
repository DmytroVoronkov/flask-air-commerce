from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from urllib.parse import quote_plus

app = Flask(__name__)

connection_string = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=mssql,1433;"
    "DATABASE=master;"
    "UID=sa;"
    "PWD=YourStrong@Password123;"
    "Encrypt=no;"
    "TrustServerCertificate=yes;"
)

params = quote_plus(connection_string)

app.config['SQLALCHEMY_DATABASE_URI'] = f"mssql+pyodbc:///?odbc_connect={params}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

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
