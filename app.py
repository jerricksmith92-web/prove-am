import os
from flask import Flask, request, jsonify, send_from_directory, render_template_string, session, redirect
from datetime import datetime, timedelta, date
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "proveam-social-v2-postgres-gold-2026"
DB_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = bool(DB_URL)
DB = "proveam.db"

def get_conn():
    if USE_POSTGRES:
        import psycopg2
        conn = psycopg2.connect(DB_URL)
        return conn
    else:
        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("CREATE TABLE IF NOT EXISTS auth (username TEXT PRIMARY KEY, password TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, streak INT, last_date TEXT, longest INT)")
        c.execute("CREATE TABLE IF NOT EXISTS friends (id SERIAL PRIMARY KEY, user1 TEXT, user2 TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS challenges (id SERIAL PRIMARY KEY, from_user TEXT, to_user TEXT, task TEXT, created_at TEXT, status TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS posts (id SERIAL PRIMARY KEY, username TEXT, media TEXT, media_type TEXT, task TEXT, challenge_from TEXT, likes INT DEFAULT 0, created_at TEXT, expires_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS likes (id SERIAL PRIMARY KEY, post_id INT, username TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS replies (id SERIAL PRIMARY KEY, post_id INT, username TEXT, text TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS stories (id SERIAL PRIMARY KEY, username TEXT, media TEXT, media_type TEXT, created_at TEXT, expires_at TEXT, views INT DEFAULT 0)")
        c.execute("CREATE TABLE IF NOT EXISTS chats (id SERIAL PRIMARY KEY, sender TEXT, receiver TEXT, text TEXT, media TEXT, media_type TEXT, created_at TEXT)")
    else:
        c.execute("CREATE TABLE IF NOT EXISTS auth (username TEXT PRIMARY KEY, password TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, streak INTEGER, last_date TEXT, longest INTEGER)")
        c.execute("CREATE TABLE IF NOT EXISTS friends (id INTEGER PRIMARY KEY AUTOINCREMENT, user1 TEXT, user2 TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS challenges (id INTEGER PRIMARY KEY AUTOINCREMENT, from_user TEXT, to_user TEXT, task TEXT, created_at TEXT, status TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, media TEXT, media_type TEXT, task TEXT, challenge_from TEXT, likes INTEGER DEFAULT 0, created_at TEXT, expires_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS likes (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, username TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS replies (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, username TEXT, text TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS stories (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, media TEXT, media_type TEXT, created_at TEXT, expires_at TEXT, views INTEGER DEFAULT 0)")
        c.execute("CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, receiver TEXT, text TEXT, media TEXT, media_type TEXT, created_at TEXT)")
    conn.commit()
    conn.close()
init_db()

# ---------- HTML ----------
BASE_STYLE = """
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}
body{background:#000;color:#fff}
.header{text-align:center;padding:12px;border-bottom:1px solid #222;position:sticky;top:0;background:#000;z-index:10}
.logo{width:60px;height:60px;border-radius:50%;border:2px solid #D4AF37}
.gold{color:#D4AF37}
.top-links{display:flex;gap:6px;justify-content:center;margin-top:6px;flex-wrap:wrap}
.top-links a{color:#888;font-size:10px;border:1px solid #333;padding:5px 10px;border-radius:20px;text-decoration:none}
.card{background:#111;border:1px solid #222;border-radius:16px;overflow:hidden;margin:10px}
.btn{padding:10px 14px;border-radius:12px;border:none;font-weight:800;cursor:pointer}
.btn-gold{background:#D4AF37;color:#000}
.btn-dark{background:#222;color:#fff;border:1px solid #444}
input,textarea{width:100%;padding:12px;background:#000;border:1px solid #333;color:#fff;border-radius:10px;margin:6px 0}
.story-bar{display:flex;gap:10px;overflow-x:auto;padding:10px;border-bottom:1px solid #222}
.story-circle{min-width:60px;text-align:center}
.story-circle div{width:55px;height:55px;border-radius:50%;border:2px solid #D4AF37;background:#111;display:flex;align-items:center;justify-content:center;font-size:10px}
</style>
"""

