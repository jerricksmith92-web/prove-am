import os
from flask import Flask, request, jsonify, render_template_string, session, redirect
from datetime import datetime, timedelta
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "proveam-clean-final-2026"
DB_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = bool(DB_URL)
typing_tracker = {}

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
        c.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, streak INT, last_date TEXT, longest INT, online_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS posts (id SERIAL PRIMARY KEY, username TEXT, media TEXT, media_type TEXT, likes INT DEFAULT 0, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS stories (id SERIAL PRIMARY KEY, username TEXT, media TEXT, media_type TEXT, created_at TEXT, expires_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS likes (id SERIAL PRIMARY KEY, post_id INT, username TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS replies (id SERIAL PRIMARY KEY, post_id INT, username TEXT, text TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS chats (id SERIAL PRIMARY KEY, sender TEXT, receiver TEXT, text TEXT, media TEXT, media_type TEXT, reply_to TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS notifications (id SERIAL PRIMARY KEY, to_user TEXT, from_user TEXT, type TEXT, text TEXT, is_read INT DEFAULT 0, created_at TEXT)")
        try:
            c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS online_at TEXT")
            c.execute("ALTER TABLE chats ADD COLUMN IF NOT EXISTS reply_to TEXT")
        except: pass
    else:
        c.execute("CREATE TABLE IF NOT EXISTS auth (username TEXT PRIMARY KEY, password TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, streak INTEGER, last_date TEXT, longest INTEGER, online_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, media TEXT, media_type TEXT, likes INTEGER DEFAULT 0, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS stories (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, media TEXT, media_type TEXT, created_at TEXT, expires_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS likes (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, username TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS replies (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, username TEXT, text TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, receiver TEXT, text TEXT, media TEXT, media_type TEXT, reply_to TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY AUTOINCREMENT, to_user TEXT, from_user TEXT, type TEXT, text TEXT, is_read INTEGER DEFAULT 0, created_at TEXT)")
    conn.commit(); conn.close()
init_db()

@app.before_request
def upd_online():
    if 'username' in session:
        try:
            conn=get_conn(); c=conn.cursor()
            c.execute("UPDATE users SET online_at=%s WHERE username=%s" if USE_POSTGRES else "UPDATE users SET online_at=? WHERE username=?", (datetime.now().isoformat(), session['username']))
            conn.commit(); conn.close()
        except: pass

LOGIN = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:#000;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh}.box{background:#111;border:1px solid #222;padding:25px;border-radius:16px;width:90%;max-width:350px;text-align:center}input{width:100%;padding:12px;background:#000;border:1px solid #333;color:#fff;border-radius:10px;margin:6px 0}.btn{padding:10px;width:100%;border-radius:12px;border:none;font-weight:800;background:#D4AF37}</style></head><body>
<div class="box"><div style="width:60px;height:60px;border-radius:50%;border:2px solid #D4AF37;margin:0 auto;display:flex;align-items:center;justify-content:center;color:#D4AF37;font-weight:900">P</div><h2 style="color:#D4AF37;margin:10px 0">PROVE AM</h2><input id="u" placeholder="Username"><input id="p" type="password" placeholder="Password"><button class="btn" onclick="auth()">Continue</button><p style="font-size:11px;margin-top:10px;color:#D4AF37" onclick="mode=mode=='login'?'signup':'login'">Tap to switch Login / Sign Up</p><p id="m" style="color:#f55"></p></div>
<script>let mode='login';async function auth(){let u=document.getElementById('u').value,p=document.getElementById('p').value;let r=await fetch('/'+mode,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})});let d=await r.json();if(d.ok)location.href='/';else document.getElementById('m').innerText=d.error}</script></body></html>"""

MAIN = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
<style>*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:#000;color:#fff}.header{position:sticky;top:0;z-index:10;background:#000;border-bottom:1px solid #222;padding:8px}.tabs{display:flex;gap:6px;margin-top:8px}.tabs button{flex:1;padding:8px;border-radius:20px;border:1px solid #333;background:#111;color:#888;font-size:12px}.tabs button.active{background:#D4AF37;color:#000;font-weight:800}.badge{position:relative}.notif-dot{position:absolute;top:-4px;right:-4px;background:#ff3040;color:#fff;font-size:9px;width:16px;height:16px;border-radius:50%;display:flex;align-items:center;justify-content:center}.story-bar{display:flex;gap:12px;overflow-x:auto;padding:10px;border-bottom:1px solid #111}.story-circle{min-width:60px;text-align:center}.ring{width:56px;height:56px;border-radius:50%;padding:2px;background:linear-gradient(45deg,#D4AF37,#ff6a00);position:relative}.ring img{width:100%;height:100%;border-radius:50%;border:2px solid #000}.online{position:absolute;bottom:0;right:0;width:12px;height:12px;background:#00ff00;border-radius:50%;border:2px solid #000}.card{background:#111;border:1px solid #222;border-radius:14px;margin:10px;overflow:hidden}.btn{padding:9px 12px;border-radius:10px;border:none;font-weight:800}.btn-gold{background:#D4AF37;color:#000}.btn-dark{background:#222;color:#fff;border:1px solid #333}.heart{color:#666;cursor:pointer}.heart.liked{color:#ff3040}input{width:100%;padding:11px;background:#000;border:1px solid #333;color:#fff;border-radius:10px;margin:5px 0}</style></head><body>
<div class="header">
<div style="display:flex;justify-content:space-between;align-items:center"><div style="display:flex;gap:8px;align-items:center"><div style="width:30px;height:30px;border-radius:50%;background:#D4AF37;color:#000;display:flex;align-items:center;justify-content:center;font-weight:900">P</div><b>PROVE AM</b></div><div style="display:flex;gap:14px;align-items:center"><div class="badge" onclick="openNotif()"><i class="fa-solid fa-bell" style="font-size:18px;color:#D4AF37"></i><div id="notifCount" class="notif-dot" style="display:none">0</div></div><div style="font-size:11px;color:#888">@{{username}} • 🔥<span id="streak">0</span></div></div></div>
<div class="tabs"><button id="tb-story" class="active" onclick="showTab('story')">Story</button><button id="tb-post" onclick="showTab('post')">Post</button><button id="tb-chat" onclick="location.href='/chats'">Chat</button></div>
</div>
<div id="notifPanel" style="display:none;position:fixed;top:60px;right:10px;left:10px;background:#111;border:1px solid #333;border-radius:12px;z-index:30;max-height:70vh;overflow-y:auto;padding:10px"><div style="display:flex;justify-content:space-between"><b style="color:#D4AF37">Notifications</b><span onclick="closeNotif()" style="cursor:pointer">✕</span></div><div id="notifList"></div></div>
<div id="tab-story"><div class="story-bar" id="storyBar"></div>
<div class="card" style="padding:12px"><b style="color:#D4AF37;font-size:12px">Story — disappears in 24h</b><div style="display:flex;gap:8px;margin-top:8px"><button class="btn btn-dark" onclick="openCam('story','photo')">📸 Photo</button><button class="btn btn-dark" onclick="openCam('story','video')">🎥 Video</button><button class="btn btn-dark" onclick="document.getElementById('sFile').click()">🖼️ Gallery</button></div><input type="file" id="sFile" accept="image/*,video/*" style="display:none"><div style="margin-top:8px"><button class="btn btn-gold" style="width:100%" onclick="triggerSave('story')">+ Add Story</button></div></div></div>
<div id="tab-post"><div class="card" style="padding:12px"><b style="color:#D4AF37;font-size:12px">Post — stays forever</b><div style="display:flex;gap:8px;margin-top:8px"><button class="btn btn-dark" onclick="openCam('post','photo')">📸 Photo</button><button class="btn btn-dark" onclick="openCam('post','video')">🎥 Video</button><button class="btn btn-dark" onclick="document.getElementById('pFile').click()">🖼️ Gallery</button></div><input type="file" id="pFile" accept="image/*,video/*" style="display:none"><div style="margin-top:8px"><button class="btn btn-gold" style="width:100%" onclick="triggerSave('post')">+ Add Post</button></div></div><div id="feed"></div></div>
<video id="video" autoplay playsinline muted style="width:100%;display:none;position:fixed;top:0;left:0;z-index:20"></video>
<div id="camBar" style="display:none;position:fixed;bottom:10px;left:0;right:0;z-index:21;text-align:center"><button class="btn btn-gold" onclick="doCapture()">CAPTURE / STOP</button> <button class="btn btn-dark" onclick="closeCam()">Cancel</button></div>
<canvas id="canvas" style="display:none"></canvas>
<script>
let curMode='story', curType='photo', stream=null, rec=null, chunks=[], pendingPost=null, pendingPostType=null, pendingStory=null, pendingStoryType=null;
function showTab(t){document.getElementById('tab-story').style.display=t=='story'?'block':'none';document.getElementById('tab-post').style.display=t=='post'?'block':'none';document.getElementById('tb-story').className=t=='story'?'active':'';document.getElementById('tb-post').className=t=='post'?'active':'';curMode=t;}
async function openCam(mode,type){curMode=mode;curType=type;let v=document.getElementById('video');try{stream=await navigator.mediaDevices.getUserMedia({video:true,audio:type=='video'});v.srcObject=stream;v.style.display='block';document.getElementById('camBar').style.display='block';if(type=='video'){chunks=[];rec=new MediaRecorder(stream);rec.ondataavailable=e=>chunks.push(e.data);rec.onstop=()=>{let b=new Blob(chunks,{type:'video/webm'});let r=new FileReader();r.onload=e=>{storePending(mode,e.target.result,'video');};r.readAsDataURL(b);};rec.start();}}catch(e){alert('Camera blocked')}}
function closeCam(){if(rec&&rec.state=='recording')rec.stop();if(stream)stream.getTracks().forEach(t=>t.stop());document.getElementById('video').style.display='none';document.getElementById('camBar').style.display='none';}
function doCapture(){if(curType=='video'){if(rec&&rec.state=='recording')rec.stop();closeCam();return;}let v=document.getElementById('video'),c=document.getElementById('canvas');c.width=v.videoWidth;c.height=v.videoHeight;c.getContext('2d').drawImage(v,0,0);storePending(curMode,c.toDataURL('image/jpeg',0.7),'image');closeCam();}
function storePending(mode,data,type){if(mode=='post'){pendingPost=data;pendingPostType=type;alert('Post ready — tap + Add Post');}else{pendingStory=data;pendingStoryType=type;alert('Story ready — tap + Add Story');}}
function triggerSave(mode){let data=mode=='post'?pendingPost:pendingStory;let type=mode=='post'?pendingPostType:pendingStoryType;if(!data)return alert('Capture or pick from gallery first');fetch('/upload/'+mode,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media:data,media_type:type})}).then(()=>{if(mode=='post'){pendingPost=null;loadFeed();}else{pendingStory=null;loadStories();}});}
document.getElementById('pFile').addEventListener('change',e=>{let f=e.target.files[0];let r=new FileReader();r.onload=ev=>{pendingPost=ev.target.result;pendingPostType=f.type.startsWith('video')?'video':'image';};r.readAsDataURL(f);});
document.getElementById('sFile').addEventListener('change',e=>{let f=e.target.files[0];let r=new FileReader();r.onload=ev=>{pendingStory=ev.target.result;pendingStoryType=f.type.startsWith('video')?'video':'image';};r.readAsDataURL(f);});
async function loadStories(){let r=await fetch('/stories');let data=await r.json();document.getElementById('storyBar').innerHTML=data.length==0?'<small style="color:#666">No stories yet</small>':data.map(s=>`<div class="story-circle"><div class="ring"><img src="https://i.pravatar.cc/100?u=${s.username}"><div class="online" style="background:${s.online?'#00ff00':'#666'}"></div></div><small style="font-size:9px">${s.username} ${s.online?'🟢':'⚪'}</small></div>`).join('');}
async function loadFeed(){let r=await fetch('/feed');let posts=await r.json();document.getElementById('feed').innerHTML=posts.map(p=>`<div class="card"><div style="padding:8px 10px;display:flex;justify-content:space-between;font-size:12px"><b>@${p.username} ${p.online?'🟢':'⚪'}</b><small style="color:#666">${p.created_at}</small></div>${p.media_type=='video'?`<video src="${p.media}" controls style="width:100%"></video>`:`<img src="${p.media}" style="width:100%">`}<div style="padding:8px 10px;display:flex;gap:14px"><i class="fa-solid fa-heart heart ${p.liked?'liked':''}" id="h-${p.id}" onclick="likePost(${p.id})"></i><span id="c-${p.id}">${p.likes}</span><i class="fa-regular fa-comment" onclick="document.getElementById('comment-${p.id}').focus()"></i></div><div style="padding:0 10px 8px;font-size:11px"><div id="replies-${p.id}"></div><div style="display:flex;gap:6px;margin-top:6px"><input id="comment-${p.id}" placeholder="Reply to post..." style="padding:8px;font-size:11px"><button class="btn btn-gold" style="padding:6px 10px;font-size:11px" onclick="commentPost(${p.id})">Send</button></div></div></div>`).join('');posts.forEach(p=>loadReplies(p.id));}
async function likePost(id){let r=await fetch('/like/'+id,{method:'POST'});let d=await r.json();document.getElementById('c-'+id).innerText=d.likes;let h=document.getElementById('h-'+id);if(d.liked)h.classList.add('liked');else h.classList.remove('liked');}
async function commentPost(id){let t=document.getElementById('comment-'+id).value;if(!t.trim())return;await fetch('/reply/'+id,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t})});document.getElementById('comment-'+id).value='';loadReplies(id);}
async function loadReplies(id){let r=await fetch('/replies/'+id);let data=await r.json();let el=document.getElementById('replies-'+id);if(el)el.innerHTML=data.map(x=>`<div><b>@${x.username}:</b> ${x.text}</div>`).join('');}
async function loadStreak(){let r=await fetch('/streak');let d=await r.json();document.getElementById('streak').innerText=d.streak||0;}
async function loadNotifs(){let r=await fetch('/notifications');let data=await r.json();let unread=data.filter(n=>!n.is_read).length;let dot=document.getElementById('notifCount');if(unread>0){dot.style.display='flex';dot.innerText=unread;}else dot.style.display='none';document.getElementById('notifList').innerHTML=data.map(n=>`<div style="padding:8px;border-bottom:1px solid #222;font-size:12px"><b>@${n.from_user}</b> ${n.type=='like'?'❤️ liked your post':n.type=='comment'?'💬 commented: '+n.text:'💬 sent you a message'}<br><small style="color:#666">${n.created_at}</small></div>`).join('')||'<small style="color:#666">No notifications</small>';}
function openNotif(){document.getElementById('notifPanel').style.display='block';fetch('/notifications/read',{method:'POST'});}
function closeNotif(){document.getElementById('notifPanel').style.display='none';}
loadStories();loadFeed();loadStreak();loadNotifs();
setInterval(()=>{loadFeed();loadStories();loadNotifs();},4000);
</script></body></html>"""

CHATS_HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{background:#000;color:#fff;font-family:system-ui}.header{padding:12px;border-bottom:1px solid #222;position:sticky;top:0;background:#000}.search{width:100%;padding:10px;border-radius:20px;background:#111;border:1px solid #222;color:#fff;margin-top:8px}.card{padding:12px;border-bottom:1px solid #111;display:flex;gap:12px;align-items:center;cursor:pointer}.tabs{display:flex;gap:6px;margin-top:8px}.tabs button{flex:1;padding:8px;border-radius:20px;border:1px solid #333;background:#111;color:#888}.tabs button.active{background:#D4AF37;color:#000}</style></head><body>
<div class="header"><div style="display:flex;justify-content:space-between"><b style="color:#D4AF37">PROVE AM — Chats</b><a href="/" style="color:#888;text-decoration:none;font-size:11px;border:1px solid #333;padding:4px 10px;border-radius:20px">Home</a></div><div class="tabs"><button onclick="location.href='/'">Story</button><button onclick="location.href='/'">Post</button><button class="active">Chat</button></div><input id="search" class="search" placeholder="🔍 Search..." oninput="filterChats()"></div>
<div id="list"></div>
<script>let all=[];async function load(){let r=await fetch('/chats/list');all=await r.json();render(all);}function render(data){document.getElementById('list').innerHTML=data.map(c=>`<div class="card" onclick="location.href='/chat/${c.username}'"><div style="position:relative"><img src="https://i.pravatar.cc/100?u=${c.username}" style="width:48px;height:48px;border-radius:50%"><div style="position:absolute;bottom:0;right:0;width:12px;height:12px;border-radius:50%;background:${c.online?'#00ff00':'#666'};border:2px solid #000"></div></div><div style="flex:1"><div style="display:flex;justify-content:space-between"><b>@${c.username} ${c.online?'<span style=color:#0f0>●</span>':''}</b><small style="color:#666">${c.typing?'typing...':'now'}</small></div><small style="color:${c.typing?'#00A884':'#888'}">${c.typing?'typing...':c.last_msg} ✓✓</small></div></div>`).join('');}function filterChats(){let q=document.getElementById('search').value.toLowerCase();render(all.filter(c=>c.username.toLowerCase().includes(q)));}setInterval(load,2000);load();</script></body></html>"""

CHAT_HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
<style>*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:#0B141A;color:#fff;display:flex;flex-direction:column;height:100vh}.header{background:#202C33;padding:10px;display:flex;align-items:center;gap:10px}.header img{width:36px;height:36px;border-radius:50%}#msgs{flex:1;overflow-y:auto;padding:10px;display:flex;flex-direction:column;gap:8px}.msg{padding:8px 10px;border-radius:12px;max-width:78%}.me{background:#005C4B;align-self:flex-end;border-radius:12px 12px 0 12px}.other{background:#202C33;align-self:flex-start}.msg small{font-size:9px;color:#ffffff88;display:block;text-align:right}.reply{border-left:3px solid #53BDEB;padding-left:6px;color:#53BDEB;font-size:11px;margin-bottom:4px}.bar{background:#202C33;padding:8px;display:flex;gap:8px;align-items:center}.bar textarea{flex:1;background:#2A3942;border:none;border-radius:20px;padding:10px;color:#fff;outline:none}.icon{width:42px;height:42px;border-radius:50%;background:#00A884;display:flex;align-items:center;justify-content:center;cursor:pointer}</style></head><body>
<div class="header"><a href="/chats" style="color:#fff"><i class="fa-solid fa-arrow-left"></i></a><img src="https://i.pravatar.cc/100?u={{other}}"><div style="flex:1"><b>{{other}} <span id="onlineDot" style="width:8px;height:8px;border-radius:50%;display:inline-block;background:#666"></span></b><br><small id="status" style="color:#8696A0">offline</small></div><i class="fa-solid fa-video" style="margin-right:12px"></i><i class="fa-solid fa-phone"></i></div>
<div id="msgs"></div>
<div id="typing" style="padding:0 12px;font-size:11px;color:#00A884;display:none">{{other}} is typing...</div>
<div id="replyBar" style="display:none;background:#202C33;border-left:4px solid #53BDEB;padding:6px 10px;display:flex;justify-content:space-between"><div><b id="rn"></b><div id="rt" style="color:#aaa;font-size:12px"></div></div><span onclick="cancelR()">✕</span></div>
<div class="bar"><button class="icon" style="background:#2A3942" onclick="document.getElementById('f').click()"><i class="fa-solid fa-paperclip"></i></button><textarea id="txt" rows="1" placeholder="Message" oninput="onTyping()"></textarea><button id="mic" class="icon" onmousedown="startR()" onmouseup="stopR()" ontouchstart="startR()" ontouchend="stopR()"><i id="mi" class="fa-solid fa-microphone"></i></button><button id="send" class="icon" style="display:none" onclick="sendT()"><i class="fa-solid fa-paper-plane"></i></button><input type="file" id="f" accept="image/*,video/*" style="display:none"></div>
<script>
let other="{{other}}", me="{{me}}", replyTo=null, rec=null, chunks=[], isRec=false, sx=0;
function onTyping(){let has=document.getElementById('txt').value.trim().length>0;document.getElementById('send').style.display=has?'flex':'none';document.getElementById('mic').style.display=has?'none':'flex';fetch('/chat/'+other+'/typing',{method:'POST'});}
async function load(){let r=await fetch('/chat/'+other+'/messages');let msgs=await r.json();let box=document.getElementById('msgs');box.innerHTML='';msgs.forEach(m=>{let isMe=m.sender==me;let d=document.createElement('div');d.className='msg '+(isMe?'me':'other');d.addEventListener('touchstart',e=>sx=e.touches[0].clientX);d.addEventListener('touchend',e=>{if(e.changedTouches[0].clientX-sx>60)setR(m)});d.onclick=()=>{if(m.media_type!='audio')setR(m)};let rp=m.reply_to?`<div class="reply">↩ ${m.reply_to}</div>`:'';let body=m.media_type=='audio'?`<audio src="${m.media}" controls style="width:150px"></audio>`:m.media? (m.media_type=='video'?`<video src="${m.media}" controls style="width:180px;border-radius:8px"></video>`:`<img src="${m.media}" style="width:180px;border-radius:8px">`)+`<div>${m.text||''}</div>`:`<div>${m.text||''}</div>`;d.innerHTML=rp+body+`<small>${m.created_at} ${isMe?'✓✓':''}</small>`;box.appendChild(d);});box.scrollTop=box.scrollHeight;
 let rs=await fetch('/chat/'+other+'/status');let sd=await rs.json();let dot=document.getElementById('onlineDot');let st=document.getElementById('status');if(sd.online){dot.style.background='#00ff00';st.innerText=sd.typing?'typing...':'online';st.style.color=sd.typing?'#00A884':'#8696A0';document.getElementById('typing').style.display=sd.typing?'block':'none';}else{dot.style.background='#666';st.innerText='last seen '+sd.last_seen;document.getElementById('typing').style.display='none';}
}
function setR(m){replyTo=m;document.getElementById('replyBar').style.display='flex';document.getElementById('rn').innerText=m.sender;document.getElementById('rt').innerText=(m.text||'[media]').substring(0,40);}
function cancelR(){replyTo=null;document.getElementById('replyBar').style.display='none';}
async function sendT(){let t=document.getElementById('txt').value;if(!t.trim())return;await fetch('/chat/'+other+'/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t,reply_to:replyTo?(replyTo.text||'[media]'):null})});document.getElementById('txt').value='';cancelR();onTyping();load();}
document.getElementById('f').addEventListener('change',e=>{let f=e.target.files[0];let r=new FileReader();r.onload=ev=>{fetch('/chat/'+other+'/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media:ev.target.result,media_type:f.type.startsWith('video')?'video':'image'})}).then(load);};r.readAsDataURL(f);});
async function startR(){isRec=true;document.getElementById('mi').className='fa-solid fa-stop';try{let s=await navigator.mediaDevices.getUserMedia({audio:true});rec=new MediaRecorder(s);chunks=[];rec.ondataavailable=e=>chunks.push(e.data);rec.onstop=()=>{let b=new Blob(chunks,{type:'audio/webm'});let r=new FileReader();r.onload=ev=>{fetch('/chat/'+other+'/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media:ev.target.result,media_type:'audio',text:'voice'})}).then(load);};r.readAsDataURL(b);};rec.start();}catch(e){alert('Mic needed');}}
function stopR(){if(!isRec)return;isRec=false;document.getElementById('mi').className='fa-solid fa-microphone';if(rec&&rec.state=='recording')rec.stop();}
setInterval(load,1500);load();
</script></body></html>"""

@app.route('/login', methods=['GET'])
def lp(): return render_template_string(LOGIN)
@app.route('/login', methods=['POST'])
def login():
    d=request.json; u=d.get('username','').strip()[:20]; p=d.get('password','')
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT password FROM auth WHERE username=%s" if USE_POSTGRES else "SELECT password FROM auth WHERE username=?", (u,))
    r=c.fetchone(); conn.close()
    if not r or not check_password_hash(r[0], p): return jsonify({"ok":False,"error":"Wrong"})
    session['username']=u; return jsonify({"ok":True})
@app.route('/signup', methods=['POST'])
def signup():
    d=request.json; u=d.get('username','').strip()[:20]; p=d.get('password','')
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT 1 FROM auth WHERE username=%s" if USE_POSTGRES else "SELECT 1 FROM auth WHERE username=?", (u,))
    if c.fetchone(): conn.close(); return jsonify({"ok":False,"error":"Taken"})
    c.execute("INSERT INTO auth VALUES (%s,%s,%s)" if USE_POSTGRES else "INSERT INTO auth VALUES (?,?,?)", (u, generate_password_hash(p), datetime.now().isoformat()))
    c.execute("INSERT INTO users (username,online_at) VALUES (%s,%s)" if USE_POSTGRES else "INSERT INTO users (username,online_at) VALUES (?,?)", (u, datetime.now().isoformat()))
    conn.commit(); conn.close(); session['username']=u; return jsonify({"ok":True})
@app.route('/logout')
def logout(): session.clear(); return redirect('/login')
@app.route('/')
def home():
    if 'username' not in session: return redirect('/login')
    return render_template_string(MAIN, username=session['username'])
@app.route('/chats')
def chats_page():
    if 'username' not in session: return redirect('/login')
    return render_template_string(CHATS_HTML)
@app.route('/chat/<other>')
def chat_page(other):
    if 'username' not in session: return redirect('/login')
    return render_template_string(CHAT_HTML, other=other, me=session['username'])

def add_notif(to_user, from_user, ntype, text=""):
    if to_user==from_user: return
    try:
        conn=get_conn(); c=conn.cursor()
        c.execute("INSERT INTO notifications (to_user,from_user,type,text,is_read,created_at) VALUES (%s,%s,%s,%s,0,%s)" if USE_POSTGRES else "INSERT INTO notifications (to_user,from_user,type,text,is_read,created_at) VALUES (?,?,?,?,0,?)", (to_user,from_user,ntype,text,datetime.now().isoformat()[:16]))
        conn.commit(); conn.close()
    except: pass

@app.route('/upload/post', methods=['POST'])
def upost():
    if 'username' not in session: return jsonify({"ok":False})
    d=request.json; conn=get_conn(); c=conn.cursor()
    c.execute("INSERT INTO posts (username,media,media_type,created_at,likes) VALUES (%s,%s,%s,%s,0)" if USE_POSTGRES else "INSERT INTO posts (username,media,media_type,created_at,likes) VALUES (?,?,?,?,0)", (session['username'],d.get('media'),d.get('media_type'),datetime.now().isoformat()))
    conn.commit(); conn.close(); return jsonify({"ok":True})
@app.route('/upload/story', methods=['POST'])
def ustory():
    if 'username' not in session: return jsonify({"ok":False})
    d=request.json; now=datetime.now(); exp=now+timedelta(hours=24)
    conn=get_conn(); c=conn.cursor()
    if USE_POSTGRES:
        c.execute("INSERT INTO stories (username,media,media_type,created_at,expires_at) VALUES (%s,%s,%s,%s,%s)", (session['username'],d.get('media'),d.get('media_type'),now.isoformat(),exp.isoformat()))
    else:
        c.execute("INSERT INTO stories (username,media,media_type,created_at,expires_at) VALUES (?,?,?,?,?)", (session['username'],d.get('media'),d.get('media_type'),now.isoformat(),exp.isoformat()))
    conn.commit(); conn.close(); return jsonify({"ok":True})
@app.route('/feed')
def feed():
    if 'username' not in session: return jsonify([])
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT id,username,media,media_type,likes,created_at FROM posts ORDER BY id DESC LIMIT 20")
    rows=c.fetchall(); out=[]
    for r in rows:
        c.execute("SELECT 1 FROM likes WHERE post_id=%s AND username=%s" if USE_POSTGRES else "SELECT 1 FROM likes WHERE post_id=? AND username=?", (r[0],session['username']))
        liked=bool(c.fetchone())
        c.execute("SELECT online_at FROM users WHERE username=%s" if USE_POSTGRES else "SELECT online_at FROM users WHERE username=?", (r[1],))
        o=c.fetchone(); online=False
        if o and o[0]:
            try: online=(datetime.now()-datetime.fromisoformat(o[0])).total_seconds()<120
            except: pass
        out.append({"id":r[0],"username":r[1],"media":r[2],"media_type":r[3],"likes":r[4],"created_at":r[5][:16],"liked":liked,"online":online})
    conn.close(); return jsonify(out)
@app.route('/stories')
def stories():
    conn=get_conn(); c=conn.cursor()
    now=datetime.now().isoformat()
    c.execute("DELETE FROM stories WHERE expires_at<%s" if USE_POSTGRES else "DELETE FROM stories WHERE expires_at<?", (now,))
    c.execute("SELECT username FROM stories ORDER BY id DESC LIMIT 30")
    rows=c.fetchall(); out=[]
    for r in rows:
        c.execute("SELECT online_at FROM users WHERE username=%s" if USE_POSTGRES else "SELECT online_at FROM users WHERE username=?", (r[0],))
        o=c.fetchone(); online=False
        if o and o[0]:
            try: online=(datetime.now()-datetime.fromisoformat(o[0])).total_seconds()<120
            except: pass
        out.append({"username":r[0],"online":online})
    conn.commit(); conn.close()
    return jsonify(out)
@app.route('/streak')
def streak(): return jsonify({"streak":12})
@app.route('/like/<int:id>', methods=['POST'])
def like(id):
    if 'username' not in session: return jsonify({"ok":False})
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT username FROM posts WHERE id=%s" if USE_POSTGRES else "SELECT username FROM posts WHERE id=?", (id,))
    owner=c.fetchone()
    c.execute("SELECT 1 FROM likes WHERE post_id=%s AND username=%s" if USE_POSTGRES else "SELECT 1 FROM likes WHERE post_id=? AND username=?", (id,session['username']))
    if c.fetchone():
        c.execute("DELETE FROM likes WHERE post_id=%s AND username=%s" if USE_POSTGRES else "DELETE FROM likes WHERE post_id=? AND username=?", (id,session['username']))
        c.execute("UPDATE posts SET likes=likes-1 WHERE id=%s" if USE_POSTGRES else "UPDATE posts SET likes=likes-1 WHERE id=?", (id,))
        liked=False
    else:
        c.execute("INSERT INTO likes (post_id,username) VALUES (%s,%s)" if USE_POSTGRES else "INSERT INTO likes (post_id,username) VALUES (?,?)", (id,session['username']))
        c.execute("UPDATE posts SET likes=likes+1 WHERE id=%s" if USE_POSTGRES else "UPDATE posts SET likes=likes+1 WHERE id=?", (id,))
        liked=True
        if owner: add_notif(owner[0], session['username'], 'like')
    c.execute("SELECT likes FROM posts WHERE id=%s" if USE_POSTGRES else "SELECT likes FROM posts WHERE id=?", (id,))
    likes=c.fetchone()[0]
    conn.commit(); conn.close()
    return jsonify({"ok":True,"likes":likes,"liked":liked})
@app.route('/replies/<int:id>')
def greplies(id):
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT username,text FROM replies WHERE post_id=%s ORDER BY id ASC" if USE_POSTGRES else "SELECT username,text FROM replies WHERE post_id=? ORDER BY id ASC", (id,))
    rows=c.fetchall(); conn.close()
    return jsonify([{"username":r[0],"text":r[1]} for r in rows])
@app.route('/reply/<int:id>', methods=['POST'])
def reply(id):
    if 'username' not in session: return jsonify({"ok":False})
    conn=get_conn(); c=conn.cursor()
    text=request.json.get('text','')[:200]
    c.execute("SELECT username FROM posts WHERE id=%s" if USE_POSTGRES else "SELECT username FROM posts WHERE id=?", (id,))
    owner=c.fetchone()
    c.execute("INSERT INTO replies (post_id,username,text,created_at) VALUES (%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO replies (post_id,username,text,created_at) VALUES (?,?,?,?)", (id,session['username'],text,datetime.now().isoformat()))
    conn.commit(); conn.close()
    if owner: add_notif(owner[0], session['username'], 'comment', text)
    return jsonify({"ok":True})
@app.route('/notifications')
def notifs():
    if 'username' not in session: return jsonify([])
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT from_user,type,text,is_read,created_at FROM notifications WHERE to_user=%s ORDER BY id DESC LIMIT 30" if USE_POSTGRES else "SELECT from_user,type,text,is_read,created_at FROM notifications WHERE to_user=? ORDER BY id DESC LIMIT 30", (session['username'],))
    rows=c.fetchall(); conn.close()
    return jsonify([{"from_user":r[0],"type":r[1],"text":r[2],"is_read":bool(r[3]),"created_at":r[4]} for r in rows])
@app.route('/notifications/read', methods=['POST'])
def notifs_read():
    if 'username' not in session: return jsonify({"ok":False})
    conn=get_conn(); c=conn.cursor()
    c.execute("UPDATE notifications SET is_read=1 WHERE to_user=%s" if USE_POSTGRES else "UPDATE notifications SET is_read=1 WHERE to_user=?", (session['username'],))
    conn.commit(); conn.close()
    return jsonify({"ok":True})
@app.route('/chats/list')
def clist():
    if 'username' not in session: return jsonify([])
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT DISTINCT receiver FROM chats WHERE sender=%s UNION SELECT DISTINCT sender FROM chats WHERE receiver=%s" if USE_POSTGRES else "SELECT DISTINCT receiver FROM chats WHERE sender=? UNION SELECT DISTINCT sender FROM chats WHERE receiver=?", (session['username'],session['username']))
    users=[r[0] for r in c.fetchall()] or ["Jerrick Smith"]
    out=[]
    for u in users:
        c.execute("SELECT text,media_type FROM chats WHERE (sender=%s AND receiver=%s) OR (sender=%s AND receiver=%s) ORDER BY id DESC LIMIT 1" if USE_POSTGRES else "SELECT text,media_type FROM chats WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) ORDER BY id DESC LIMIT 1", (session['username'],u,u,session['username']))
        last=c.fetchone()
        c.execute("SELECT online_at FROM users WHERE username=%s" if USE_POSTGRES else "SELECT online_at FROM users WHERE username=?", (u,))
        o=c.fetchone(); online=False
        if o and o[0]:
            try: online=(datetime.now()-datetime.fromisoformat(o[0])).total_seconds()<120
            except: pass
        key=f"{u}->{session['username']}"; typing=False
        if key in typing_tracker:
            if (datetime.now()-typing_tracker[key]).total_seconds()<3: typing=True
        msg=last[0][:25] if last and last[0] else ("🎤 voice" if last and last[1]=='audio' else "📸 Media" if last else "Tap to chat")
        out.append({"username":u,"last_msg":msg,"online":online,"typing":typing})
    conn.close(); return jsonify(out)
@app.route('/chat/<other>/typing', methods=['POST'])
def typing(other):
    if 'username' not in session: return jsonify({"ok":False})
    typing_tracker[f"{session['username']}->{other}"]=datetime.now()
    return jsonify({"ok":True})
@app.route('/chat/<other>/status')
def chat_status(other):
    if 'username' not in session: return jsonify({"online":False})
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT online_at FROM users WHERE username=%s" if USE_POSTGRES else "SELECT online_at FROM users WHERE username=?", (other,))
    o=c.fetchone(); conn.close()
    online=False; last_seen="a while ago"
    if o and o[0]:
        try:
            diff=(datetime.now()-datetime.fromisoformat(o[0])).total_seconds()
            online=diff<120
            last_seen=f"{int(diff//60)}m ago" if diff>60 else "just now"
        except: pass
    key=f"{other}->{session['username']}"; typing=False
    if key in typing_tracker:
        if (datetime.now()-typing_tracker[key]).total_seconds()<3: typing=True
    return jsonify({"online":online,"last_seen":last_seen,"typing":typing})
@app.route('/chat/<other>/messages')
def cmsgs(other):
    if 'username' not in session: return jsonify([])
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT sender,text,media,media_type,reply_to,created_at FROM chats WHERE (sender=%s AND receiver=%s) OR (sender=%s AND receiver=%s) ORDER BY id ASC LIMIT 100" if USE_POSTGRES else "SELECT sender,text,media,media_type,reply_to,created_at FROM chats WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) ORDER BY id ASC LIMIT 100", (session['username'],other,other,session['username']))
    rows=c.fetchall(); conn.close()
    return jsonify([{"sender":r[0],"text":r[1],"media":r[2],"media_type":r[3],"reply_to":r[4],"created_at":r[5][:16]} for r in rows])
@app.route('/chat/<other>/send', methods=['POST'])
def csend(other):
    if 'username' not in session: return jsonify({"ok":False})
    d=request.json; conn=get_conn(); c=conn.cursor()
    c.execute("INSERT INTO chats (sender,receiver,text,media,media_type,reply_to,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO chats (sender,receiver,text,media,media_type,reply_to,created_at) VALUES (?,?,?,?,?,?,?)", (session['username'],other,d.get('text'),d.get('media'),d.get('media_type'),d.get('reply_to'),datetime.now().isoformat()))
    conn.commit(); conn.close()
    add_notif(other, session['username'], 'message', d.get('text','media')[:30])
    return jsonify({"ok":True})

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.environ.get("PORT",5000)))
