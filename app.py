import os
from flask import Flask, request, jsonify, render_template_string, session, redirect
from datetime import datetime, timedelta, date
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "proveam-social-v2-postgres-gold-2026"
DB_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = bool(DB_URL)

def get_conn():
    if USE_POSTGRES:
        import psycopg2
        return psycopg2.connect(DB_URL)
    else:
        conn = sqlite3.connect("proveam.db")
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    conn = get_conn(); c = conn.cursor()
    if USE_POSTGRES:
        c.execute("CREATE TABLE IF NOT EXISTS auth (username TEXT PRIMARY KEY, password TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, streak INT, last_date TEXT, longest INT)")
        c.execute("CREATE TABLE IF NOT EXISTS posts (id SERIAL PRIMARY KEY, username TEXT, media TEXT, media_type TEXT, task TEXT, likes INT DEFAULT 0, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS stories (id SERIAL PRIMARY KEY, username TEXT, media TEXT, media_type TEXT, created_at TEXT, expires_at TEXT, views INT DEFAULT 0)")
        c.execute("CREATE TABLE IF NOT EXISTS likes (id SERIAL PRIMARY KEY, post_id INT, username TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS replies (id SERIAL PRIMARY KEY, post_id INT, username TEXT, text TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS chats (id SERIAL PRIMARY KEY, sender TEXT, receiver TEXT, text TEXT, media TEXT, media_type TEXT, reply_to TEXT, created_at TEXT)")
        try: c.execute("ALTER TABLE chats ADD COLUMN IF NOT EXISTS reply_to TEXT")
        except: pass
    else:
        c.execute("CREATE TABLE IF NOT EXISTS auth (username TEXT PRIMARY KEY, password TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, streak INTEGER, last_date TEXT, longest INTEGER)")
        c.execute("CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, media TEXT, media_type TEXT, task TEXT, likes INTEGER DEFAULT 0, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS stories (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, media TEXT, media_type TEXT, created_at TEXT, expires_at TEXT, views INTEGER DEFAULT 0)")
        c.execute("CREATE TABLE IF NOT EXISTS likes (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, username TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS replies (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, username TEXT, text TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, receiver TEXT, text TEXT, media TEXT, media_type TEXT, reply_to TEXT, created_at TEXT)")
    conn.commit(); conn.close()
init_db()