LOGIN_HTML = f"""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>PROVE AM</title>{BASE_STYLE}
<style>body{{display:flex;justify-content:center;align-items:center;height:100vh}}.box{{background:#111;border:1px solid #222;padding:25px;border-radius:16px;width:90%;max-width:350px;text-align:center}}</style></head><body>
<div class="box"><div style="width:80px;height:80px;border-radius:50%;border:2px solid #D4AF37;margin:0 auto;display:flex;align-items:center;justify-content:center;font-weight:900;color:#D4AF37">PROVE</div><h1 class="gold" style="margin:10px 0">PROVE AM</h1><h3 id="title">Login</h3>
<input id="u" placeholder="Username"><input id="p" type="password" placeholder="Password"><button class="btn btn-gold" style="width:100%;margin-top:10px" onclick="doAuth()">Continue</button>
<p style="margin-top:12px"><a href="#" onclick="toggleMode()" id="toggleLink" style="color:#D4AF37;font-size:12px">No account? Sign Up</a> • <a href="/forgot" style="color:#D4AF37;font-size:12px">Forgot?</a></p><p id="msg" style="color:#f55;font-size:12px;margin-top:8px"></p></div>
<script>
let mode='login';function toggleMode(){{mode=mode=='login'?'signup':'login';document.getElementById('title').innerText=mode=='login'?'Login':'Sign Up';document.getElementById('toggleLink').innerText=mode=='login'?'No account? Sign Up':'Have account? Login'}}
async function doAuth(){{let u=document.getElementById('u').value,p=document.getElementById('p').value;if(!u||!p){{document.getElementById('msg').innerText='Fill all';return;}}
let r=await fetch('/'+mode,{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{username:u,password:p}})}});let d=await r.json();if(d.ok)location.href='/';else document.getElementById('msg').innerText=d.error;}}
</script></body></html>"""

FORGOT_HTML = f"""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Forgot</title>{BASE_STYLE}
<style>body{{display:flex;justify-content:center;align-items:center;height:100vh}}.box{{background:#111;border:1px solid #222;padding:25px;border-radius:16px;width:90%;max-width:350px;text-align:center}}</style></head><body>
<div class="box"><h1 class="gold">Reset Password</h1><input id="u" placeholder="Username"><input id="p" type="password" placeholder="New Password"><button class="btn btn-gold" style="width:100%" onclick="resetPw()">Reset</button><p id="msg" style="font-size:12px;margin-top:10px"></p><p style="margin-top:15px"><a href="/login" style="color:#D4AF37">Back</a></p></div>
<script>async function resetPw(){{let u=document.getElementById('u').value,p=document.getElementById('p').value;let r=await fetch('/forgot',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{username:u,password:p}})}});let d=await r.json();document.getElementById('msg').innerText=d.ok?'✅ Changed! Go login':'❌ '+d.error;}}</script></body></html>"""

