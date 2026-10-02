import os
from flask import Flask, request, jsonify, render_template_string, session, redirect
from datetime import datetime, timedelta
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "proveam-final-no-zoom-2026"
DB_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = bool(DB_URL)
typing_tracker = {}

def get_conn():
    if USE_POSTGRES:
        import psycopg2
        return psycopg2.connect(DB_URL)
    else:
        c = sqlite3.connect("proveam.db")
        c.row_factory = sqlite3.Row
        return c

def init_db():
    conn=get_conn(); cur=conn.cursor()
    if USE_POSTGRES:
        cur.execute("CREATE TABLE IF NOT EXISTS auth (username TEXT PRIMARY KEY, password TEXT, created_at TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, online_at TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS posts (id SERIAL PRIMARY KEY, username TEXT, media TEXT, media_type TEXT, likes INT DEFAULT 0, created_at TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS stories (id SERIAL PRIMARY KEY, username TEXT, media TEXT, media_type TEXT, created_at TEXT, expires_at TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS likes (id SERIAL PRIMARY KEY, post_id INT, username TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS replies (id SERIAL PRIMARY KEY, post_id INT, username TEXT, text TEXT, created_at TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS chats (id SERIAL PRIMARY KEY, sender TEXT, receiver TEXT, text TEXT, media TEXT, media_type TEXT, reply_to TEXT, created_at TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS notifications (id SERIAL PRIMARY KEY, to_user TEXT, from_user TEXT, type TEXT, text TEXT, is_read INT DEFAULT 0, created_at TEXT)")
    else:
        cur.execute("CREATE TABLE IF NOT EXISTS auth (username TEXT PRIMARY KEY, password TEXT, created_at TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, online_at TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, media TEXT, media_type TEXT, likes INTEGER DEFAULT 0, created_at TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS stories (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, media TEXT, media_type TEXT, created_at TEXT, expires_at TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS likes (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, username TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS replies (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, username TEXT, text TEXT, created_at TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, receiver TEXT, text TEXT, media TEXT, media_type TEXT, reply_to TEXT, created_at TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY AUTOINCREMENT, to_user TEXT, from_user TEXT, type TEXT, text TEXT, is_read INTEGER DEFAULT 0, created_at TEXT)")
    conn.commit(); conn.close()
init_db()

@app.before_request
def upd():
    if 'username' in session:
        try:
            conn=get_conn(); c=conn.cursor()
            c.execute("UPDATE users SET online_at=%s WHERE username=%s" if USE_POSTGRES else "UPDATE users SET online_at=? WHERE username=?", (datetime.now().isoformat(), session['username']))
            conn.commit(); conn.close()
        except: pass