LOGIN_HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:#000;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh}.box{background:#111;border:1px solid #222;padding:25px;border-radius:16px;width:90%;max-width:350px;text-align:center}input{width:100%;padding:12px;background:#000;border:1px solid #333;color:#fff;border-radius:10px;margin:6px 0}.btn{padding:10px;border-radius:12px;border:none;font-weight:800;width:100%;background:#D4AF37}</style></head><body>
<div class="box"><div style="width:80px;height:80px;border-radius:50%;border:2px solid #D4AF37;margin:0 auto;display:flex;align-items:center;justify-content:center;font-weight:900;color:#D4AF37">P</div><h1 style="color:#D4AF37;margin:10px 0">PROVE AM</h1><h3 id="title">Login</h3>
<input id="u" placeholder="Username"><input id="p" type="password" placeholder="Password"><button class="btn" onclick="doAuth()">Continue</button>
<p style="margin-top:12px"><a href="#" onclick="toggleMode()" id="toggleLink" style="color:#D4AF37;font-size:12px">No account? Sign Up</a></p><p id="msg" style="color:#f55;font-size:12px"></p></div>
<script>
let mode='login';function toggleMode(){mode=mode=='login'?'signup':'login';document.getElementById('title').innerText=mode=='login'?'Login':'Sign Up';}
async function doAuth(){let u=document.getElementById('u').value,p=document.getElementById('p').value;let r=await fetch('/'+mode,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})});let d=await r.json();if(d.ok)location.href='/';else document.getElementById('msg').innerText=d.error;}
</script></body></html>"""

MAIN_HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
<style>*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:#000;color:#fff}.header{padding:10px;border-bottom:1px solid #222;position:sticky;top:0;background:#000;z-index:20}.top-row{display:flex;justify-content:space-between;align-items:center}.logo{width:36px;height:36px;border-radius:50%;background:#D4AF37;color:#000;font-weight:900;display:flex;align-items:center;justify-content:center}.story-bar{display:flex;gap:12px;overflow-x:auto;padding:10px;border-bottom:1px solid #222}.story-circle{min-width:62px;text-align:center;cursor:pointer}.story-ring{width:58px;height:58px;border-radius:50%;padding:2px;background:linear-gradient(45deg,#D4AF37,#FF6A00)}.story-ring img{width:100%;height:100%;border-radius:50%;border:2px solid #000}.card{background:#111;border:1px solid #222;border-radius:16px;margin:10px;overflow:hidden}.btn{padding:10px 14px;border-radius:12px;border:none;font-weight:800}.btn-gold{background:#D4AF37;color:#000}.btn-dark{background:#222;color:#fff;border:1px solid #444}input{width:100%;padding:12px;background:#000;border:1px solid #333;color:#fff;border-radius:10px;margin:6px 0}</style>
</head><body>
<div class="header"><div class="top-row"><div style="display:flex;gap:8px;align-items:center"><div class="logo">P</div><b>PROVE AM</b></div><div style="font-size:11px;color:#888">@{{username}} • 🔥 <span id="streak">0</span></div></div></div>
<div class="story-bar" id="storyBar"></div>
<div style="margin:8px 10px;background:#1A1A0A;border:1px solid #332;border-radius:12px;padding:10px;display:flex;justify-content:space-between;align-items:center"><div><b style="font-size:12px">🔥 RESTORE STREAKS — 2 STREAKS EXPIRING SOON!</b><br><small style="color:#888;font-size:10px">Only 3h left!</small></div><button class="btn btn-gold" style="padding:6px 12px;font-size:11px">Restore</button></div>
<div class="card" style="padding:12px">
<h4 style="color:#D4AF37">PROVE AM NOW 📸🎥</h4>
<div style="display:flex;gap:8px;margin:8px 0"><button class="btn btn-dark" onclick="startCamera('photo')">📸 Photo</button><button class="btn btn-dark" onclick="startCamera('video')">🎥 Video</button><button class="btn btn-dark" onclick="document.getElementById('fileIn').click()">🖼️ Gallery</button></div>
<video id="video" autoplay playsinline muted style="width:100%;display:none;border-radius:12px"></video><canvas id="canvas" style="display:none"></canvas>
<div id="camActions" style="display:none;gap:8px;margin-top:8px"><button class="btn btn-gold" onclick="capture()">CAPTURE / STOP</button><button class="btn btn-dark" onclick="stopCamera()">Cancel</button></div>
<input type="file" id="fileIn" accept="image/*,video/*" style="display:none">
<div style="display:flex;gap:6px;margin-top:10px"><button class="btn btn-gold" style="flex:1" onclick="uploadPost()">Instagram Post (Forever)</button><button class="btn btn-dark" style="flex:1" onclick="uploadStory()">Snapchat Story (24h)</button></div>
</div>
<div id="feed"></div>
<script>
let stream=null,mediaRecorder=null,chunks=[],mode='photo',pendingMedia=null,pendingType=null;
async function startCamera(m){mode=m;let v=document.getElementById('video');try{stream=await navigator.mediaDevices.getUserMedia({video:true,audio:m=='video'});v.srcObject=stream;v.style.display='block';document.getElementById('camActions').style.display='flex';if(m=='video'){chunks=[];mediaRecorder=new MediaRecorder(stream);mediaRecorder.ondataavailable=e=>chunks.push(e.data);mediaRecorder.onstop=()=>{let blob=new Blob(chunks,{type:'video/webm'});let r=new FileReader();r.onload=e=>{pendingMedia=e.target.result;pendingType='video';};r.readAsDataURL(blob);};mediaRecorder.start();setTimeout(()=>{if(mediaRecorder&&mediaRecorder.state=='recording')mediaRecorder.stop();},30000);}}catch(e){alert('Camera needed')}}
function stopCamera(){if(mediaRecorder&&mediaRecorder.state=='recording')mediaRecorder.stop();if(stream)stream.getTracks().forEach(t=>t.stop());document.getElementById('video').style.display='none';document.getElementById('camActions').style.display='none'}
function capture(){if(mode=='video'){if(mediaRecorder&&mediaRecorder.state=='recording')mediaRecorder.stop();stopCamera();return;}let v=document.getElementById('video'),c=document.getElementById('canvas');c.width=v.videoWidth;c.height=v.videoHeight;c.getContext('2d').drawImage(v,0,0);pendingMedia=c.toDataURL('image/jpeg',0.6);pendingType='image';stopCamera();}
document.getElementById('fileIn').addEventListener('change',e=>{let f=e.target.files[0];if(!f)return;let r=new FileReader();r.onload=ev=>{pendingMedia=ev.target.result;pendingType=f.type.startsWith('video')?'video':'image';};r.readAsDataURL(f);});
async function uploadPost(){if(!pendingMedia)return alert('Capture first');let res=await fetch('/upload/post',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media:pendingMedia,media_type:pendingType})});if((await res.json()).ok){pendingMedia=null;loadFeed();loadStreak();}}
async function uploadStory(){if(!pendingMedia)return alert('Capture first');let res=await fetch('/upload/story',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media:pendingMedia,media_type:pendingType})});if((await res.json()).ok){pendingMedia=null;loadStories();}}
async function loadStreak(){let r=await fetch('/streak');let d=await r.json();document.getElementById('streak').innerText=d.streak;}
async function loadStories(){let r=await fetch('/stories');let s=await r.json();document.getElementById('storyBar').innerHTML=s.length==0?'<span style="color:#666;font-size:11px">No stories — add one</span>':s.map(x=>`<div class="story-circle" onclick="location.href='/profile/${x.username}'"><div class="story-ring"><img src="https://i.pravatar.cc/100?u=${x.username}"></div><small style="font-size:9px">${x.username} 🔥127</small></div>`).join('');}
async function loadFeed(){let r=await fetch('/feed');let posts=await r.json();document.getElementById('feed').innerHTML=posts.map(p=>`<div class="card"><div style="padding:8px 10px;display:flex;justify-content:space-between;font-size:12px"><b>@${p.username}</b><span style="color:#666">${p.created_at}</span></div>${p.media_type=='video'?`<video src="${p.media}" controls style="width:100%"></video>`:`<img src="${p.media}" style="width:100%">`}<div style="padding:8px 10px;display:flex;gap:12px"><i class="fa-regular fa-heart" onclick="likePost(${p.id})"></i> ${p.likes} <i class="fa-regular fa-comment"></i> <i class="fa-regular fa-paper-plane"></i><span style="flex:1"></span><i class="fa-regular fa-bookmark"></i></div><div style="padding:0 10px 8px;font-size:12px"><b>@${p.username}</b> NO DAYS OFF 💪<div id="replies-${p.id}" style="color:#aaa"></div></div></div>`).join('');posts.forEach(p=>loadReplies(p.id));}
async function likePost(id){await fetch('/like/'+id,{method:'POST'});loadFeed();}
async function loadReplies(id){let r=await fetch('/replies/'+id);let reps=await r.json();let el=document.getElementById('replies-'+id);if(el)el.innerHTML=reps.map(x=>`<div><b>@${x.username}:</b> ${x.text}</div>`).join('');}
setInterval(()=>{loadFeed();loadStories();},5000);loadFeed();loadStories();loadStreak();
</script>
<div style="text-align:center;padding:12px"><a href="/chats" style="color:#000;background:#D4AF37;padding:10px 20px;border-radius:20px;text-decoration:none;font-weight:800">Go to WhatsApp Chats 💬</a></div>
</body></html>"""