MAIN_HTML = f"""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>PROVE AM</title>{BASE_STYLE}</head><body>
<div class="header"><h1 class="gold">PROVE AM</h1><div style="color:#666;font-size:11px">@{{{{username}}}} • 🔥 <span id="streak">0</span> days | 👑 Longest: <span id="longest">0</span></div>
<div class="top-links"><a href="/friends">👥 Friends</a><a href="/chats">💬 Chats</a><a href="/profile">👤 Profile</a><a href="/logout">Logout</a></div></div>

<div class="story-bar" id="storyBar">Loading stories...</div>

<div class="card" style="padding:12px"><h4 class="gold">Challenge who? (username)</h4><input id="challengeTo" placeholder="e.g. jerrick">
<h4 class="gold" style="margin-top:8px">Ask them to prove...</h4><input id="challengeTask" placeholder="e.g. Prove you dey gym!">
<button class="btn btn-gold" style="width:100%;margin-top:8px" onclick="sendChallenge()">ASK TO PROVE AM</button><p id="chMsg" style="font-size:11px;margin-top:6px"></p></div>

<div class="card" style="padding:12px"><h4 class="gold">PROVE AM NOW 📸🎥</h4>
<div style="display:flex;gap:8px;margin:8px 0"><button class="btn btn-dark" onclick="startCamera('photo')">📸 Photo</button><button class="btn btn-dark" onclick="startCamera('video')">🎥 Video (30s)</button><button class="btn btn-dark" onclick="document.getElementById('fileIn').click()">🖼️ Gallery</button></div>
<video id="video" autoplay playsinline muted style="width:100%;display:none;border-radius:12px"></video><canvas id="canvas" style="display:none"></canvas>
<div id="camActions" style="display:none;gap:8px;margin-top:8px"><button class="btn btn-gold" onclick="capture()">CAPTURE / STOP RECORD</button><button class="btn btn-dark" onclick="stopCamera()">Cancel</button></div>
<input type="file" id="fileIn" accept="image/*,video/*" style="display:none"><p style="font-size:10px;color:#666">Video auto-deletes after 24h like Snapchat</p></div>

<div id="feed">Loading feed...</div>

<script>
let stream=null,mediaRecorder=null,chunks=[],mode='photo';
async function startCamera(m){{mode=m;let v=document.getElementById('video');try{{stream=await navigator.mediaDevices.getUserMedia({{video:true,audio:m=='video'}});v.srcObject=stream;v.style.display='block';document.getElementById('camActions').style.display='flex';
if(m=='video'){{chunks=[];mediaRecorder=new MediaRecorder(stream);mediaRecorder.ondataavailable=e=>chunks.push(e.data);mediaRecorder.onstop=()=>{{let blob=new Blob(chunks,{{type:'video/webm'}});let r=new FileReader();r.onload=e=>upload(e.target.result,'video');r.readAsDataURL(blob);}};mediaRecorder.start();setTimeout(()=>{{if(mediaRecorder&&mediaRecorder.state=='recording')mediaRecorder.stop();}},30000);}}
}}catch(e){{alert('Camera needed')}}}}
function stopCamera(){{if(mediaRecorder&&mediaRecorder.state=='recording')mediaRecorder.stop();if(stream)stream.getTracks().forEach(t=>t.stop());document.getElementById('video').style.display='none';document.getElementById('camActions').style.display='none'}}
function capture(){{if(mode=='video'){{if(mediaRecorder&&mediaRecorder.state=='recording')mediaRecorder.stop();stopCamera();return;}}let v=document.getElementById('video'),c=document.getElementById('canvas');c.width=v.videoWidth;c.height=v.videoHeight;c.getContext('2d').drawImage(v,0,0);upload(c.toDataURL('image/jpeg',0.6),'image');stopCamera();}}
document.getElementById('fileIn').addEventListener('change',e=>{{let f=e.target.files[0];if(!f)return;let r=new FileReader();r.onload=ev=>{{let type=f.type.startsWith('video')?'video':'image';upload(ev.target.result,type);}};r.readAsDataURL(f);}});
async function upload(media,media_type){{let res=await fetch('/upload',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{media,media_type}})}});let d=await res.json();if(d.ok){{loadFeed();loadStories();loadStreak();}}else alert(d.error)}}
async function sendChallenge(){{let to=document.getElementById('challengeTo').value,task=document.getElementById('challengeTask').value;if(!to||!task){{document.getElementById('chMsg').innerText='Fill both';return;}}let r=await fetch('/challenge',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{to_user:to,task}})}});let d=await r.json();document.getElementById('chMsg').innerText=d.ok?'✅ Challenge sent to @'+to:'❌ '+d.error;}}
async function loadStreak(){{let r=await fetch('/streak');let d=await r.json();document.getElementById('streak').innerText=d.streak;document.getElementById('longest').innerText=d.longest;}}
async function loadStories(){{let r=await fetch('/stories');let stories=await r.json();document.getElementById('storyBar').innerHTML=stories.length==0?'<span style="color:#666;font-size:11px">No stories — post a proof to add</span>':stories.map(s=>`<div class="story-circle" onclick="viewStory(${{s.id}})"><div>${{s.media_type=='video'?'🎥':'📸'}}<br>${{s.username}}</div><small style="font-size:9px">${{s.username}}</small></div>`).join('');}}
async function loadFeed(){{let r=await fetch('/feed');let posts=await r.json();document.getElementById('feed').innerHTML=posts.map(p=>`<div class="card"><div style="padding:8px 10px;display:flex;justify-content:space-between;font-size:12px"><b>@${{p.username}}</b><span style="color:#666">${{p.task?p.task:'PROVE AM'}} • ${{p.created_at}}</span></div>
${{p.media_type=='video'?`<video src="${{p.media}}" controls style="width:100%"></video>`:`<img src="${{p.media}}" style="width:100%">`}}
<div style="padding:8px 10px;display:flex;gap:10px;font-size:12px"><button onclick="likePost(${{p.id}})">❤️ ${{p.likes}} Like</button><button onclick="let t=prompt('Reply:');if(t)replyPost(${{p.id}},t)">💬 Reply</button><button onclick="deletePost(${{p.id}})">🗑️ Delete</button></div>
<div id="replies-${{p.id}}" style="padding:0 10px 8px;font-size:11px;color:#aaa"></div></div>`).join('');posts.forEach(p=>loadReplies(p.id));}}
async function likePost(id){{await fetch('/like/'+id,{{method:'POST'}});loadFeed();}}
async function replyPost(id,text){{await fetch('/reply/'+id,{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{text}})}});loadReplies(id);}}
async function loadReplies(id){{let r=await fetch('/replies/'+id);let reps=await r.json();document.getElementById('replies-'+id).innerHTML=reps.map(rr=>`<div><b>@${{rr.username}}:</b> ${{rr.text}}</div>`).join('');}}
async function deletePost(id){{if(!confirm('Delete?'))return;await fetch('/delete/'+id,{{method:'POST'}});loadFeed();}}
async function viewStory(id){{await fetch('/story/view/'+id,{{method:'POST'}});alert('Story viewed — expires in 24h like Snapchat');}}
setInterval(()=>{{loadFeed();loadStories();}},5000);loadFeed();loadStories();loadStreak();
</script></body></html>"""

