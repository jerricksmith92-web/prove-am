import os, sqlite3
from flask import Flask, render_template_string, request, redirect, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'proveam_real_streak_final')
UPLOAD = 'static/uploads'
os.makedirs(UPLOAD, exist_ok=True)

def get_db():
    conn = sqlite3.connect('proveam.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY, user_id INTEGER, username TEXT, image TEXT, caption TEXT, timestamp TEXT, challenge_from TEXT, type TEXT DEFAULT "prove")')
    conn.execute('CREATE TABLE IF NOT EXISTS replies (id INTEGER PRIMARY KEY, post_id INTEGER, user_id INTEGER, username TEXT, image TEXT, text TEXT, timestamp TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS friends (id INTEGER PRIMARY KEY, user_id INTEGER, friend_name TEXT)')
    conn.commit(); conn.close()
init_db()

PAGE = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PROVE AM</title><link rel="manifest" href="/manifest.json"><meta name="theme-color" content="#D4AF37">
<style>
*{margin:0;padding:0;box-sizing:border-box} body{background:#000;color:#fff;font-family:-apple-system,sans-serif}
.top{position:sticky;top:0;z-index:10;background:#000;border-bottom:1px solid #151515;padding:12px 0 8px;text-align:center}
.logo-circle{width:62px;height:62px;border-radius:50%;border:2.5px solid #D4AF37;background:radial-gradient(circle,#FFD700,#8B7500);display:flex;align-items:center;justify-content:center;margin:0 auto 6px;font-weight:900;color:#000;font-size:22px;overflow:hidden}
.logo-text{color:#D4AF37;font-size:28px;font-weight:900;letter-spacing:2px}
.sub{color:#888;font-size:12px}
.install{display:none;background:#D4AF37;color:#000;border:none;padding:8px 14px;border-radius:20px;font-weight:800;font-size:12px;margin:8px auto 0;cursor:pointer}
.card{background:#0f0f0f;border:1.5px solid #D4AF37;border-radius:16px;padding:14px;margin:11px}
.flex{display:flex;justify-content:space-between;align-items:center}
.gold{color:#D4AF37}.small{color:#777;font-size:11px}
input{width:100%;padding:13px;border-radius:12px;border:1px solid #2a2a2a;background:#1a1a1a;color:#fff;margin:6px 0;font-size:13px;outline:none}
.btn{width:100%;padding:13px;border-radius:25px;border:none;font-weight:900;font-size:13px;margin-top:8px;cursor:pointer}
.btn-gold{background:#D4AF37;color:#000}.btn-dark{background:#1f1f1f;color:#fff;border:1px solid #333}
#video{width:100%;height:48vh;background:#000;border-radius:12px;object-fit:cover;display:block}
.post-img{width:100%;border-radius:12px;margin-top:8px;display:block}
.actions{display:flex;gap:6px;margin-top:10px;flex-wrap:wrap}
.act{flex:1;padding:9px 4px;border-radius:18px;text-align:center;font-size:11px;text-decoration:none;border:1px solid #333;background:#1e1e1e;color:#fff;cursor:pointer;min-width:60px}
.del{background:#251010;border-color:#5a2222;color:#ff7a7a}.dl{background:#102116;border-color:#204d2a;color:#7dff9f}
.text-reply-box{display:flex;gap:6px;margin-top:8px}.text-reply-box input{flex:1;margin:0}
.streak-fire{font-size:16px}
</style></head><body>
<div class="top">
<div class="logo-circle"><img src="/static/uploads/logo.jpg" onerror="this.style.display='none';document.getElementById('paText').style.display='block'" style="width:100%;height:100%;object-fit:cover"><span id="paText" style="display:none">PA</span></div>
<div class="logo-text">PROVE AM</div>
<div class="sub">@{{ session.get('username','Guest') }}</div>
<button id="installBtn" class="install">📲 Install PROVE AM</button>
<div id="iosHint" style="display:none;color:#D4AF37;font-size:11px;margin-top:5px">iPhone: Tap ⎙ then Add to Home Screen</div>
</div>

{% if not session.get('user_id') %}
<div class="card"><h3 style="color:#D4AF37;text-align:center">Join PROVE AM 🇬🇭</h3>
<form method="post" action="/auth"><input name="username" placeholder="Username" required><input name="password" type="password" placeholder="Password" required><button class="btn btn-gold" name="action" value="signup">SIGN UP</button><button class="btn btn-dark" name="action" value="login">LOGIN</button></form></div>
{% else %}

<div class="card flex"><div><div style="font-weight:800" class="streak-fire">🔥 Streak: <span class="gold">{{ streak }} days</span></div><div class="small">Longest: {{ longest }} days | Total Posts: {{ total }}</div></div><a href="/friends" style="color:#D4AF37;text-decoration:none">👥 Friends</a></div>

<div class="card"><input id="to_user" placeholder="Challenge who? (username)"><input id="challenge_text" placeholder="Ask them to prove... e.g. Prove you dey gym!"><button class="btn btn-gold" onclick="doChallenge()">⚡ ASK TO PROVE AM</button></div>

<div class="card"><div style="color:#D4AF37;font-weight:800;margin-bottom:8px">📸 PROVE AM NOW</div><video id="video" autoplay playsinline muted></video><input type="file" id="fileInput" accept="image/*" capture="environment" style="display:none"><canvas id="canvas" style="display:none"></canvas><input id="caption" placeholder="What you dey prove?"><button class="btn btn-gold" onclick="doCapture()">📸 CAPTURE & PROVE</button><button class="btn btn-dark" onclick="doTextPost()">💬 POST TEXT ONLY</button><button class="btn btn-dark" onclick="document.getElementById('fileInput').click()">📁 Gallery (Fix Black Camera)</button></div>

{% for p in posts %}
<div class="card"><div class="flex"><b>@{{ p['username'] }}</b><span class="small">{{ p['timestamp'] }}</span></div>
{% if p['challenge_from'] %}<div style="background:#D4AF37;color:#000;padding:7px 10px;border-radius:9px;margin:8px 0;font-size:12px;font-weight:700">{{ p['challenge_from'] }}: {{ p['caption'] }}</div>
{% else %}<div style="margin:8px 0;font-size:13px;white-space:pre-wrap">{{ p['caption'] }}</div>{% endif %}
{% if p['image'] and 'logo.jpg' not in p['image'] %}<img src="/{{ p['image'] }}" class="post-img">{% endif %}
<div class="actions"><button class="act" onclick="doReply({{ p['id'] }})">📸 Reply</button><button class="act" onclick="document.getElementById('text-{{ p['id'] }}').style.display='flex'">💬 Text</button><a class="act dl" href="/{{ p['image'] }}" download>⬇️ Download</a>{% if p['user_id']==session['user_id'] %}<a class="act del" href="/delete/{{ p['id'] }}">🗑️ Delete</a>{% endif %}</div>
<div id="text-{{ p['id'] }}" class="text-reply-box" style="display:none"><input id="input-{{ p['id'] }}" placeholder="Type text reply..."><button class="act btn-gold" style="flex:0.4" onclick="doTextReply({{ p['id'] }})">Send</button></div>
{% for r in replies if r['post_id']==p['id'] %}<div style="margin-top:10px;background:#151515;padding:9px;border-radius:10px;border-left:2px solid #D4AF37"><div class="small">@{{ r['username'] }} replied:</div>{% if r['text'] %}<div style="font-size:13px;margin:4px 0">{{ r['text'] }}</div>{% endif %}{% if r['image'] %}<img src="/{{ r['image'] }}" style="width:100%;border-radius:8px;margin-top:4px">{% endif %}<div class="small">{{ r['timestamp'] }}</div></div>{% endfor %}
</div>
{% endfor %}
{% endif %}

<script>
let deferredPrompt; window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();deferredPrompt=e;document.getElementById('installBtn').style.display='block';});
document.getElementById('installBtn').addEventListener('click',async()=>{if(deferredPrompt){deferredPrompt.prompt();await deferredPrompt.userChoice;deferredPrompt=null;document.getElementById('installBtn').style.display='none';}});
if(/iPhone|iPad|iPod/.test(navigator.userAgent)&&!window.navigator.standalone){document.getElementById('iosHint').style.display='block';}
if('serviceWorker' in navigator){navigator.serviceWorker.register('/sw.js').catch(()=>{});}
async function initCam(){try{const s=await navigator.mediaDevices.getUserMedia({video:{facingMode:"environment"}});const v=document.getElementById('video');if(v){v.srcObject=s;v.setAttribute('playsinline','');await v.play()}}catch(e){}} initCam();
function doCapture(){const v=document.getElementById('video');const c=document.getElementById('canvas');if(!v||v.videoWidth===0){document.getElementById('fileInput').click();return;}c.width=v.videoWidth;c.height=v.videoHeight;c.getContext('2d').drawImage(v,0,0);c.toBlob(b=>{const fd=new FormData();fd.append('image',b,'prove.jpg');fd.append('caption',document.getElementById('caption').value);fetch('/post',{method:'POST',body:fd}).then(()=>location.reload())},'image/jpeg',0.85);}
function doTextPost(){const t=document.getElementById('caption').value.trim();if(!t){alert('Type something');return;}const fd=new FormData();fd.append('caption',t);fd.append('type','text');fetch('/post',{method:'POST',body:fd}).then(()=>location.reload());}
document.getElementById('fileInput').addEventListener('change',function(){if(!this.files[0])return;const fd=new FormData();fd.append('image',this.files[0]);fd.append('caption',document.getElementById('caption').value);fetch('/post',{method:'POST',body:fd}).then(()=>location.reload());});
function doReply(id){const i=document.getElementById('fileInput');i.onchange=function(){const fd=new FormData();fd.append('image',this.files[0]);fd.append('post_id',id);fetch('/reply',{method:'POST',body:fd}).then(()=>location.reload())};i.click();}
function doTextReply(id){const inp=document.getElementById('input-'+id);const txt=inp.value.trim();if(!txt)return;const fd=new FormData();fd.append('post_id',id);fd.append('text',txt);fetch('/reply_text',{method:'POST',body:fd}).then(()=>location.reload());}
function doChallenge(){const to=document.getElementById('to_user').value.trim();const txt=document.getElementById('challenge_text').value.trim();if(!to||!txt){alert('Fill both');return;}const fd=new FormData();fd.append('to_user',to);fd.append('challenge_text',txt);fetch('/challenge',{method:'POST',body:fd}).then(()=>location.reload());}
</script></body></html>
"""

FRIENDS_HTML = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Friends</title>
<style>body{background:#000;color:#fff;font-family:sans-serif;margin:0}.top{text-align:center;padding:16px;border-bottom:1px solid #222}.logo{color:#D4AF37;font-size:26px;font-weight:900}.card{background:#0f0f0f;border:1.5px solid #D4AF37;border-radius:16px;padding:14px;margin:12px}input{width:100%;padding:13px;border-radius:12px;border:1px solid #333;background:#1a1a1a;color:#fff;margin:8px 0}.btn{width:100%;padding:13px;border-radius:25px;background:#D4AF37;color:#000;border:none;font-weight:900}</style></head><body>
<div class="top"><div class="logo">PROVE AM</div><a href="/" style="color:#D4AF37;text-decoration:none">← Back</a></div>
<div class="card"><form method="post"><input name="friend_name" placeholder="Username" required><button class="btn">Add Friend</button></form></div>
<div class="card"><h3>Friends ({{ friends|length }})</h3>{% for f in friends %}<div style="padding:12px;border-bottom:1px solid #222">@{{ f['friend_name'] }}</div>{% else %}<p style="color:#777">No friends</p>{% endfor %}</div></body></html>
"""

@app.route('/')
def home():
    if 'user_id' not in session:
        return render_template_string(PAGE, posts=[], replies=[], streak=0, longest=0, total=0)
    conn = get_db()
    posts = conn.execute('SELECT * FROM posts ORDER BY id DESC').fetchall()
    replies = conn.execute('SELECT * FROM replies ORDER BY id DESC').fetchall()
    # REAL STREAK CALCULATION
    rows = conn.execute('SELECT DATE(timestamp) as d FROM posts WHERE user_id=? GROUP BY DATE(timestamp) ORDER BY d DESC', (session['user_id'],)).fetchall()
    total_posts = conn.execute('SELECT COUNT(*) FROM posts WHERE user_id=?', (session['user_id'],)).fetchone()[0]
    streak = 0
    longest_days = len(rows)
    if rows:
        try:
            last_date = datetime.strptime(rows[0]['d'], '%Y-%m-%d').date()
            today = date.today()
            diff = (today - last_date).days
            if diff <= 1: # posted today or yesterday = streak alive
                streak = 1
                for i in range(1, len(rows)):
                    prev = datetime.strptime(rows[i-1]['d'], '%Y-%m-%d').date()
                    curr = datetime.strptime(rows[i]['d'], '%Y-%m-%d').date()
                    if (prev - curr).days == 1:
                        streak += 1
                    else:
                        break
            else:
                streak = 0
        except Exception as e:
            streak = len(rows) if rows else 0
    conn.close()
    return render_template_string(PAGE, posts=posts, replies=replies, streak=streak, longest=longest_days, total=total_posts)

@app.route('/manifest.json')
def manifest():
    return jsonify({"name":"PROVE AM","short_name":"PROVE AM","start_url":"/","display":"standalone","background_color":"#000000","theme_color":"#D4AF37","icons":[{"src":"/static/uploads/logo.jpg","sizes":"192x192","type":"image/jpeg"}]})

@app.route('/sw.js')
def sw():
    return "self.addEventListener('install',e=>self.skipWaiting())", 200, {'Content-Type':'application/javascript'}

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
def create_post():
    if 'user_id' not in session: return 'no'
    caption=request.form.get('caption','').strip()
    img=request.files.get('image')
    fpath=''; ptype=request.form.get('type','prove')
    if img and img.filename!='':
        fname=secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{img.filename}")
        fpath=os.path.join(UPLOAD,fname); img.save(fpath)
    else:
        if caption=='' : return 'no content'
        fpath='static/uploads/logo.jpg'
        ptype='text'
    conn=get_db(); conn.execute('INSERT INTO posts (user_id,username,image,caption,timestamp,type) VALUES (?,?,?,?,?,?)',(session['user_id'],session['username'],fpath,caption,datetime.now().strftime('%Y-%m-%d %H:%M'),ptype)); conn.commit(); conn.close()
    return 'ok'

@app.route('/delete/<int:pid>')
def delete_post(pid):
    if 'user_id' not in session: return redirect('/')
    conn=get_db(); conn.execute('DELETE FROM posts WHERE id=? AND user_id=?',(pid,session['user_id'])); conn.commit(); conn.close()
    return redirect('/')

@app.route('/reply', methods=['POST'])
def reply_img():
    if 'user_id' not in session: return 'no'
    img=request.files.get('image'); pid=request.form.get('post_id')
    if not img: return 'no'
    fname=secure_filename(f"reply_{datetime.now().strftime('%Y%m%d%H%M%S')}_{img.filename}")
    fpath=os.path.join(UPLOAD,fname); img.save(fpath)
    conn=get_db(); conn.execute('INSERT INTO replies (post_id,user_id,username,image,timestamp) VALUES (?,?,?,?,?)',(pid,session['user_id'],session['username'],fpath,datetime.now().strftime('%Y-%m-%d %H:%M'))); conn.commit(); conn.close()
    return 'ok'

@app.route('/reply_text', methods=['POST'])
def reply_text():
    if 'user_id' not in session: return 'no'
    txt=request.form.get('text','').strip(); pid=request.form.get('post_id')
    if not txt: return 'no'
    conn=get_db(); conn.execute('INSERT INTO replies (post_id,user_id,username,text,timestamp) VALUES (?,?,?,?,?)',(pid,session['user_id'],session['username'],txt,datetime.now().strftime('%Y-%m-%d %H:%M'))); conn.commit(); conn.close()
    return 'ok'

@app.route('/challenge', methods=['POST'])
def challenge():
    if 'user_id' not in session: return 'no'
    to_user=request.form['to_user'].strip(); txt=request.form['challenge_text'].strip()
    conn=get_db(); conn.execute('INSERT INTO posts (user_id,username,image,caption,timestamp,challenge_from,type) VALUES (?,?,?,?,?,?,?)',(session['user_id'],session['username'],'static/uploads/logo.jpg',txt,datetime.now().strftime('%Y-%m-%d %H:%M'),f"@{session['username']} → @{to_user} asks",'challenge')); conn.commit(); conn.close()
    return 'ok'

@app.route('/friends', methods=['GET','POST'])
def friends():
    if 'user_id' not in session: return redirect('/')
    conn=get_db()
    if request.method=='POST':
        fname=request.form['friend_name'].strip()
        u=conn.execute('SELECT * FROM users WHERE username=?',(fname,)).fetchone()
        if u:
            try: conn.execute('INSERT INTO friends (user_id,friend_name) VALUES (?,?)',(session['user_id'],u['username'])); conn.commit()
            except: pass
    fr=conn.execute('SELECT * FROM friends WHERE user_id=?',(session['user_id'],)).fetchall(); conn.close()
    return render_template_string(FRIENDS_HTML, friends=fr)

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
