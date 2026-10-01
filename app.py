import os
from flask import Flask, render_template_string, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import sqlite3

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'proveam_ghana_gold_2026')
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db():
    conn = sqlite3.connect('proveam.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY, user_id INTEGER, username TEXT, image TEXT, caption TEXT, timestamp TEXT, challenge_from TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS replies (id INTEGER PRIMARY KEY, post_id INTEGER, user_id INTEGER, username TEXT, image TEXT, timestamp TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS friends (id INTEGER PRIMARY KEY, user_id INTEGER, friend_id INTEGER, friend_name TEXT)')
    conn.commit(); conn.close()
init_db()

MAIN = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>PROVE AM</title>
<style>
body{background:#000;color:#fff;font-family:sans-serif;margin:0}
.header{text-align:center;padding:15px;border-bottom:1px solid #222;background:#000;position:sticky;top:0}
.logo{color:#D4AF37;font-size:28px;font-weight:900}
.card{background:#111;border:1px solid #333;border-radius:15px;padding:15px;margin:15px}
.btn-gold{background:#D4AF37;color:#000;border:none;padding:12px;border-radius:25px;font-weight:800;width:100%;margin:5px 0}
.btn-dark{background:#222;color:#fff;border:1px solid #444;padding:12px;border-radius:25px;width:100%;margin:5px 0}
.post-img{width:100%;border-radius:12px;margin-top:10px}
input{width:100%;padding:12px;border-radius:10px;border:1px solid #333;background:#111;color:#fff;margin:8px 0}
#video{width:100%;height:50vh;background:#000;border-radius:15px;object-fit:cover}
</style></head><body>
<div class="header"><div class="logo">PROVE AM</div><small>@{{ session.get('username','') }}</small></div>
{% if not session.get('user_id') %}
<div class="card"><form method="post" action="/auth"><input name="username" placeholder="Username" required><input name="password" type="password" placeholder="Password" required><button class="btn-gold" name="action" value="signup">SIGN UP</button><button class="btn-dark" name="action" value="login">LOGIN</button></form></div>
{% else %}
<div class="card"><b>Streak: {{ streak }} days</b> | <a href="/friends" style="color:#D4AF37">Friends</a></div>
<div class="card"><form method="post" action="/challenge"><input name="to_user" placeholder="Challenge who?" required><input name="challenge_text" placeholder="Prove you dey gym!" required><button class="btn-gold">ASK TO PROVE AM</button></form></div>
<div class="card"><h4 style="color:#D4AF37">PROVE AM NOW</h4><video id="video" autoplay playsinline muted></video><input type="file" id="fileInput" accept="image/*" capture="environment" style="display:none"><canvas id="canvas" style="display:none"></canvas><input id="cap" placeholder="Caption"><button class="btn-gold" onclick="doCap()">CAPTURE & PROVE</button><button class="btn-dark" onclick="document.getElementById('fileInput').click()">📁 Gallery (iPhone Fix)</button></div>
{% for p in posts %}<div class="card"><b>@{{ p['username'] }}</b> <small>{{ p['timestamp'] }}</small>{% if p['challenge_from'] %}<div style="background:#D4AF37;color:#000;padding:6px;border-radius:8px;margin:8px 0">{{ p['challenge_from'] }}: {{ p['caption'] }}</div>{% else %}<div>{{ p['caption'] }}</div>{% endif %}<img src="/{{ p['image'] }}" class="post-img"><div style="display:flex;gap:8px;margin-top:10px"><button class="btn-dark" onclick="reply({{ p['id'] }})">Reply</button>{% if p['user_id']==session['user_id'] %}<a href="/delete/{{ p['id'] }}" style="background:#440000;color:#fff;padding:12px;border-radius:25px;text-decoration:none;flex:1;text-align:center">Delete</a>{% endif %}</div>{% for r in replies if r['post_id']==p['id'] %}<div style="background:#0a0a0a;padding:8px;border-radius:8px;margin-top:8px;border-left:2px solid #D4AF37">@{{ r['username'] }} replied<br><img src="/{{ r['image'] }}" style="width:100%;border-radius:8px"><small>{{ r['timestamp'] }}</small></div>{% endfor %}</div>{% endfor %}{% endif %}
<script>
async function start(){try{let s=await navigator.mediaDevices.getUserMedia({video:{facingMode:"environment"}});let v=document.getElementById('video');if(v){v.srcObject=s;v.setAttribute('playsinline','');v.play()}}catch(e){}} start();
function doCap(){let v=document.getElementById('video');let c=document.getElementById('canvas');if(!v||v.videoWidth==0){document.getElementById('fileInput').click();return;}c.width=v.videoWidth;c.height=v.videoHeight;c.getContext('2d').drawImage(v,0,0);c.toBlob(b=>{let fd=new FormData();fd.append('image',b,'p.jpg');fd.append('caption',document.getElementById('cap').value);fetch('/post',{method:'POST',body:fd}).then(()=>location.reload())},'image/jpeg',0.8)}
document.getElementById('fileInput').addEventListener('change',function(){let fd=new FormData();fd.append('image',this.files[0]);fd.append('caption',document.getElementById('cap')?document.getElementById('cap').value:'');fetch('/post',{method:'POST',body:fd}).then(()=>location.reload())});
function reply(id){let i=document.getElementById('fileInput');i.onchange=function(){let fd=new FormData();fd.append('image',this.files[0]);fd.append('post_id',id);fetch('/reply',{method:'POST',body:fd}).then(()=>location.reload())};i.click()}
</script></body></html>
"""

FRIENDS = """
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"><title>Friends</title><style>body{background:#000;color:#fff;font-family:sans-serif}.card{background:#111;border:1px solid #D4AF37;border-radius:15px;padding:15px;margin:15px}input{width:100%;padding:12px;border-radius:10px;border:1px solid #333;background:#111;color:#fff;margin:8px 0}.btn{background:#D4AF37;color:#000;padding:12px;border-radius:25px;width:100%;border:none;font-weight:800}</style></head><body>
<div style="text-align:center;padding:15px"><h2 style="color:#D4AF37">PROVE AM</h2><a href="/" style="color:#D4AF37">Back</a></div>
<div class="card"><form method="post"><input name="friend_name" placeholder="Username" required><button class="btn">Add Friend</button></form></div>
<div class="card">{% for f in friends %}<div style="padding:10px;border-bottom:1px solid #222">@{{ f['friend_name'] }}</div>{% else %}<p>No friends yet</p>{% endfor %}</div></body></html>
"""

@app.route('/')
def home():
    if 'user_id' not in session:
        return render_template_string(MAIN, posts=[], replies=[], streak=0)
    conn=get_db(); posts=conn.execute('SELECT * FROM posts ORDER BY id DESC').fetchall(); replies=conn.execute('SELECT * FROM replies ORDER BY id DESC').fetchall(); streak=len(conn.execute('SELECT * FROM posts WHERE user_id=?',(session['user_id'],)).fetchall()); conn.close()
    return render_template_string(MAIN, posts=posts, replies=replies, streak=streak)

@app.route('/auth', methods=['POST'])
def auth():
    u=request.form['username'].strip(); p=request.form['password']; act=request.form['action']
    conn=get_db()
    if act=='signup':
        try: conn.execute('INSERT INTO users (username,password) VALUES (?,?)',(u,generate_password_hash(p))); conn.commit()
        except: pass
    user=conn.execute('SELECT * FROM users WHERE username=?',(u,)).fetchone(); conn.close()
    if user and check_password_hash(user['password'],p):
        session['user_id']=user['id']; session['username']=user['username']
    return redirect('/')

@app.route('/post', methods=['POST'])
def post_route():
    if 'user_id' not in session: return 'no'
    img=request.files['image']; cap=request.form.get('caption','')
    fname=secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{img.filename}")
    path=os.path.join(UPLOAD_FOLDER,fname); img.save(path)
    conn=get_db(); conn.execute('INSERT INTO posts (user_id,username,image,caption,timestamp) VALUES (?,?,?,?,?)',(session['user_id'],session['username'],path,cap,datetime.now().strftime('%Y-%m-%d %H:%M'))); conn.commit(); conn.close()
    return 'ok'

@app.route('/delete/<int:pid>')
def delete(pid):
    conn=get_db(); conn.execute('DELETE FROM posts WHERE id=? AND user_id=?',(pid,session['user_id'])); conn.commit(); conn.close()
    return redirect('/')

@app.route('/reply', methods=['POST'])
def reply_route():
    img=request.files['image']; pid=request.form['post_id']
    fname=secure_filename(f"r_{datetime.now().strftime('%Y%m%d%H%M%S')}_{img.filename}")
    path=os.path.join(UPLOAD_FOLDER,fname); img.save(path)
    conn=get_db(); conn.execute('INSERT INTO replies (post_id,user_id,username,image,timestamp) VALUES (?,?,?,?,?)',(pid,session['user_id'],session['username'],path,datetime.now().strftime('%Y-%m-%d %H:%M'))); conn.commit(); conn.close()
    return 'ok'

@app.route('/challenge', methods=['POST'])
def challenge():
    to_user=request.form['to_user']; txt=request.form['challenge_text']
    conn=get_db(); conn.execute('INSERT INTO posts (user_id,username,image,caption,timestamp,challenge_from) VALUES (?,?,?,?,?,?)',(session['user_id'],session['username'],'static/uploads/logo.jpg',txt,datetime.now().strftime('%Y-%m-%d %H:%M'),f"@{session['username']} -> @{to_user} asks")); conn.commit(); conn.close()
    return redirect('/')

@app.route('/friends', methods=['GET','POST'])
def friends_route():
    if 'user_id' not in session: return redirect('/')
    conn=get_db()
    if request.method=='POST':
        fname=request.form['friend_name'].strip()
        u=conn.execute('SELECT * FROM users WHERE username=?',(fname,)).fetchone()
        if u:
            try: conn.execute('INSERT INTO friends (user_id,friend_id,friend_name) VALUES (?,?,?)',(session['user_id'],u['id'],u['username'])); conn.commit()
            except: pass
    fr=conn.execute('SELECT * FROM friends WHERE user_id=?',(session['user_id'],)).fetchall(); conn.close()
    return render_template_string(FRIENDS, friends=fr)

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