FRIENDS_HTML = f"""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Friends</title>{BASE_STYLE}</head><body>
<div class="header"><h1 class="gold">Friends</h1><div class="top-links"><a href="/">Home</a><a href="/chats">Chats</a><a href="/profile">Profile</a></div></div>
<div class="card" style="padding:12px"><input id="u" placeholder="Search username"><button class="btn btn-gold" style="width:100%;margin-top:6px" onclick="addFriend()">Add Friend</button><p id="msg" style="font-size:11px"></p></div>
<div id="list"></div>
<script>async function addFriend(){{let u=document.getElementById('u').value;let r=await fetch('/friends/add',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{username:u}})}});let d=await r.json();document.getElementById('msg').innerText=d.ok?'Added':'❌ '+d.error;load();}}async function load(){{let r=await fetch('/friends/list');let data=await r.json();document.getElementById('list').innerHTML=data.map(f=>`<div class="card" style="padding:10px;display:flex;justify-content:space-between"><span>@${{f.username}} • 🔥 ${{f.streak}} days</span><a href="/chat/${{f.username}}" style="color:#D4AF37">Chat</a></div>`).join('');}}load();</script></body></html>"""

CHATS_HTML = f"""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Chats</title>{BASE_STYLE}</head><body>
<div class="header"><h1 class="gold">Private Chats</h1><div class="top-links"><a href="/">Home</a><a href="/friends">Friends</a></div></div>
<div id="list">Loading...</div>
<script>async function load(){{let r=await fetch('/chats/list');let data=await r.json();document.getElementById('list').innerHTML=data.map(c=>`<div class="card" style="padding:10px"><a href="/chat/${{c.username}}" style="color:#fff;text-decoration:none"><b>@${{c.username}}</b><br><small style="color:#666">${{c.last_msg||'No messages yet'}}</small></a></div>`).join('');}}load();</script></body></html>"""

