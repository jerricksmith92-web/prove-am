import os
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import sqlite3

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'proveam_ghana_gold_2026')
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED = {'png','jpg','jpeg'}

def get_db():
    conn = sqlite3.connect('proveam.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS users
        (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS posts
        (id INTEGER PRIMARY KEY, user_id INTEGER, username TEXT, image TEXT,
         caption TEXT, timestamp TEXT, challenge_from TEXT, streak INTEGER)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS replies
        (id INTEGER PRIMARY KEY, post_id INTEGER, user_id INTEGER, username TEXT, image TEXT, timestamp TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS friends
        (id INTEGER PRIMARY KEY, user_id INTEGER, friend_id INTEGER, friend_name TEXT)''')
    conn.commit()
    conn.close()

init_db()

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>PROVE AM</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#000;color:#fff;font-family:-apple-system,BlinkMacSystemFont,sans-serif}
.header{text-align:center;padding:15px;border-bottom:1px solid #222;position:sticky;top:0;background:#000;z-index:10}
.logo{color:#D4AF37;font-size:28px;font-weight:900;letter-spacing:3px}
.btn-gold{background:#D4AF37;color:#000;border:none;padding:12px 20px;border-radius:25px;font-weight:800;width:100%;margin:5px 0}
.btn-dark{background:#222;color:#fff;border:1px solid #444;padding:12px 20px;border-radius:25px;font-weight:700;width:100%;margin:5px 0}
.card{background:#111;border:1px solid #D4AF37;border-radius:15px;padding:15px;margin:15px}
.post-img{width:100%;border-radius:12px;margin-top:10px;max-height:500px;object-fit:cover}
.small{font-size:12px;color:#888}
input{width:100%;padding:12px;border-radius:10px;border:1px solid #333;background:#111;color:#fff;margin:8px 0}
.video-wrap{width:100%;height:60vh;background:#000;border-radius:15px;overflow:hidden;position:relative}
#video{width:100%;height:100%;object-fit:cover}
</style>
</head>
<body>

<div class="header">
  <div class="logo">PROVE AM</div>
  <div class="small">@{{ session.get('username','Guest') }}</div>
</div>

{% if not session.get('user_id') %}
<div class="card">
  <h3 style="color:#D4AF37;text-align:center">Join PROVE AM 🇬🇭</h3>
  <form method="post" action="/auth">
    <input name="username" placeholder="Username" required>
    <input name="password" type="password" placeholder="Password" required>
    <button class="btn-gold" name="action" value="signup">SIGN UP</button>
    <button class="btn-dark" name="action" value="login">LOGIN</button>
  </form>
</div>
{% else %}

<div class="card" style="display:flex;justify-content:space-between">
  <div><b>Streak: <span style="color:#D4AF37">{{ streak }} days</span></b><br><span class="small">Longest: {{ longest }}</span></div>
  <div><a href="/friends" style="color:#D4AF37;text-decoration:none">👥 Friends</a></div>
</div>

<div class="card">
  <form method="post" action="/challenge">
    <input name="to_user" placeholder="Challenge who? (username)">
    <input name="challenge_text" placeholder="Ask them to prove... e.g. Prove you dey gym!">
    <button class="btn-gold">⚡ ASK TO PROVE AM</button>
  </form>
</div>

<div class="card">
  <h4 style="color:#D4AF37">📸 PROVE AM NOW</h4>
  <div class="video-wrap">
    <video id="video" autoplay playsinline muted></video>
  </div>
  <input type="file" id="fileInput" accept="image/*" capture="environment" style="display:none">
  <canvas id="canvas" style="display:none"></canvas>
  <input id="caption" placeholder="What you dey prove?">
  <button class="btn-gold" onclick="capture()">CAPTURE & PROVE</button>
  <button class="btn-dark" onclick="document.getElementById('fileInput').click()">📁 Use Gallery (iPhone Fix)</button>
  <div id="status" class="small" style="text-align:center;margin-top:8px"></div>
</div>

<div style="padding:15px">
{% for post in posts %}
  <div class="card">
    <div style="display:flex;justify-content:space-between">
      <b>@{{ post['username'] }}</b>
      <span class="small">{{ post['timestamp'] }}</span>
    </div>
    {% if post['challenge_from'] %}
    <div style="background:#D4AF37;color:#000;padding:5px 10px;border-radius:10px;margin:8px 0;font-size:12px;font-weight:700">
      ⚡ {{ post['challenge_from'] }} asked: {{ post['caption'] }}
    </div>
    {% else %}
    <div style="margin:8px 0">{{ post['caption'] }}</div>
    {% endif %}
    <img src="/{{ post['image'] }}" class="post-img">

    <div style="display:flex;gap:8px;margin-top:10px">
      <button class="btn-dark" style="flex:1" onclick="replyTo({{ post['id'] }})">💬 Reply with Proof</button>
      {% if post['user_id'] == session['user_id'] %}
      <a href="/delete/{{ post['id'] }}" style="flex:0.5;text-align:center;background:#440000;color:#fff;padding:12px;border-radius:25px;text-decoration:none">🗑️ Delete</a>
      {% endif %}
    </div>

    {% for r in replies if r['post_id'] == post['id'] %}
      <div style="margin-top:10px;background:#0a0a0a;padding:10px;border-radius:10px;border-left:2px solid #D4AF37">
        <b class="small">@{{ r['username'] }} replied:</b><br>
        <img src="/{{ r['image'] }}" style="width:100%;border-radius:8px;margin-top:5px">
        <div class="small">{{ r['timestamp'] }}</div>
      </div>
    {% endfor %}
  </div>
{% endfor %}
</div>

{% endif %}

<script>
let stream;
async function initCam(){
  try{
    stream = await navigator.mediaDevices.getUserMedia({video:{facingMode:"environment"},audio:false});
    let v=document.getElementById('video');
    v.srcObject=stream; v.setAttribute('playsinline',true); await v.play();
  }catch(e){ document.getElementById('status').innerText="Camera blocked, use Gallery button 👇"; }
}
initCam();

function capture(){
  let video=document.getElementById('video');
  let canvas=document.getElementById('canvas');
  let caption=document.getElementById('caption').value;
  if(video.videoWidth==0){ document.getElementById('fileInput').click(); return; }
  canvas.width=video.videoWidth; canvas.height=video.videoHeight;
  canvas.getContext('2d').drawImage(video,0,0);
  canvas.toBlob(blob=>{
    let fd=new FormData();
    fd.append('image',blob,'prove.jpg');
    fd.append('caption',caption);
    fd.append('lat',''); fd.append('lon','');
    fetch('/post',{method:'POST',body:fd}).then(()=>location.reload());
  },'image/jpeg',0.8);
}

document.getElementById('fileInput').addEventListener('change',function(){
  if(!this.files[0]) return;
  let fd=new FormData();
  fd.append('image',this.files[0]);
  fd.append('caption',document.getElementById('caption').value);
  fetch('/post',{method:'POST',body:fd}).then(()=>location.reload());
});

function replyTo(id){
  document.getElementById('fileInput').onchange = function(){
    let fd=new FormData(); fd.append('image',this.files[0]); fd.append('post_id',id);
    fetch('/reply',{method:'POST',body:fd}).then(()=>location.reload());
  };
  document.getElementById('fileInput').click();
}
</script>
</body>
</html>
"""

FRIENDS_HTML = """
<div class="header"><div class="logo">FRIENDS</div><a href="/" style="color:#D4AF37">← Back</a></div>
<div class="card">
  <form method="post">
    <input name="friend_name" placeholder="Friend username to add">
    <button class="btn-gold">Add Friend</button>
  </form>
</div>
<div class="card">
  {% for f in friends %}<div style="padding:10px;border-bottom:1px solid #222">@{{ f['friend_name'] }} <a href="/challenge_user/{{ f['friend_name'] }}" style="color:#D4AF37;float:right">Challenge</a></div>{% endfor %}
</div>
"""

@app.route('/')
def home():
    if 'user_id' not in session:
        return render_template_string(HTML, posts=[], replies=[], streak=0, longest=0)
    conn=get_db()
    posts=conn.execute('SELECT * FROM posts ORDER BY id DESC').fetchall()
    replies=conn.execute('SELECT * FROM replies ORDER BY id DESC').fetchall()
    # streak calc simple
    user_posts=conn.execute('SELECT timestamp FROM posts WHERE user_id=? ORDER BY id DESC',(session['user_id'],)).fetchall()
    streak=len(user_posts)
    conn.close()
    return render_template_string(HTML, posts=posts, replies=replies, streak=streak, longest=streak)

@app.route('/auth', methods=['POST'])
def auth():
    u=request.form['username'].strip()
    p=request.form['password']
    act=request.form['action']
    conn=get_db()
    if act=='signup':
        try:
            conn.execute('INSERT INTO users (username,password) VALUES (?,?)',(u,generate_password_hash(p)))
            conn.commit()
        except: pass
    user=conn.execute('SELECT * FROM users WHERE username=?',(u,)).fetchone()
    conn.close()
    if user and check_password_hash(user['password'],p):
        session['user_id']=user['id']; session['username']=user['username']
    return redirect('/')

@app.route('/post', methods=['POST'])
def post():
    if 'user_id' not in session: return 'no'
    img=request.files['image']
    caption=request.form.get('caption','')
    fname=secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{img.filename}")
    path=os.path.join(app.config['UPLOAD_FOLDER'],fname)
    img.save(path)
    conn=get_db()
    conn.execute('INSERT INTO posts (user_id,username,image,caption,timestamp) VALUES (?,?,?,?,?)',
        (session['user_id'],session['username'],path,caption,datetime.now().strftime('%Y-%m-%d %H:%M')))
    conn.commit(); conn.close()
    return 'ok'

@app.route('/delete/<int:pid>')
def delete(pid):
    conn=get_db()
    conn.execute('DELETE FROM posts WHERE id=? AND user_id=?',(pid,session['user_id']))
    conn.commit(); conn.close()
    return redirect('/')

@app.route('/reply', methods=['POST'])
def reply():
    img=request.files['image']
    pid=request.form['post_id']
    fname=secure_filename(f"reply_{datetime.now().strftime('%Y%m%d%H%M%S')}_{img.filename}")
    path=os.path.join(app.config['UPLOAD_FOLDER'],fname)
    img.save(path)
    conn=get_db()
    conn.execute
