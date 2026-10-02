import os
from flask import Flask, request, render_template_string, redirect, url_for, session, send_from_directory
from werkzeug.utils import secure_filename
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "prove-am-secret-2024")

DATABASE_URL = os.getenv("DATABASE_URL")
UPLOAD_FOLDER = "media"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED = {'png','jpg','jpeg','gif','webp','mp4','mov'}

def get_db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def init_db():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS posts (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            username TEXT,
            caption TEXT,
            filename TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("DB init ok")
    except Exception as e:
        print(f"DB init error: {e}")

init_db()

# --- HTML TEMPLATES (Fixed braces) ---
HOME_HTML = """
<!doctype html>
<html><head><meta name='viewport' content='width=device-width,initial-scale=1'>
<style>body{font-family:sans-serif;max-width:600px;margin:auto;padding:20px} .post{border:1px solid #ddd;padding:10px;margin:10px 0} img{max-width:100%}</style>
</head><body>
<h2>Prove Am 📸</h2>
{% if session.username %}
<p>Hi {{session.username}} | <a href='/logout'>Logout</a></p>
<form method='post' action='/post' enctype='multipart/form-data'>
<input type='text' name='caption' placeholder='Caption' required><br><br>
<input type='file' name='file' required><br><br>
<button type='submit'>Post</button>
</form><hr>
{% else %}
<a href='/login'>Login</a> | <a href='/signup'>Signup</a><hr>
{% endif %}
{% for p in posts %}
<div class='post'>
<b>{{p.username}}</b>: {{p.caption}}<br>
{% if p.filename %}
<img src='/media/{{p.filename}}'>
{% endif %}
<small>{{p.created_at}}</small>
</div>
{% endfor %}
</body></html>
"""

@app.route('/')
def home():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM posts ORDER BY id DESC LIMIT 50")
    posts = cur.fetchall()
    cur.close()
    conn.close()
    return render_template_string(HOME_HTML, posts=posts)

@app.route('/media/<filename>')
def media_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        u = request.form['username']; p = request.form['password']
        try:
            conn = get_db(); cur = conn.cursor()
            cur.execute("INSERT INTO users (username,password) VALUES (%s,%s)", (u,p))
            conn.commit(); cur.close(); conn.close()
            return redirect('/login')
        except:
            return "User exists"
    return "<form method='post'><input name='username'><input name='password' type='password'><button>Signup</button></form>"

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        u = request.form['username']; p = request.form['password']
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=%s AND password=%s", (u,p))
        user = cur.fetchone(); cur.close(); conn.close()
        if user:
            session['username'] = user['username']; session['user_id'] = user['id']
            return redirect('/')
        return "Wrong"
    return "<form method='post'><input name='username'><input name='password' type='password'><button>Login</button></form>"

@app.route('/logout')
def logout():
    session.clear(); return redirect('/')

@app.route('/post', methods=['POST'])
def create_post():
    if 'username' not in session: return redirect('/login')
    file = request.files.get('file')
    if not file: return "No file"
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    caption = request.form.get('caption','')
    conn = get_db(); cur = conn.cursor()
    cur.execute("INSERT INTO posts (user_id,username,caption,filename) VALUES (%s,%s,%s,%s)",
                (session['user_id'], session['username'], caption, filename))
    conn.commit(); cur.close(); conn.close()
    return redirect('/')

if __name__ == '__main__':
    app.run()