CHAT_HTML = f"""<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Chat</title>{BASE_STYLE}
<style>.msg{{padding:8px 10px;border-radius:12px;margin:6px;max-width:75%}}.me{{background:#D4AF37;color:#000;margin-left:auto}}.other{{background:#222}} #msgs{{height:70vh;overflow-y:auto;padding:10px}}</style></head><body>
<div class="header"><h1 class="gold">@{{{{other}}}}</h1><div class="top-links"><a href="/chats">Back to Chats</a><a href="/">Home</a></div></div>
<div id="msgs"></div><div style="padding:10px;display:flex;gap:6px;position:fixed;bottom:0;width:100%;background:#000"><input id="txt" placeholder="Message..."><button class="btn btn-gold" onclick="send()">Send</button><button class="btn btn-dark" onclick="document.getElementById('f').click()">📸</button><input type="file" id="f" style="display:none" accept="image/*,video/*"></div>
<script>
let other="{{{{other}}}}";
async function load(){{let r=await fetch('/chat/'+other+'/messages');let msgs=await r.json();document.getElementById('msgs').innerHTML=msgs.map(m=>`<div class="msg ${{m.sender=='{{{{me}}}}'?'me':'other'}}">${{m.media? (m.media_type=='video'?`<video src="${{m.media}}" controls style="width:100%"></video>`:`<img src="${{m.media}}" style="width:100%;border-radius:8px">`):''}}<div>${{m.text||''}}</div><small style="font-size:8px">${{m.created_at}}</small></div>`).join('');let d=document.getElementById('msgs');d.scrollTop=d.scrollHeight;}}
async function send(){{let t=document.getElementById('txt').value;if(!t)return;await fetch('/chat/'+other+'/send',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{text:t}})}});document.getElementById('txt').value='';load();}}
document.getElementById('f').addEventListener('change',e=>{{let f=e.target.files[0];let r=new FileReader();r.onload=ev=>{{fetch('/chat/'+other+'/send',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{media:ev.target.result,media_type:f.type.startsWith('video')?'video':'image'}})}}).then(()=>load());}};r.readAsDataURL(f);}});
setInterval(load,3000);load();
</script></body></html>"""

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='GET': return render_template_string(LOGIN_HTML)
    data=request.json; u=data.get('username','').strip()[:20]; p=data.get('password','')
    conn=get_conn(); c=conn.cursor()
    try:
        c.execute("SELECT password FROM auth WHERE username=%s" if USE_POSTGRES else "SELECT password FROM auth WHERE username=?", (u,))
        row=c.fetchone()
    except: row=None
    conn.close()
    if not row or not check_password_hash(row[0], p): return jsonify({"ok":False,"error":"Wrong credentials"})
    session['username']=u; return jsonify({"ok":True})

@app.route('/signup', methods=['POST'])
def signup():
    data=request.json; u=data.get('username','').strip()[:20]; p=data.get('password','')
    if len(u)<3 or len(p)<3: return jsonify({"ok":False,"error":"Min 3 chars"})
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT 1 FROM auth WHERE username=%s" if USE_POSTGRES else "SELECT 1 FROM auth WHERE username=?", (u,))
    if c.fetchone(): conn.close(); return jsonify({"ok":False,"error":"Taken"})
    c.execute("INSERT INTO auth (username,password,created_at) VALUES (%s,%s,%s)" if USE_POSTGRES else "INSERT INTO auth (username,password,created_at) VALUES (?,?,?)", (u, generate_password_hash(p), datetime.now().isoformat()))
    conn.commit(); conn.close(); session['username']=u; return jsonify({"ok":True})

@app.route('/forgot', methods=['GET','POST'])
def forgot():
    if request.method=='GET': return render_template_string(FORGOT_HTML)
    data=request.json; u=data.get('username','').strip(); p=data.get('password','')
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT 1 FROM auth WHERE username=%s" if USE_POSTGRES else "SELECT 1 FROM auth WHERE username=?", (u,))
    if not c.fetchone(): conn.close(); return jsonify({"ok":False,"error":"Not found"})
    c.execute("UPDATE auth SET password=%s WHERE username=%s" if USE_POSTGRES else "UPDATE auth SET password=? WHERE username=?", (generate_password_hash(p), u)); conn.commit(); conn.close()
    return jsonify({"ok":True})

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