LOGIN = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:#000;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh}.box{background:#111;border:1px solid #222;padding:22px;border-radius:16px;width:90%;max-width:340px;text-align:center}input{width:100%;padding:12px;background:#000;border:1px solid #333;color:#fff;border-radius:10px;margin:6px 0}.btn{width:100%;padding:11px;border-radius:12px;border:none;font-weight:800;background:#D4AF37}</style></head><body>
<div class="box"><div style="width:54px;height:54px;border-radius:50%;border:2px solid #D4AF37;margin:0 auto;display:flex;align-items:center;justify-content:center;color:#D4AF37;font-weight:900">P</div><h2 style="color:#D4AF37;margin:10px">PROVE AM</h2><input id="u" placeholder="Username"><input id="p" type="password" placeholder="Password"><button class="btn" onclick="auth()">Continue</button><p style="font-size:11px;color:#D4AF37;margin-top:8px" onclick="mode=mode=='login'?'signup':'login'">Switch Login / Sign Up</p><p id="m" style="color:#f66"></p></div>
<script>let mode='login';async function auth(){let u=document.getElementById('u').value.trim(),p=document.getElementById('p').value;let r=await fetch('/'+mode,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})});let d=await r.json();if(d.ok)location.href='/';else document.getElementById('m').innerText=d.error}</script></body></html>"""

MAIN = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:#000;color:#fff}
.header{position:sticky;top:0;z-index:20;background:#000;border-bottom:1px solid #1a1a1a;padding:8px}
.tabs{display:flex;gap:6px;margin-top:8px}.tabs button{flex:1;padding:10px;border-radius:20px;border:1px solid #333;background:#111;color:#888;font-weight:700}.tabs button.active{background:#D4AF37;color:#000;border-color:#D4AF37}
.story-bar{display:flex;gap:12px;overflow-x:auto;padding:12px;border-bottom:1px solid #111}.story-circle{min-width:62px;text-align:center;cursor:pointer}.ring{width:58px;height:58px;border-radius:50%;padding:2px;background:linear-gradient(45deg,#D4AF37,#ff6a00);position:relative}.ring img{width:100%;height:100%;border-radius:50%;border:2px solid #000;object-fit:cover}.online-dot{position:absolute;bottom:0;right:0;width:12px;height:12px;background:#00ff00;border-radius:50%;border:2px solid #000}
.card{background:#111;border:1px solid #222;border-radius:14px;margin:10px;overflow:hidden}
.btn{padding:8px 12px;border-radius:10px;border:none;font-weight:800}.btn-gold{background:#D4AF37;color:#000}.btn-dark{background:#222;color:#fff;border:1px solid #333}
.heart{font-size:20px;color:#555;cursor:pointer}.heart.liked{color:#ff3040}
#tab-story{display:block} #tab-post{display:none}
.story-viewer{position:fixed;top:0;left:0;right:0;bottom:0;background:#000;z-index:100;display:none;flex-direction:column}
input{width:100%;padding:10px;background:#000;border:1px solid #333;color:#fff;border-radius:10px;margin:5px 0}
.comment-box{background:#0a0a0a;border-top:1px solid #222;padding:8px;max-height:220px;overflow-y:auto}
/* ZOOM FIX - NO CROP */
.card img,.card video, #feed img, #feed video, #storyFeed img, #storyFeed video {
  width:100%!important; height:auto!important; max-height:70vh!important; object-fit:contain!important; background:#000; display:block;
}
.story-viewer img,.story-viewer video {width:100%!important; height:100%!important; object-fit:contain!important; background:#000;}
#video {object-fit:contain!important; background:#000; height:100vh!important; width:100%!important;}
</style></head><body>
<div class="header">
<div style="display:flex;justify-content:space-between;align-items:center"><div style="display:flex;gap:8px;align-items:center"><div style="width:32px;height:32px;border-radius:50%;background:#D4AF37;color:#000;display:flex;align-items:center;justify-content:center;font-weight:900">P</div><b>PROVE AM</b></div><div style="display:flex;gap:12px;align-items:center"><div style="position:relative" onclick="openNotif()"><i class="fa-solid fa-bell" style="color:#D4AF37;font-size:18px"></i><div id="notifCount" style="display:none;position:absolute;top:-6px;right:-6px;background:#ff3040;color:#fff;font-size:9px;width:16px;height:16px;border-radius:50%;align-items:center;justify-content:center">0</div></div><span style="font-size:11px;color:#888">@{{username}}</span></div></div>
<div class="tabs"><button id="tb-story" class="active" onclick="showTab('story')">Story</button><button id="tb-post" onclick="showTab('post')">Post</button><button onclick="location.href='/chats'">Chat</button></div>
</div>

<div id="notifPanel" style="display:none;position:fixed;top:65px;left:10px;right:10px;background:#111;border:1px solid #333;border-radius:12px;z-index:40;padding:10px;max-height:70vh;overflow-y:auto"><div style="display:flex;justify-content:space-between"><b style="color:#D4AF37">Notifications</b><span onclick="closeNotif()">✕</span></div><div id="notifList"></div></div>

<div id="tab-story">
<div class="story-bar" id="storyBar"></div>
<div class="card" style="padding:12px"><b style="color:#D4AF37;font-size:12px">Story — disappears in 24h</b><div style="display:flex;gap:8px;margin-top:10px"><button class="btn btn-dark" onclick="openCam('story','photo')">📸 Photo</button><button class="btn btn-dark" onclick="openCam('story','video')">🎥 Video</button><button class="btn btn-dark" onclick="document.getElementById('sFile').click()">🖼️ Gallery</button></div><input type="file" id="sFile" accept="image/*,video/*" style="display:none"><button class="btn btn-gold" style="width:100%;margin-top:10px" onclick="doUpload('story')">+ Add Story</button></div>
<div id="storyFeed"></div>
</div>

<div id="tab-post">
<div class="card" style="padding:12px"><b style="color:#D4AF37;font-size:12px">Post — stays forever</b><div style="display:flex;gap:8px;margin-top:10px"><button class="btn btn-dark" onclick="openCam('post','photo')">📸 Photo</button><button class="btn btn-dark" onclick="openCam('post','video')">🎥 Video</button><button class="btn btn-dark" onclick="document.getElementById('pFile').click()">🖼️ Gallery</button></div><input type="file" id="pFile" accept="image/*,video/*" style="display:none"><button class="btn btn-gold" style="width:100%;margin-top:10px" onclick="doUpload('post')">+ Add Post</button></div>
<div id="feed"></div>
</div>

<div id="viewer" class="story-viewer"><div style="padding:12px;display:flex;justify-content:space-between;background:rgba(0,0,0,0.7)"><b id="viewerName"></b><span onclick="closeViewer()" style="font-size:22px;cursor:pointer">✕</span></div><div id="viewerMedia" style="flex:1;display:flex;align-items:center;justify-content:center;background:#000"></div><div style="padding:12px;text-align:center"><button id="viewerDel" class="btn" style="background:#ff3040;color:#fff;display:none" onclick="delCurrentStory()">🗑️ Delete Story</button></div></div>

<video id="video" autoplay playsinline muted style="display:none;position:fixed;top:0;left:0;z-index:60"></video>
<div id="camBar" style="display:none;position:fixed;bottom:15px;left:0;right:0;z-index:61;text-align:center"><button class="btn btn-gold" onclick="doCapture()">CAPTURE / STOP</button> <button class="btn btn-dark" onclick="closeCam()">Cancel</button></div>
<canvas id="canvas" style="display:none"></canvas>

<script>
let curMode='story', curType='photo', stream=null, rec=null, chunks=[], curUser="{{username}}";
let pendingStory=null, pendingStoryType=null, pendingPost=null, pendingPostType=null;
let currentStoryId=null, storiesData=[];

function showTab(t){
 curMode=t;
 document.getElementById('tab-story').style.display = t=='story'? 'block' : 'none';
 document.getElementById('tab-post').style.display = t=='post'? 'block' : 'none';
 document.getElementById('tb-story').className = t=='story'? 'active' : '';
 document.getElementById('tb-post').className = t=='post'? 'active' : '';
 if(t=='story') loadStories(); else loadFeed();
}

async function openCam(mode,type){curMode=mode;curType=type;let v=document.getElementById('video');try{stream=await navigator.mediaDevices.getUserMedia({video:true,audio:type=='video'});v.srcObject=stream;v.style.display='block';document.getElementById('camBar').style.display='block';if(type=='video'){chunks=[];rec=new MediaRecorder(stream);rec.ondataavailable=e=>chunks.push(e.data);rec.onstop=()=>{let b=new Blob(chunks,{type:'video/webm'});let r=new FileReader();r.onload=e=>{storePending(mode,e.target.result,'video');};r.readAsDataURL(b);};rec.start();}}catch(e){alert('Camera blocked')}}
function closeCam(){if(rec&&rec.state=='recording')rec.stop();if(stream)stream.getTracks().forEach(t=>t.stop());document.getElementById('video').style.display='none';document.getElementById('camBar').style.display='none';}
function doCapture(){
 if(curType=='video'){if(rec&&rec.state=='recording')rec.stop();closeCam();return;}
 let v=document.getElementById('video'),c=document.getElementById('canvas');
 c.width=v.videoWidth; c.height=v.videoHeight;
 c.getContext('2d').drawImage(v,0,0,c.width,c.height);
 storePending(curMode,c.toDataURL('image/jpeg',0.5),'image');
 closeCam();
}
function storePending(mode,data,type){if(mode=='post'){pendingPost=data;pendingPostType=type;alert('Post ready — tap + Add Post');}else{pendingStory=data;pendingStoryType=type;alert('Story ready — tap + Add Story');}}
async function doUpload(mode){let data=mode=='post'?pendingPost:pendingStory;let type=mode=='post'?pendingPostType:pendingStoryType;if(!data)return alert('Pick media first');await fetch('/upload/'+mode,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media:data,media_type:type})});if(mode=='post'){pendingPost=null;showTab('post');}else{pendingStory=null;showTab('story');}}

document.getElementById('pFile').addEventListener('change',e=>{let f=e.target.files[0];if(f.size>5*1024*1024)return alert('Max 5MB');let r=new FileReader();r.onload=ev=>{pendingPost=ev.target.result;pendingPostType=f.type.startsWith('video')?'video':'image';};r.readAsDataURL(f);});
document.getElementById('sFile').addEventListener('change',e=>{let f=e.target.files[0];if(f.size>5*1024*1024)return alert('Max 5MB');let r=new FileReader();r.onload=ev=>{pendingStory=ev.target.result;pendingStoryType=f.type.startsWith('video')?'video':'image';};r.readAsDataURL(f);});

async function loadStories(){
 let r=await fetch('/stories'); let data=await r.json();
 document.getElementById('storyBar').innerHTML=data.length==0?'<small style="color:#666">No stories</small>':data.map((s,i)=>`<div class="story-circle" onclick="openViewer(${i})"><div class="ring"><img src="https://i.pravatar.cc/100?u=${s.username}"><div class="online-dot" style="background:${s.online?'#00ff00':'#666'}"></div></div><small style="font-size:9px">${s.username}</small></div>`).join('');
 let r2=await fetch('/stories/feed'); storiesData=await r2.json();
 document.getElementById('storyFeed').innerHTML=storiesData.map((s,i)=>`<div class="card" style="padding:8px"><div style="display:flex;justify-content:space-between"><b>@${s.username} ${s.online?'🟢':''}</b><div><small style="color:#666">${s.created_at}</small> ${s.username==curUser?`<i class="fa-solid fa-trash" style="color:#ff3040;margin-left:8px;cursor:pointer" onclick="delStory(${s.id})"></i>`:''}</div></div><div onclick="openViewer(${i})" style="cursor:pointer">${s.media_type=='video'?`<video src="${s.media}" style="width:100%;margin-top:6px;border-radius:10px" muted></video>`:`<img src="${s.media}" style="width:100%;margin-top:6px;border-radius:10px">`}</div></div>`).join('');
}
function openViewer(idx){let s=storiesData[idx];if(!s)return;currentStoryId=s.id;document.getElementById('viewerName').innerText='@'+s.username;document.getElementById('viewerMedia').innerHTML=s.media_type=='video'?`<video src="${s.media}" controls autoplay style="width:100%;height:100%"></video>`:`<img src="${s.media}" style="width:100%;height:auto">`;document.getElementById('viewerDel').style.display=s.username==curUser?'inline-block':'none';document.getElementById('viewer').style.display='flex';}
function closeViewer(){document.getElementById('viewer').style.display='none';document.getElementById('viewerMedia').innerHTML='';}
async function delCurrentStory(){if(!currentStoryId)return;if(!confirm('Delete story?'))return;await fetch('/delete/story/'+currentStoryId,{method:'POST'});closeViewer();loadStories();}
async function delStory(id){if(!confirm('Delete story?'))return;await fetch('/delete/story/'+id,{method:'POST'});loadStories();}

async function loadFeed(){
 let r=await fetch('/feed'); let posts=await r.json();
 document.getElementById('feed').innerHTML=posts.map(p=>`
 <div class="card">
 <div style="padding:8px 10px;display:flex;justify-content:space-between"><b>@${p.username} ${p.online?'🟢':''}</b><div style="display:flex;gap:8px"><small style="color:#666">${p.created_at}</small>${p.username==curUser?`<i class="fa-solid fa-trash" style="color:#ff3040;cursor:pointer" onclick="delPost(${p.id})"></i>`:''}</div></div>
 ${p.media_type=='video'?`<video src="${p.media}" controls></video>`:`<img src="${p.media}">`}
 <div style="padding:8px 10px;display:flex;gap:16px;align-items:center">
 <i class="fa-solid fa-heart heart ${p.liked?'liked':''}" id="h-${p.id}" onclick="likePost(${p.id})"></i><span id="c-${p.id}" style="font-size:13px">${p.likes}</span>
 <i class="fa-regular fa-comment" style="cursor:pointer" onclick="toggleComments(${p.id})"></i><span style="font-size:13px">Comments</span>
 <i class="fa-solid fa-share" style="cursor:pointer;margin-left:auto" onclick="sharePost(${p.id})"></i>
 </div>
 <div id="commentBox-${p.id}" class="comment-box" style="display:none"><div id="replies-${p.id}"></div><div style="display:flex;gap:6px;margin-top:8px"><input id="comment-${p.id}" placeholder="Add comment..."><button class="btn btn-gold" style="padding:6px 10px" onclick="commentPost(${p.id})">Send</button></div></div>
 </div>`).join('');
 posts.forEach(p=>loadReplies(p.id));
}
function toggleComments(id){let box=document.getElementById('commentBox-'+id);box.style.display=box.style.display=='none'?'block':'none';}
async function likePost(id){let r=await fetch('/like/'+id,{method:'POST'});let d=await r.json();document.getElementById('c-'+id).innerText=d.likes;let h=document.getElementById('h-'+id);if(d.liked)h.classList.add('liked');else h.classList.remove('liked');}
async function commentPost(id){let t=document.getElementById('comment-'+id).value;if(!t.trim())return;await fetch('/reply/'+id,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t})});document.getElementById('comment-'+id).value='';loadReplies(id);}
async function loadReplies(id){let r=await fetch('/replies/'+id);let data=await r.json();let el=document.getElementById('replies-'+id);if(el)el.innerHTML=data.map(x=>`<div style="padding:4px 0;border-bottom:1px solid #1a1a1a"><b>@${x.username}:</b> ${x.text}</div>`).join('')||'<small style="color:#666">No comments</small>';}
async function delPost(id){if(!confirm('Delete post?'))return;await fetch('/delete/post/'+id,{method:'POST'});loadFeed();}
function sharePost(id){let url=location.origin+'/#post-'+id;if(navigator.share){navigator.share({title:'PROVE AM',url});}else{navigator.clipboard.writeText(url);alert('Link copied');}}

async function loadNotifs(){let r=await fetch('/notifications');let data=await r.json();let unread=data.filter(n=>!n.is_read).length;let dot=document.getElementById('notifCount');if(unread>0){dot.style.display='flex';dot.innerText=unread;}else dot.style.display='none';document.getElementById('notifList').innerHTML=data.map(n=>`<div style="padding:8px;border-bottom:1px solid #222;font-size:12px"><b>@${n.from_user}</b> ${n.type} ${n.text}<br><small style="color:#666">${n.created_at}</small></div>`).join('')||'<small>No notifications</small>';}
function openNotif(){document.getElementById('notifPanel').style.display='block';fetch('/notifications/read',{method:'POST'});}function closeNotif(){document.getElementById('notifPanel').style.display='none';}

loadStories(); loadFeed(); loadNotifs();
setInterval(loadNotifs,15000);
</script></body></html>"""