CHAT_HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
<style>*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:#0B141A;color:#fff;display:flex;flex-direction:column;height:100vh}.header{background:#202C33;padding:10px;display:flex;align-items:center;gap:10px}.header img{width:38px;height:38px;border-radius:50%}.logo{width:28px;height:28px;background:#FFFC00;color:#000;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:900}#msgs{flex:1;overflow-y:auto;padding:10px;display:flex;flex-direction:column;gap:6px}.msg{padding:8px 10px;border-radius:12px;max-width:75%;cursor:pointer}.me{background:#005C4B;align-self:flex-end;border-radius:12px 12px 0 12px}.other{background:#202C33;align-self:flex-start}.msg small{font-size:9px;color:#ffffff66;display:block;text-align:right}.reply-preview{border-left:3px solid #53BDEB;padding-left:6px;margin-bottom:4px;color:#53BDEB;font-size:11px}.wave{display:flex;gap:2px;align-items:center}.wave span{width:3px;height:10px;background:#00A884;border-radius:2px;animation:wave 1s infinite}.wave span:nth-child(2){animation-delay:.1s}.wave span:nth-child(3){animation-delay:.2s}.wave span:nth-child(4){animation-delay:.3s}@keyframes wave{0%,100%{height:6px}50%{height:18px}}.input-bar{background:#202C33;padding:8px;display:flex;gap:8px}.input-bar textarea{flex:1;background:#2A3942;border:none;border-radius:20px;padding:10px 14px;color:#fff;outline:none}.icon{width:44px;height:44px;border-radius:50%;background:#00A884;display:flex;align-items:center;justify-content:center}.reply-bar{background:#202C33;border-left:4px solid #53BDEB;padding:6px 10px;display:flex;justify-content:space-between}</style></head><body>
<div class="header"><a href="/chats" style="color:#fff"><i class="fa-solid fa-arrow-left"></i></a><div class="logo">P</div><img src="https://i.pravatar.cc/100?u={{other}}"><div style="flex:1"><b id="chatName">{{other}}</b><br><small style="color:#8696A0">Coach Alex • online • now • 🔥 <span id="streak">12</span></small></div><i class="fa-solid fa-video" style="margin-right:12px"></i><i class="fa-solid fa-phone"></i></div>
<div id="msgs"></div>
<div id="replyBar" class="reply-bar" style="display:none"><div><b id="replyName"></b><div id="replyText" style="color:#aaa"></div></div><span onclick="cancelReply()">✕</span></div>
<div class="input-bar"><textarea id="txt" rows="1" placeholder="Message" oninput="onType()"></textarea><button id="micBtn" class="icon" onmousedown="startRec()" onmouseup="stopRec()" ontouchstart="startRec()" ontouchend="stopRec()"><i id="micIcon" class="fa-solid fa-microphone"></i></button><button id="sendBtn" class="icon" style="display:none" onclick="sendText()"><i class="fa-solid fa-paper-plane"></i></button></div>
<script>
let other="{{other}}", me="{{me}}", replyTo=null, recorder=null, chunks=[], isRec=false, startX=0;
function onType(){let has=document.getElementById('txt').value.trim().length>0;document.getElementById('sendBtn').style.display=has?'flex':'none';document.getElementById('micBtn').style.display=has?'none':'flex';}
async function load(){let r=await fetch('/chat/'+other+'/messages');let msgs=await r.json();let box=document.getElementById('msgs');box.innerHTML='';msgs.forEach(m=>{let isMe=m.sender==me;let div=document.createElement('div');div.className='msg '+(isMe?'me':'other');div.addEventListener('touchstart',e=>{startX=e.touches[0].clientX});div.addEventListener('touchend',e=>{if(e.changedTouches[0].clientX-startX>60)setReply(m)});div.onclick=()=>{if(m.media_type!='audio')setReply(m)};let replyHtml=m.reply_to?`<div class="reply-preview">↩ ${m.reply_to}</div>`:'';let body=m.media_type=='audio'?`<div style="display:flex;align-items:center;gap:8px"><div style="width:28px;height:28px;border-radius:50%;background:#00A884;display:flex;align-items:center;justify-content:center" onclick="event.stopPropagation();let a=this.nextElementSibling.nextElementSibling;a.paused?a.play():a.pause()"><i class="fa-solid fa-play" style="font-size:10px"></i></div><div class="wave"><span></span><span></span><span></span><span></span></div><span style="font-size:10px">0:08</span><audio src="${m.media}" style="display:none"></audio></div>`:m.media?`<img src="${m.media}" style="width:100%;border-radius:8px"><div>${m.text||''}</div>`:`<div>${m.text||''}</div>`;div.innerHTML=replyHtml+body+`<small>${m.created_at} ${isMe?'✓✓':''}</small>`;box.appendChild(div);});box.scrollTop=box.scrollHeight;fetch('/streak/'+other).then(r=>r.json()).then(d=>{document.getElementById('streak').innerText=d.streak||12;});}
function setReply(m){replyTo=m;document.getElementById('replyBar').style.display='flex';document.getElementById('replyName').innerText=m.sender;document.getElementById('replyText').innerText=(m.text||'[media]').substring(0,50);}
function cancelReply(){replyTo=null;document.getElementById('replyBar').style.display='none';}
async function sendText(){let txt=document.getElementById('txt').value;if(!txt.trim())return;await fetch('/chat/'+other+'/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:txt,reply_to:replyTo?(replyTo.text||'[media]'):null})});document.getElementById('txt').value='';cancelReply();onType();load();}
async function startRec(){isRec=true;document.getElementById('micIcon').className='fa-solid fa-stop';try{let stream=await navigator.mediaDevices.getUserMedia({audio:true});recorder=new MediaRecorder(stream);chunks=[];recorder.ondataavailable=e=>chunks.push(e.data);recorder.onstop=()=>{let blob=new Blob(chunks,{type:'audio/webm'});let reader=new FileReader();reader.onload=ev=>{fetch('/chat/'+other+'/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media:ev.target.result,media_type:'audio',text:'0:08'})}).then(load);};reader.readAsDataURL(blob);};recorder.start();}catch(e){alert('Mic permission needed');}}
function stopRec(){if(!isRec)return;isRec=false;document.getElementById('micIcon').className='fa-solid fa-microphone';if(recorder&&recorder.state=='recording')recorder.stop();}
setInterval(load,3000);load();
</script></body></html>"""

@app.route('/login', methods=['GET'])
def login_page(): return render_template_string(LOGIN_HTML)
@app.route('/login', methods=['POST'])
def login():
    data=request.json; u=data.get('username','').strip()[:20]; p=data.get('password','')
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT password FROM auth WHERE username=%s" if USE_POSTGRES else "SELECT password FROM auth WHERE username=?", (u,))
    row=c.fetchone(); conn.close()
    if not row or not check_password_hash(row[0], p): return jsonify({"ok":False,"error":"Wrong"})
    session['username']=u; return jsonify({"ok":True})
@app.route('/signup', methods=['POST'])
def signup():
    data=request.json; u=data.get('username','').strip()[:20]; p=data.get('password','')
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT 1 FROM auth WHERE username=%s" if USE_POSTGRES else "SELECT 1 FROM auth WHERE username=?", (u,))
    if c.fetchone(): conn.close(); return jsonify({"ok":False,"error":"Taken"})
    c.execute("INSERT INTO auth VALUES (%s,%s,%s)" if USE_POSTGRES else "INSERT INTO auth VALUES (?,?,?)", (u, generate_password_hash(p), datetime.now().isoformat()))
    conn.commit(); conn.close(); session['username']=u; return jsonify({"ok":True})
@app.route('/logout')
def logout(): session.clear(); return redirect('/login')
@app.route('/')
def home():
    if 'username' not in session: return redirect('/login')
    return render_template_string(MAIN_HTML, username=session['username'])
@app.route('/chats')
def chats_page():
    if 'username' not in session: return redirect('/login')
    return """<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{background:#000;color:#fff;font-family:system-ui}.header{padding:12px;border-bottom:1px solid #222;position:sticky;top:0;background:#000}.search{width:100%;padding:10px 14px;border-radius:20px;background:#111;border:1px solid #222;color:#fff;margin-top:8px}.card{padding:12px;border-bottom:1px solid #111;display:flex;gap:12px;align-items:center}</style></head><body>
    <div class="header"><div style="display:flex;justify-content:space-between"><b style="color:#D4AF37">Prove AM • Chats</b><a href="/" style="color:#888;text-decoration:none;border:1px solid #333;padding:5px 10px;border-radius:20px;font-size:11px">Home</a></div><input id="search" class="search" placeholder="🔍 Search chats..." oninput="filterChats()"></div>
    <div id="list">Loading WhatsApp style...</div>
    <script>let allChats=[];async function load(){let r=await fetch('/chats/list');allChats=await r.json();render(allChats);}function render(data){document.getElementById('list').innerHTML=data.map(c=>`<div class="card" onclick="location.href='/chat/${c.username}'"><img src="https://i.pravatar.cc/100?u=${c.username}" style="width:48px;height:48px;border-radius:50%"><div style="flex:1"><div style="display:flex;justify-content:space-between"><b>@${c.username} • 🔥12</b><small style="color:#666">${c.time||'10:14'}</small></div><small style="color:#888">${c.last_msg} ✓✓</small></div></div>`).join('');}function filterChats(){let q=document.getElementById('search').value.toLowerCase();render(allChats.filter(c=>c.username.toLowerCase().includes(q)));}load();</script></body></html>"""
@app.route('/chat/<other>')
def chat_page(other):
    if 'username' not in session: return redirect('/login')
    return render_template_string(CHAT_HTML, other=other, me=session['username'])
@app.route('/upload/post', methods=['POST'])
def upload_post():
    if 'username' not in session: return jsonify({"ok":False})
    data=request.json
    conn=get_conn(); c=conn.cursor()
    c.execute("INSERT INTO posts (username,media,media_type,created_at,likes) VALUES (%s,%s,%s,%s,0)" if USE_POSTGRES else "INSERT INTO posts (username,media,media_type,created_at,likes) VALUES (?,?,?,?,0)", (session['username'],data.get('media'),data.get('media_type'),datetime.now().isoformat()))
    conn.commit(); conn.close(); return jsonify({"ok":True})
@app.route('/upload/story', methods=['POST'])
def upload_story():
    if 'username' not in session: return jsonify({"ok":False})
    data=request.json; now=datetime.now(); exp=now+timedelta(hours=24)
    conn=get_conn(); c=conn.cursor()
    if USE_POSTGRES:
        c.execute("INSERT INTO stories (username,media,media_type,created_at,expires_at) VALUES (%s,%s,%s,%s,%s)", (session['username'],data.get('media'),data.get('media_type'),now.isoformat(),exp.isoformat()))
    else:
        c.execute("INSERT INTO stories (username,media,media_type,created_at,expires_at,views) VALUES (?,?,?,?,?,0)", (session['username'],data.get('media'),data.get('media_type'),now.isoformat(),exp.isoformat()))
    conn.commit(); conn.close(); return jsonify({"ok":True})
@app.route('/feed')
def feed():
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT id,username,media,media_type,likes,created_at FROM posts ORDER BY id DESC LIMIT 50")
    rows=c.fetchall(); conn.close()
    return jsonify([{"id":r[0],"username":r[1],"media":r[2],"media_type":r[3],"likes":r[4],"created_at":r[5][:16]} for r in rows])
@app.route('/stories')
def stories_route():
    conn=get_conn(); c=conn.cursor()
    now=datetime.now().isoformat()
    c.execute("DELETE FROM stories WHERE expires_at<%s" if USE_POSTGRES else "DELETE FROM stories WHERE expires_at<?", (now,))
    c.execute("SELECT username FROM stories ORDER BY id DESC LIMIT 30")
    rows=c.fetchall(); conn.commit(); conn.close()
    return jsonify([{"username":r[0]} for r in rows])
@app.route('/streak')
def streak():
    if 'username' not in session: return jsonify({"streak":0})
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT streak FROM users WHERE username=%s" if USE_POSTGRES else "SELECT streak FROM users WHERE username=?", (session['username'],))
    r=c.fetchone(); conn.close()
    return jsonify({"streak":r[0] if r else 12})
@app.route('/streak/<other>')
def streak_other(other):
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT streak FROM users WHERE username=%s" if USE_POSTGRES else "SELECT streak FROM users WHERE username=?", (other,))
    r=c.fetchone(); conn.close()
    return jsonify({"streak":r[0] if r else 12})
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
@app.route('/replies/<int:id>')
def get_replies(id):
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT username,text FROM replies WHERE post_id=%s" if USE_POSTGRES else "SELECT username,text FROM replies WHERE post_id=?", (id,))
    rows=c.fetchall(); conn.close()
    return jsonify([{"username":r[0],"text":r[1]} for r in rows])
@app.route('/reply/<int:id>', methods=['POST'])
def reply(id):
    conn=get_conn(); c=conn.cursor()
    c.execute("INSERT INTO replies (post_id,username,text,created_at) VALUES (%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO replies (post_id,username,text,created_at) VALUES (?,?,?,?)", (id,session['username'],request.json.get('text','')[:200],datetime.now().isoformat()))
    conn.commit(); conn.close(); return jsonify({"ok":True})
@app.route('/chats/list')
def chats_list():
    if 'username' not in session: return jsonify([])
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT DISTINCT receiver FROM chats WHERE sender=%s UNION SELECT DISTINCT sender FROM chats WHERE receiver=%s" if USE_POSTGRES else "SELECT DISTINCT receiver FROM chats WHERE sender=? UNION SELECT DISTINCT sender FROM chats WHERE receiver=?", (session['username'],session['username']))
    users=[r[0] for r in c.fetchall()] or ["Coach Alex","jamie","Maxwell Kyere"]
    out=[]
    for u in users:
        c.execute("SELECT text,media_type FROM chats WHERE (sender=%s AND receiver=%s) OR (sender=%s AND receiver=%s) ORDER BY id DESC LIMIT 1" if USE_POSTGRES else "SELECT text,media_type FROM chats WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) ORDER BY id DESC LIMIT 1", (session['username'],u,u,session['username']))
        last=c.fetchone()
        out.append({"username":u,"last_msg": last[0][:30] if last and last[0] else ("🎤 0:08 voice note" if last and last[1]=='audio' else "Tap to chat"), "time":"10:14"})
    conn.close(); return jsonify(out)
@app.route('/chat/<other>/messages')
def chat_messages(other):
    if 'username' not in session: return jsonify([])
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT sender,text,media,media_type,reply_to,created_at FROM chats WHERE (sender=%s AND receiver=%s) OR (sender=%s AND receiver=%s) ORDER BY id ASC" if USE_POSTGRES else "SELECT sender,text,media,media_type,reply_to,created_at FROM chats WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) ORDER BY id ASC", (session['username'],other,other,session['username']))
    rows=c.fetchall(); conn.close()
    return jsonify([{"sender":r[0],"text":r[1],"media":r[2],"media_type":r[3],"reply_to":r[4],"created_at":r[5][:16]} for r in rows])
@app.route('/chat/<other>/send', methods=['POST'])
def chat_send(other):
    if 'username' not in session: return jsonify({"ok":False})
    data=request.json
    conn=get_conn(); c=conn.cursor()
    c.execute("INSERT INTO chats (sender,receiver,text,media,media_type,reply_to,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO chats (sender,receiver,text,media,media_type,reply_to,created_at) VALUES (?,?,?,?,?,?,?)", (session['username'],other,data.get('text'),data.get('media'),data.get('media_type'),data.get('reply_to'),datetime.now().isoformat()))
    conn.commit(); conn.close(); return jsonify({"ok":True})

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.environ.get("PORT",5000)))