@app.route('/')
def home():
    if 'username' not in session: return redirect('/login')
    return render_template_string(MAIN_HTML, username=session['username'])

@app.route('/friends')
def friends_page():
    if 'username' not in session: return redirect('/login')
    return render_template_string(FRIENDS_HTML)

@app.route('/chats')
def chats_page():
    if 'username' not in session: return redirect('/login')
    return render_template_string(CHATS_HTML)

@app.route('/chat/<other>')
def chat_page(other):
    if 'username' not in session: return redirect('/login')
    return render_template_string(CHAT_HTML, other=other, me=session['username'])

@app.route('/profile')
def profile():
    if 'username' not in session: return redirect('/login')
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT streak,longest FROM users WHERE username=%s" if USE_POSTGRES else "SELECT streak,longest FROM users WHERE username=?", (session['username'],))
    row=c.fetchone(); conn.close()
    streak=row[0] if row else 0; longest=row[1] if row else 0
    return f"<html><body style='background:#000;color:#fff;font-family:system-ui;text-align:center;padding:20px'><h1 style='color:#D4AF37'>@{session['username']}</h1><p>🔥 {streak} days</p><p>👑 Longest {longest}</p><a href='/' style='color:#D4AF37'>Back</a></body></html>"

# --- API ---
@app.route('/upload', methods=['POST'])
def upload():
    if 'username' not in session: return jsonify({"ok":False})
    data=request.json; media=data.get('media'); mtype=data.get('media_type','image')
    now=datetime.now(); exp=now+timedelta(hours=24)
    conn=get_conn(); c=conn.cursor()
    c.execute("INSERT INTO posts (username,media,media_type,created_at,expires_at,likes) VALUES (%s,%s,%s,%s,%s,0)" if USE_POSTGRES else "INSERT INTO posts (username,media,media_type,created_at,expires_at,likes) VALUES (?,?,?,?,?,0)", (session['username'],media,mtype,now.isoformat(),exp.isoformat()))
    c.execute("INSERT INTO stories (username,media,media_type,created_at,expires_at) VALUES (%s,%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO stories (username,media,media_type,created_at,expires_at) VALUES (?,?,?,?,?)", (session['username'],media,mtype,now.isoformat(),exp.isoformat()))
    # streak
    c.execute("SELECT last_date,streak,longest FROM users WHERE username=%s" if USE_POSTGRES else "SELECT last_date,streak,longest FROM users WHERE username=?", (session['username'],))
    r=c.fetchone()
    today=date.today().isoformat()
    if not r:
        c.execute("INSERT INTO users (username,streak,last_date,longest) VALUES (%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO users (username,streak,last_date,longest) VALUES (?,?,?,?)", (session['username'],1,today,1))
    else:
        last,stk,longest=r; stk=stk or 0; longest=longest or 0
        if last!=today:
            from datetime import date as d
            try:
                ld=d.fromisoformat(last) if last else None
                delta=(d.today()-ld).days if ld else 2
            except: delta=2
            if delta==1: stk+=1
            elif delta>1: stk=1
            longest=max(longest,stk)
            c.execute("UPDATE users SET streak=%s,last_date=%s,longest=%s WHERE username=%s" if USE_POSTGRES else "UPDATE users SET streak=?,last_date=?,longest=? WHERE username=?", (stk,today,longest,session['username']))
    conn.commit(); conn.close()
    return jsonify({"ok":True})

@app.route('/feed')
def feed():
    conn=get_conn(); c=conn.cursor()
    now=datetime.now().isoformat()
    c.execute("DELETE FROM posts WHERE expires_at<%s" if USE_POSTGRES else "DELETE FROM posts WHERE expires_at<?", (now,))
    c.execute("SELECT id,username,media,media_type,task,likes,created_at FROM posts ORDER BY id DESC LIMIT 50")
    rows=c.fetchall(); conn.commit(); conn.close()
    return jsonify([{"id":r[0],"username":r[1],"media":r[2],"media_type":r[3],"task":r[4],"likes":r[5],"created_at":r[6][:16]} for r in rows])