CHATS_HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{background:#000;color:#fff;font-family:system-ui}.header{padding:12px;border-bottom:1px solid #222;position:sticky;top:0;background:#000}.tabs{display:flex;gap:6px;margin-top:8px}.tabs button{flex:1;padding:10px;border-radius:20px;border:1px solid #333;background:#111;color:#888}.tabs button.active{background:#D4AF37;color:#000}</style></head><body>
<div class="header"><b style="color:#D4AF37">PROVE AM — Chats</b><div class="tabs"><button onclick="location.href='/'">Story</button><button onclick="location.href='/'">Post</button><button class="active">Chat</button></div></div><div id="list"></div>
<script>async function load(){let r=await fetch('/chats/list');let d=await r.json();document.getElementById('list').innerHTML=d.map(c=>`<div style="padding:12px;border-bottom:1px solid #111;display:flex;gap:12px;align-items:center" onclick="location.href='/chat/${c.username}'"><img src="https://i.pravatar.cc/100?u=${c.username}" style="width:48px;height:48px;border-radius:50%;object-fit:cover"><div><b>@${c.username} ${c.online?'🟢':''} ${c.typing?'<small style=color:#00ff80>typing...</small>':''}</b><br><small style="color:#888">${c.last_msg}</small></div></div>`).join('');}setInterval(load,3000);load();</script></body></html>"""

CHAT_HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
<style>*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:#0B141A;color:#fff;display:flex;flex-direction:column;height:100vh}.header{background:#202C33;padding:10px;display:flex;align-items:center;gap:10px}.header img{width:36px;height:36px;border-radius:50%;object-fit:cover}#msgs{flex:1;overflow-y:auto;padding:10px;display:flex;flex-direction:column;gap:8px}.msg{padding:8px 10px;border-radius:12px;max-width:82%;position:relative}.me{background:#005C4B;align-self:flex-end;border-radius:12px 12px 0 12px}.other{background:#202C33;align-self:flex-start}.replyTag{border-left:3px solid #53BDEB;padding-left:6px;color:#53BDEB;font-size:11px;margin-bottom:4px}.msg small{font-size:9px;color:#ffffff99;display:block;text-align:right}.del{position:absolute;top:2px;right:6px;font-size:11px;cursor:pointer;color:#ff6b6b}.msg img,.msg video{width:200px!important;height:auto!important;object-fit:contain!important;background:#000;border-radius:8px}
.bar{background:#202C33;padding:8px;display:flex;gap:8px;align-items:center}.bar textarea{flex:1;background:#2A3942;border:none;border-radius:20px;padding:10px;color:#fff;outline:none}.icon{width:42px;height:42px;border-radius:50%;background:#00A884;display:flex;align-items:center;justify-content:center;cursor:pointer}
.replyBar{display:none;background:#182229;border-left:4px solid #00A884;padding:6px 10px;justify-content:space-between}
</style></head><body>
<div class="header"><a href="/chats" style="color:#fff"><i class="fa-solid fa-arrow-left"></i></a><img src="https://i.pravatar.cc/100?u={{other}}"><div style="flex:1"><b>{{other}} <span id="dot" style="width:8px;height:8px;border-radius:50%;display:inline-block;background:#666"></span></b><br><small id="status">offline</small></div></div>
<div id="msgs"></div>
<div id="typing" style="padding:0 12px;font-size:11px;color:#00A884;display:none">{{other}} is typing...</div>
<div id="replyBar" class="replyBar"><div><b id="rn" style="color:#00A884"></b><div id="rt" style="font-size:12px;color:#aaa"></div></div><span onclick="cancelR()" style="cursor:pointer">✕</span></div>
<div class="bar"><button class="icon" style="background:#2A3942" onclick="document.getElementById('f').click()"><i class="fa-solid fa-paperclip"></i></button><textarea id="txt" rows="1" placeholder="Message" oninput="onTyping()"></textarea><button id="mic" class="icon" onmousedown="startR()" onmouseup="stopR()" ontouchstart="startR()" ontouchend="stopR()"><i id="mi" class="fa-solid fa-microphone"></i></button><button id="send" class="icon" style="display:none" onclick="sendT()"><i class="fa-solid fa-paper-plane"></i></button><input type="file" id="f" accept="image/*,video/*" style="display:none"></div>
<script>
let other="{{other}}", me="{{me}}", replyTo=null, rec=null, chunks=[], isRec=false;
function onTyping(){let has=document.getElementById('txt').value.trim().length>0;document.getElementById('send').style.display=has?'flex':'none';document.getElementById('mic').style.display=has?'none':'flex';fetch('/chat/'+other+'/typing',{method:'POST'});}
async function load(){
 let r=await fetch('/chat/'+other+'/messages'); let msgs=await r.json();
 let box=document.getElementById('msgs'); box.innerHTML='';
 msgs.forEach(m=>{
   let isMe=m.sender==me;
   let d=document.createElement('div'); d.className='msg '+(isMe?'me':'other');
   d.innerHTML=`${isMe?`<span class="del" onclick="delMsg(${m.id})">✕</span>`:''}${m.reply_to?`<div class="replyTag">↩ ${m.reply_to}</div>`:''}
   ${m.media_type=='audio'?`<audio src="${m.media}" controls style="width:200px"></audio>`:m.media?(m.media_type=='video'?`<video src="${m.media}" controls></video>`:`<img src="${m.media}">`)+`<div>${m.text||''}</div>`:`<div>${m.text||''}</div>`}
   <small>${m.created_at} ${isMe?'✓✓':''}</small>`;
   d.addEventListener('click',()=>{if(!m.media)setR(m);});
   box.appendChild(d);
 });
 box.scrollTop=box.scrollHeight;
 let rs=await fetch('/chat/'+other+'/status'); let sd=await rs.json();
 let dot=document.getElementById('dot'); let st=document.getElementById('status');
 dot.style.background=sd.online?'#00ff00':'#666';
 st.innerText=sd.typing?'typing...':sd.online?'online':'last seen '+sd.last_seen;
 st.style.color=sd.typing?'#00A884':'#8696A0';
 document.getElementById('typing').style.display=sd.typing?'block':'none';
}
function setR(m){replyTo=m;document.getElementById('replyBar').style.display='flex';document.getElementById('rn').innerText=m.sender;document.getElementById('rt').innerText=(m.text||'[media]').substring(0,40);}
function cancelR(){replyTo=null;document.getElementById('replyBar').style.display='none';}
async function sendT(){let t=document.getElementById('txt').value;if(!t.trim())return;await fetch('/chat/'+other+'/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t,reply_to:replyTo?(replyTo.text||'[media]'):null})});document.getElementById('txt').value='';cancelR();onTyping();load();}
document.getElementById('f').addEventListener('change',e=>{let f=e.target.files[0];if(!f)return;if(f.size>5*1024*1024)return alert('Max 5MB');let r=new FileReader();r.onload=ev=>{fetch('/chat/'+other+'/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media:ev.target.result,media_type:f.type.startsWith('video')?'video':'image',reply_to:replyTo?(replyTo.text||'[media]'):null})}).then(()=>{cancelR();load();});};r.readAsDataURL(f);});
async function startR(){isRec=true;document.getElementById('mi').className='fa-solid fa-stop';try{let s=await navigator.mediaDevices.getUserMedia({audio:true});rec=new MediaRecorder(s);chunks=[];rec.ondataavailable=e=>chunks.push(e.data);rec.onstop=()=>{let b=new Blob(chunks,{type:'audio/webm'});let r=new FileReader();r.onload=ev=>{fetch('/chat/'+other+'/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media:ev.target.result,media_type:'audio',text:'🎤 Voice',reply_to:replyTo?(replyTo.text||'[media]'):null})}).then(()=>{cancelR();load();});};r.readAsDataURL(b);};rec.start();}catch(e){alert('Mic permission needed');}}
function stopR(){if(!isRec)return;isRec=false;document.getElementById('mi').className='fa-solid fa-microphone';if(rec&&rec.state=='recording')rec.stop();}
async function delMsg(id){if(!confirm('Delete?'))return;await fetch('/chat/delete/'+id,{method:'POST'});load();}
setInterval(load,2000);load();
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
    c.execute("INSERT INTO users VALUES (%s,%s)" if USE_POSTGRES else "INSERT INTO users VALUES (?,?)", (u, datetime.now().isoformat()))
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
    c.execute("INSERT INTO stories (username,media,media_type,created_at,expires_at) VALUES (%s,%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO stories (username,media,media_type,created_at,expires_at) VALUES (?,?,?,?,?)", (session['username'],d.get('media'),d.get('media_type'),now.isoformat(),exp.isoformat()))
    conn.commit(); conn.close(); return jsonify({"ok":True})
@app.route('/feed')
def feed():
    if 'username' not in session: return jsonify([])
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT id,username,media,media_type,likes,created_at FROM posts ORDER BY id DESC LIMIT 10")
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
    c.execute("SELECT username FROM stories GROUP BY username ORDER BY MAX(id) DESC LIMIT 20")
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
@app.route('/stories/feed')
def stories_feed():
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT id,username,media,media_type,created_at FROM stories ORDER BY id DESC LIMIT 15")
    rows=c.fetchall(); out=[]
    for r in rows:
        c.execute("SELECT online_at FROM users WHERE username=%s" if USE_POSTGRES else "SELECT online_at FROM users WHERE username=?", (r[1],))
        o=c.fetchone(); online=False
        if o and o[0]:
            try: online=(datetime.now()-datetime.fromisoformat(o[0])).total_seconds()<120
            except: pass
        out.append({"id":r[0],"username":r[1],"media":r[2],"media_type":r[3],"created_at":r[4][:16],"online":online})
    conn.close(); return jsonify(out)
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
@app.route('/delete/post/<int:id>', methods=['POST'])
def del_post(id):
    if 'username' not in session: return jsonify({"ok":False})
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT username FROM posts WHERE id=%s" if USE_POSTGRES else "SELECT username FROM posts WHERE id=?", (id,))
    row=c.fetchone()
    if row and row[0]==session['username']:
        c.execute("DELETE FROM posts WHERE id=%s" if USE_POSTGRES else "DELETE FROM posts WHERE id=?", (id,))
        conn.commit(); conn.close(); return jsonify({"ok":True})
    conn.close(); return jsonify({"ok":False})
@app.route('/delete/story/<int:id>', methods=['POST'])
def del_story(id):
    if 'username' not in session: return jsonify({"ok":False})
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT username FROM stories WHERE id=%s" if USE_POSTGRES else "SELECT username FROM stories WHERE id=?", (id,))
    row=c.fetchone()
    if row and row[0]==session['username']:
        c.execute("DELETE FROM stories WHERE id=%s" if USE_POSTGRES else "DELETE FROM stories WHERE id=?", (id,))
        conn.commit(); conn.close(); return jsonify({"ok":True})
    conn.close(); return jsonify({"ok":False})
@app.route('/chat/delete/<int:id>', methods=['POST'])
def del_chat(id):
    if 'username' not in session: return jsonify({"ok":False})
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT sender FROM chats WHERE id=%s" if USE_POSTGRES else "SELECT sender FROM chats WHERE id=?", (id,))
    row=c.fetchone()
    if row and row[0]==session['username']:
        c.execute("DELETE FROM chats WHERE id=%s" if USE_POSTGRES else "DELETE FROM chats WHERE id=?", (id,))
        conn.commit(); conn.close(); return jsonify({"ok":True})
    conn.close(); return jsonify({"ok":False})
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
    conn.commit(); conn.close(); return jsonify({"ok":True})
@app.route('/chats/list')
def clist():
    if 'username' not in session: return jsonify([])
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT DISTINCT receiver FROM chats WHERE sender=%s UNION SELECT DISTINCT sender FROM chats WHERE receiver=%s" if USE_POSTGRES else "SELECT DISTINCT receiver FROM chats WHERE sender=? UNION SELECT DISTINCT sender FROM chats WHERE receiver=?", (session['username'],session['username']))
    users=[r[0] for r in c.fetchall()] or []
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
        if key in typing_tracker and (datetime.now()-typing_tracker[key]).total_seconds()<3: typing=True
        msg=last[0][:25] if last and last[0] else ("🎤 Voice" if last and last[1]=='audio' else "📸 Media" if last else "Tap to chat")
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
    online=False; last_seen="now"
    if o and o[0]:
        try:
            diff=(datetime.now()-datetime.fromisoformat(o[0])).total_seconds()
            online=diff<120; last_seen=f"{int(diff//60)}m ago" if diff>60 else "just now"
        except: pass
    key=f"{other}->{session['username']}"; typing=False
    if key in typing_tracker and (datetime.now()-typing_tracker[key]).total_seconds()<3: typing=True
    return jsonify({"online":online,"last_seen":last_seen,"typing":typing})
@app.route('/chat/<other>/messages')
def cmsgs(other):
    if 'username' not in session: return jsonify([])
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT id,sender,text,media,media_type,reply_to,created_at FROM chats WHERE (sender=%s AND receiver=%s) OR (sender=%s AND receiver=%s) ORDER BY id ASC LIMIT 100" if USE_POSTGRES else "SELECT id,sender,text,media,media_type,reply_to,created_at FROM chats WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) ORDER BY id ASC LIMIT 100", (session['username'],other,other,session['username']))
    rows=c.fetchall(); conn.close()
    return jsonify([{"id":r[0],"sender":r[1],"text":r[2],"media":r[3],"media_type":r[4],"reply_to":r[5],"created_at":r[6][:16]} for r in rows])
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
