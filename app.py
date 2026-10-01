import os, sqlite3
from flask import Flask, render_template_string, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'proveam_final_2026_ghana')
UPLOAD = 'static/uploads'
os.makedirs(UPLOAD, exist_ok=True)

def get_db():
    conn = sqlite3.connect('proveam.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY, user_id INTEGER, username TEXT, image TEXT, caption TEXT, timestamp TEXT, challenge_from TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS replies (id INTEGER PRIMARY KEY, post_id INTEGER, user_id INTEGER, username TEXT, image TEXT, timestamp TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS friends (id INTEGER PRIMARY KEY, user_id INTEGER, friend_name TEXT)')
    conn.commit()
    conn.close()
init_db()

MAIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>PROVE AM</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#000;color:#fff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
.top{position:sticky;top:0;z-index:10;background:#000;border-bottom:1px solid #151515;padding:14px 0 10px;text-align:center}
.logo-img{width:58px;height:58px;border-radius:50%;border:2px solid #D4AF37;object-fit:cover;display:block;margin:0 auto 6px}
.logo-text{color:#D4AF37;font-size:30px;font-weight:900;letter-spacing:2.5px;line-height:1}
.user{color:#888;font-size:12px;margin-top:4px}
.card{background:#0f0f0f;border:1.5px solid #D4AF37;border-radius:16px;padding:14px;margin:12px}
.flex{display:flex;justify-content:space-between;align-items:center}
.gold{color:#D4AF37}
.small{color:#777;font-size:11px}
input{width:100%;padding:13px 14px;border-radius:12px;border:1px solid #2a2a2a;background:#1a1a1a;color:#fff;margin:6px 0;font-size:13px;outline:none}
.btn{width:100%;padding:13px;border-radius:25px;border:none;font-weight:900;font-size:13px;margin-top:8px;cursor:pointer}
.btn-gold{background:#D4AF37;color:#000}
.btn-dark{background:#1f1f1f;color:#fff;border:1px solid #333}
#video{width:100%;height:50vh;background:#000;border-radius:12px;object-fit:cover;display:block}
.post-img{width:100%;border-radius:12px;margin-top:10px;display:block}
.actions{display:flex;gap:8px;margin-top:10px}
.act{flex:1;padding:10px 6px;border-radius:20px;text-align:center;font-size:12px;text-decoration:none;border:1px solid #333;background:#1e1e1e;color:#fff;cursor:pointer}
.act-del{background:#251010;border-color:#5a2222;color:#ff7a7a}
.act-dl{background:#102116;border-color:#204d2a;color:#7dff9f}
</style>
</head>
<body>
<div class="top">
<img class="logo-img" src="/static/uploads/logo.jpg" onerror="this.src='/static/uploads/logo.png'; this.onerror=function(){this.style.display='none'}">
<div class="logo-text">PROVE AM</div>
<div class="user">@{{ session.get('username','Guest') }}</div>
</div>

{% if not session.get('user_id') %}
<div class="card"><h3 style="color:#D4AF37;text-align:center;margin-bottom:10px">Join PROVE AM 🇬🇭</h3>
<form method="post" action="/auth">
<input name="username" placeholder="Username" required>
<input name="password" type="password" placeholder="Password" required>
<button class="btn btn-gold" name="action" value="signup">SIGN UP</button>
<button class="btn btn-dark" name="action" value="login">LOGIN</button>
</form></div>
{% else %}

<div class="card flex">
<div><div style="font-weight:800;font-size:15px">Streak: <span class="gold">{{ streak }} days</span></div><div class="small">Longest: {{ longest }}</div></div>
<a href="/friends" style="color:#D4AF37;text-decoration:none;font-size:14px">👥 Friends</a>
</div>

<div class="card">
<input id="to_user" placeholder="Challenge who? (username)">
<input id="challenge_text" placeholder="Ask them to prove... e.g. Prove you dey gym!">
<button class="btn btn-gold" onclick="doChallenge()">⚡ ASK TO PROVE AM</button>
</div>

<div class="card">
<div style="color:#D4AF37;font-weight:800;margin-bottom:10px;font-size:14px">📸 PROVE AM NOW</div>
<video id="video" autoplay playsinline muted></video>
<input type="file" id="fileInput" accept="image/*" capture="environment" style="display:none">
<canvas id="canvas" style="display:none"></canvas>
<input id="caption" placeholder="What you dey prove?">
<button class="btn btn-gold" onclick="doCapture()">CAPTURE & PROVE</button>
<button class="btn btn-dark" onclick="document.getElementById('fileInput').click()">📁 Gallery (Fix Black Camera)</button>
</div>

{% for p in posts %}
<div class="card">
<div class="flex"><b style="font-size:14px">@{{ p['username'] }}</b><span class="small">{{ p['timestamp'] }}</span></div>
{% if p['challenge_from'] %}
<div style="background:#D4AF37;color:#000;padding:7px 10px;border-radius:9px;margin:8px 0;font-size:12px;font-weight:700">{{ p['challenge_from'] }}: {{ p['caption'] }}</div>
{% else %}
<div style="margin:8px 0;font-size:13px">{{ p['caption'] }}</div>
{% endif %}
<img src="/{{ p['image'] }}" class="post-img">
<div class="actions">
<button class="act" onclick="doReply({{ p['id'] }})">💬 Reply</button>
<a class="act act-dl" href="/{{ p['image'] }}" download>⬇️ Download</a>
{% if p['user_id'] == session['user_id'] %}
<a class="act act-del" href="/delete/{{ p['id'] }}">🗑️ Delete</a>
{% endif %}
</div>
{% for r in replies if r['post_id'] == p['id'] %}
<div style="margin-top:10px;background:#151515;padding:9px;border-radius:10px;border-left:2px solid #D4AF37">
<div class="small">@{{ r['username'] }} replied:</div>
<img src="/{{ r['image'] }}" style="width:100%;border-radius:8px;margin-top:6px">
<div class="flex" style="margin-top:4px"><span class="small">{{ r['timestamp'] }}</span><a href="/{{ r['image'] }}" download style="color:#7dff9f;font-size:11px;text-decoration:none">⬇️ Download</a></div>
</div>
{% endfor %}
</div>
{% endfor %}

{% endif %}

<script>
async function initCam(){
  try{
    const s = await navigator.mediaDevices.getUserMedia({video:{facingMode:"environment"},audio:false});
    const v = document.getElementById('video');
    if(v){v.srcObject=s; v.setAttribute('playsinline',''); await v.play();}
  }catch(e){}
}
initCam();

function doCapture(){
  const v = document.getElementById('video');
  const c = document.getElementById('canvas');
  if(!v || v.videoWidth===0){ document.getElementById('fileInput').click(); return; }
  c.width=v.videoWidth; c.height=v.videoHeight;
  c.getContext('2d').drawImage(v,0,0);
  c.toBlob((blob)=>{
    const fd=new FormData();
    fd.append('image',blob,'prove.jpg');
    fd.append('caption',document.getElementById('caption').value);
    fetch('/post',{method:'POST',body:fd}).then(()=>location.reload());
  },'image/jpeg',0.85);
}

document.getElementById('fileInput').addEventListener('change',function(){
  if(!this.files[0]) return;
  const fd=new FormData();
  fd.append('image',this.files[0]);
  const cap=document.getElementById('caption');
  fd.append('caption',cap?cap.value:'');
  fetch('/post',{method:'POST',body:fd}).then(()=>location.reload());
});

function doReply(id){
  const inp=document.getElementById('fileInput');
  inp.onchange=function(){
    if(!this.files[0]) return;
    const fd=new FormData();
    fd.append('image',this.files[0]);
    fd.append('post_id',id);
    fetch('/reply',{method:'POST',body:fd}).then(()=>location.reload());
  };
  inp.click();
}

function doChallenge(){
  const to=document.getElementById('to_user').value.trim();
  const txt=document.getElementById('challenge_text').value.trim();
  if(!to||!txt){alert('Fill both fields');return;}
  const fd=new FormData();
  fd.append('to_user',to);
  fd.append('challenge_text',txt);
  fetch('/challenge',{method:'POST',body:fd}).then(()=>location.reload());
}
</script>
</body>
</html>
"""

FRIENDS_PAGE = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Friends - PROVE AM</title>
<style>
body{background:#000;color:#fff;font-family:-apple-system,sans-serif;margin:0}
.top{text-align:center;padding:16px;border-bottom:1px solid #222}
.logo{color:#D4AF37;font-size:26px;font-weight:900;letter-spacing:2px}
.card{background:#0f0f0f;border:1.5px solid #D4AF37;border-radius:16px;padding:14px;margin:12px}
input{width:100%;padding:13px;border-radius:12px;border:1px solid #333;background:#1a1a1a;color:#fff;margin:8px 0}
.btn{width:100%;padding:13px;border-radius:25px;background:#D4AF37;color:#000;border:none;font-weight:900}
</style></head><body>
<div class="top"><div class="logo">PROVE AM</div><a href="/" style="color:#D4AF37;text-decoration:none;font-size:13px">← Back to Feed</a></div>
<div class="card"><h3 style="color:#D4AF37;margin-bottom:8px">👥 Add Friend</h3>
<form method="post"><input name="friend_name" placeholder="Username e.g. Kwame" required><button class="btn">Add Friend</button></form></div>
<div class="card"><h3>Your Friends ({{ friends|length }})</h3>
{% for f in friends %}<div style="padding:12px;border-bottom:1px solid #222">@{{ f['friend_name'] }}</div>
{% else %}<p style="color:#777;font-size:13px">No friends yet. Tell friend to sign up on your link then add their username here.</p>{% endfor %}
</div></body></html>
"""

@app.route('/')
def home():
    if 'user_id' not in session:
        return render_template_string(MAIN_PAGE, posts=[], replies=[], streak=0, longest=0)
    conn = get_db()
    posts = conn.execute('SELECT * FROM posts ORDER BY id DESC').fetchall()
    replies = conn.execute('SELECT * FROM replies ORDER BY id DESC').fetchall()
    count = conn.execute('SELECT COUNT(*) FROM posts WHERE user_id=?',(session['user_id'],)).fetchone()[0]
    conn.close()
    return render_template_string(MAIN_PAGE, posts=posts, replies=replies, streak=count, longest=count)

@app.route('/auth', methods=['POST'])
def auth():
    u = request.form['username'].strip()
    p = request.form['password']
    act = request.form['action']
    conn = get_db()
    if act == 'signup':
        try:
            conn.execute('INSERT INTO users (username,password) VALUES (?,?)',(u, generate_password_hash(p)))
            conn.commit()
        except: pass
    user = conn.execute('SELECT * FROM users WHERE username=?',(u,)).fetchone()
    conn.close()
    if user and check_password_hash(user['password'], p):
        session['user_id'] = user['id']
        session['username'] = user['username']
    return redirect('/')

@app.route('/post', methods=['POST'])
def create_post():
    if 'user_id' not in session: return 'no'
    img = request.files['image']
    cap = request.form.get('caption','')
    fname = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{img.filename}")
    fpath = os.path.join(UPLOAD, fname)
    img.save(fpath)
    conn = get_db()
    conn.execute('INSERT INTO posts (user_id,username,image,caption,timestamp) VALUES (?,?,?,?,?)',
                 (session['user_id'], session['username'], fpath, cap, datetime.now().strftime('%Y-%m-%d %H:%M')))
    conn.commit(); conn.close()
    return 'ok'

@app.route('/delete/<int:pid>')
def delete_post(pid):
    if 'user_id' not in session: return redirect('/')
    conn = get_db()
    conn.execute('DELETE FROM posts WHERE id=? AND user_id=?',(pid, session['user_id']))
    conn.commit(); conn.close()
    return redirect('/')

@app.route('/reply', methods=['POST'])
def create_reply():
    if 'user_id' not in session: return 'no'
    img = request.files['image']
    pid = request.form['post_id']
    fname = secure_filename(f"reply_{datetime.now().strftime('%Y%m%d%H%M%S')}_{img.filename}")
    fpath = os.path.join(UPLOAD, fname)
    img.save(fpath)
    conn = get_db()
    conn.execute('INSERT INTO replies (post_id,user_id,username,image,timestamp) VALUES (?,?,?,?,?)',
                 (pid, session['user_id'], session['username'], fpath, datetime.now().strftime('%Y-%m-%d %H:%M')))
    conn.commit(); conn.close()
    return 'ok'

@app.route('/challenge', methods=['POST'])
def create_challenge():
    if 'user_id' not in session: return 'no'
    to_user = request.form['to_user'].strip()
    txt = request.form['challenge_text'].strip()
    conn = get_db()
    conn.execute('INSERT INTO posts (user_id,username,image,caption,timestamp,challenge_from) VALUES (?,?,?,?,?,?)',
                 (session['user_id'], session['username'], 'static/uploads/logo.jpg', txt, datetime.now().strftime('%Y-%m-%d %H:%M'), f"@{session['username']} → @{to_user} asks"))
    conn.commit(); conn.close()
    return 'ok'

@app.route('/friends', methods=['GET','POST'])
def friends_page():
    if 'user_id' not in session: return redirect('/')
    conn = get_db()
    if request.method == 'POST':
        fname = request.form['friend_name'].strip()
        u = conn.execute('SELECT * FROM users WHERE username=?',(fname,)).fetchone()
        if u:
            try:
                conn.execute('INSERT INTO friends (user_id,friend_name) VALUES (?,?)',(session['user_id'], u['username']))
                conn.commit()
            except: pass
    fr = conn.execute('SELECT * FROM friends WHERE user_id=?',(session['user_id'],)).fetchall()
    conn.close()
    return render_template_string(FRIENDS_PAGE, friends=fr)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