@app.route('/stories')
def stories():
    conn=get_conn(); c=conn.cursor()
    now=datetime.now().isoformat()
    c.execute("DELETE FROM stories WHERE expires_at<%s" if USE_POSTGRES else "DELETE FROM stories WHERE expires_at<?", (now,))
    c.execute("SELECT id,username,media_type FROM stories ORDER BY id DESC LIMIT 30")
    rows=c.fetchall(); conn.close()
    return jsonify([{"id":r[0],"username":r[1],"media_type":r[2]} for r in rows])

@app.route('/story/view/<int:id>', methods=['POST'])
def view_story(id):
    conn=get_conn(); c=conn.cursor()
    c.execute("UPDATE stories SET views=views+1 WHERE id=%s" if USE_POSTGRES else "UPDATE stories SET views=views+1 WHERE id=?", (id,))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/streak')
def streak_route():
    if 'username' not in session: return jsonify({"streak":0,"longest":0})
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT streak,longest FROM users WHERE username=%s" if USE_POSTGRES else "SELECT streak,longest FROM users WHERE username=?", (session['username'],))
    r=c.fetchone(); conn.close()
    return jsonify({"streak":r[0] if r else 0,"longest":r[1] if r else 0})

@app.route('/challenge', methods=['POST'])
def challenge():
    if 'username' not in session: return jsonify({"ok":False})
    data=request.json; to_user=data.get('to_user'); task=data.get('task')
    conn=get_conn(); c=conn.cursor()
    c.execute("INSERT INTO challenges (from_user,to_user,task,created_at,status) VALUES (%s,%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO challenges (from_user,to_user,task,created_at,status) VALUES (?,?,?,?,?)", (session['username'],to_user,task,datetime.now().isoformat(),'pending'))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/like/<int:id>', methods=['POST'])
def like(id):
    if 'username' not in session: return jsonify({"ok":False})
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT 1 FROM likes WHERE post_id=%s AND username=%s" if USE_POSTGRES else "SELECT 1 FROM likes WHERE post_id=? AND username=?", (id,session['username']))
    if c.fetchone():
        c.execute("DELETE FROM likes WHERE post_id=%s AND username=%s" if USE_POSTGRES else "DELETE FROM likes WHERE post_id=? AND username=?", (id,session['username']))
        c.execute("UPDATE posts SET likes=likes-1 WHERE id=%s" if USE_POSTGRES else "UPDATE posts SET likes=likes-1 WHERE id=?", (id,))
    else:
        c.execute("INSERT INTO likes (post_id,username) VALUES (%s,%s)" if USE_POSTGRES else "INSERT INTO likes (post_id,username) VALUES (?,?)", (id,session['username']))
        c.execute("UPDATE posts SET likes=likes+1 WHERE id=%s" if USE_POSTGRES else "UPDATE posts SET likes=likes+1 WHERE id=?", (id,))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/reply/<int:id>', methods=['POST'])
def reply(id):
    if 'username' not in session: return jsonify({"ok":False})
    text=request.json.get('text','')[:200]
    conn=get_conn(); c=conn.cursor()
    c.execute("INSERT INTO replies (post_id,username,text,created_at) VALUES (%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO replies (post_id,username,text,created_at) VALUES (?,?,?,?)", (id,session['username'],text,datetime.now().isoformat()))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/replies/<int:id>')
def get_replies(id):
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT username,text FROM replies WHERE post_id=%s ORDER BY id ASC" if USE_POSTGRES else "SELECT username,text FROM replies WHERE post_id=? ORDER BY id ASC", (id,))
    rows=c.fetchall(); conn.close()
    return jsonify([{"username":r[0],"text":r[1]} for r in rows])

@app.route('/delete/<int:id>', methods=['POST'])
def delete_post(id):
    if 'username' not in session: return jsonify({"ok":False})
    conn=get_conn(); c=conn.cursor()
    c.execute("DELETE FROM posts WHERE id=%s AND username=%s" if USE_POSTGRES else "DELETE FROM posts WHERE id=? AND username=?", (id,session['username']))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/friends/add', methods=['POST'])
def add_friend():
    if 'username' not in session: return jsonify({"ok":False})
    u=request.json.get('username','').strip()
    if u==session['username']: return jsonify({"ok":False,"error":"Can't add yourself"})
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT 1 FROM auth WHERE username=%s" if USE_POSTGRES else "SELECT 1 FROM auth WHERE username=?", (u,))
    if not c.fetchone(): conn.close(); return jsonify({"ok":False,"error":"User not found"})
    c.execute("SELECT 1 FROM friends WHERE user1=%s AND user2=%s" if USE_POSTGRES else "SELECT 1 FROM friends WHERE user1=? AND user2=?", (session['username'],u))
    if c.fetchone(): conn.close(); return jsonify({"ok":False,"error":"Already friends"})
    c.execute("INSERT INTO friends (user1,user2,created_at) VALUES (%s,%s,%s)" if USE_POSTGRES else "INSERT INTO friends (user1,user2,created_at) VALUES (?,?,?)", (session['username'],u,datetime.now().isoformat()))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/friends/list')
def friends_list():
    if 'username' not in session: return jsonify([])
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT user2 FROM friends WHERE user1=%s" if USE_POSTGRES else "SELECT user2 FROM friends WHERE user1=?", (session['username'],))
    rows=c.fetchall(); result=[]
    for r in rows:
        uname=r[0]
        c.execute("SELECT streak FROM users WHERE username=%s" if USE_POSTGRES else "SELECT streak FROM users WHERE username=?", (uname,))
        s=c.fetchone(); result.append({"username":uname,"streak":s[0] if s else 0})
    conn.close(); return jsonify(result)

@app.route('/chats/list')
def chats_list():
    if 'username' not in session: return jsonify([])
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT user2 FROM friends WHERE user1=%s" if USE_POSTGRES else "SELECT user2 FROM friends WHERE user1=?", (session['username'],))
    rows=c.fetchall()
    out=[]
    for r in rows:
        uname=r[0]
        c.execute("SELECT text FROM chats WHERE (sender=%s AND receiver=%s) OR (sender=%s AND receiver=%s) ORDER BY id DESC LIMIT 1" if USE_POSTGRES else "SELECT text FROM chats WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) ORDER BY id DESC LIMIT 1", (session['username'],uname,uname,session['username']))
        last=c.fetchone()
        out.append({"username":uname,"last_msg":last[0][:30] if last and last[0] else "No messages"})
    conn.close(); return jsonify(out)

@app.route('/chat/<other>/messages')
def chat_messages(other):
    if 'username' not in session: return jsonify([])
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT sender,text,media,media_type,created_at FROM chats WHERE (sender=%s AND receiver=%s) OR (sender=%s AND receiver=%s) ORDER BY id ASC LIMIT 100" if USE_POSTGRES else "SELECT sender,text,media,media_type,created_at FROM chats WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) ORDER BY id ASC LIMIT 100", (session['username'],other,other,session['username']))
    rows=c.fetchall(); conn.close()
    return jsonify([{"sender":r[0],"text":r[1],"media":r[2],"media_type":r[3],"created_at":r[4][:16]} for r in rows])

@app.route('/chat/<other>/send', methods=['POST'])
def chat_send(other):
    if 'username' not in session: return jsonify({"ok":False})
    data=request.json
    conn=get_conn(); c=conn.cursor()
    c.execute("INSERT INTO chats (sender,receiver,text,media,media_type,created_at) VALUES (%s,%s,%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO chats (sender,receiver,text,media,media_type,created_at) VALUES (?,?,?,?,?,?)", (session['username'],other,data.get('text'),data.get('media'),data.get('media_type'),datetime.now().isoformat()))
    conn.commit(); conn.close(); return jsonify({"ok":True})

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.environ.get("PORT",5000)))
