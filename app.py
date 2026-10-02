import os
from flask import Flask, request, jsonify, render_template_string, session, redirect
from datetime import datetime, timedelta
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "proveam-final-2026-v9"
DB_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = bool(DB_URL)

def get_conn():
    if USE_POSTGRES:
        import psycopg2
        return psycopg2.connect(DB_URL)
    conn = sqlite3.connect("proveam.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn(); c = conn.cursor(); PG = USE_POSTGRES
    def q(pg,lite): return pg if PG else lite
    c.execute(q("CREATE TABLE IF NOT EXISTS auth (username TEXT PRIMARY KEY, password TEXT, created_at TEXT)","CREATE TABLE IF NOT EXISTS auth (username TEXT PRIMARY KEY, password TEXT, created_at TEXT)"))
    c.execute(q("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, streak INT, last_date TEXT, longest INT)","CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, streak INTEGER, last_date TEXT, longest INTEGER)"))
    c.execute(q("CREATE TABLE IF NOT EXISTS friends (id SERIAL PRIMARY KEY, user1 TEXT, user2 TEXT, created_at TEXT)","CREATE TABLE IF NOT EXISTS friends (id INTEGER PRIMARY KEY AUTOINCREMENT, user1 TEXT, user2 TEXT, created_at TEXT)"))
    c.execute(q("CREATE TABLE IF NOT EXISTS posts (id SERIAL PRIMARY KEY, username TEXT, media TEXT, media_type TEXT, task TEXT, likes INT DEFAULT 0, created_at TEXT, expires_at TEXT)","CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, media TEXT, media_type TEXT, task TEXT, likes INTEGER DEFAULT 0, created_at TEXT, expires_at TEXT)"))
    c.execute(q("CREATE TABLE IF NOT EXISTS likes (id SERIAL PRIMARY KEY, post_id INT, username TEXT)","CREATE TABLE IF NOT EXISTS likes (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, username TEXT)"))
    c.execute(q("CREATE TABLE IF NOT EXISTS replies (id SERIAL PRIMARY KEY, post_id INT, username TEXT, text TEXT, created_at TEXT)","CREATE TABLE IF NOT EXISTS replies (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, username TEXT, text TEXT, created_at TEXT)"))
    c.execute(q("CREATE TABLE IF NOT EXISTS stories (id SERIAL PRIMARY KEY, username TEXT, media TEXT, media_type TEXT, created_at TEXT, expires_at TEXT, views INT DEFAULT 0)","CREATE TABLE IF NOT EXISTS stories (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, media TEXT, media_type TEXT, created_at TEXT, expires_at TEXT, views INTEGER DEFAULT 0)"))
    c.execute(q("CREATE TABLE IF NOT EXISTS chats (id SERIAL PRIMARY KEY, sender TEXT, receiver TEXT, text TEXT, media TEXT, media_type TEXT, reply_to TEXT, created_at TEXT, viewed INT DEFAULT 0)","CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, receiver TEXT, text TEXT, media TEXT, media_type TEXT, reply_to TEXT, created_at TEXT, viewed INTEGER DEFAULT 0)"))
    try: c.execute("ALTER TABLE chats ADD COLUMN viewed INT DEFAULT 0")
    except: pass
    conn.commit(); conn.close()
init_db()

LOGIN_HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>PROVE AM</title>
<style>*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:#000;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh}
.box{background:#111;border:1px solid #222;padding:28px;border-radius:20px;width:90%;max-width:360px;text-align:center}
input{width:100%;padding:14px;background:#000;border:1px solid #333;color:#fff;border-radius:12px;margin:7px 0;font-size:16px;outline:none}
.btn{width:100%;padding:14px;border:none;border-radius:12px;font-weight:800;margin-top:12px;background:#D4AF37;color:#000;cursor:pointer}</style></head><body>
<div class="box"><div style="width:86px;height:86px;border-radius:50%;border:2px solid #D4AF37;margin:0 auto;display:flex;align-items:center;justify-content:center;font-weight:900;color:#D4AF37;font-size:22px">PROVE</div>
<h1 style="color:#D4AF37;margin:14px 0;letter-spacing:2px">PROVE AM</h1><h3 id="title">Login</h3>
<input id="u" placeholder="Username"><input id="p" type="password" placeholder="Password"><button class="btn" onclick="doAuth()">Continue</button>
<p style="margin-top:14px"><a href="#" onclick="toggleMode()" id="tog" style="color:#D4AF37;font-size:13px">No account? Sign Up</a></p><p id="msg" style="color:#f66;font-size:12px;margin-top:8px"></p></div>
<script>let mode='login';function toggleMode(){mode=mode=='login'?'signup':'login';document.getElementById('title').innerText=mode=='login'?'Login':'Sign Up';document.getElementById('tog').innerText=mode=='login'?'No account? Sign Up':'Have account? Login'}
async function doAuth(){let u=document.getElementById('u').value,p=document.getElementById('p').value;let r=await fetch('/'+mode,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})});let d=await r.json();if(d.ok)location.href='/';else document.getElementById('msg').innerText=d.error;}</script></body></html>"""

MAIN_HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:#000;color:#fff;padding-bottom:0;overflow-x:hidden}
.header{position:sticky;top:0;z-index:20;background:#000;border-bottom:1px solid #222}
.top-tabs{display:flex;justify-content:space-around;padding:0}
.top-tabs a{color:#888;text-decoration:none;font-weight:800;font-size:14px;padding:12px 0;border-bottom:2px solid transparent;width:33%;text-align:center}
.top-tabs a.active{color:#fff;border-bottom:2px solid #fff}
.post{width:100%;background:#000;border-bottom:8px solid #0A0A0A}
.post-top{display:flex;align-items:center;gap:10px;padding:12px 14px}
.post-top img{width:32px;height:32px;border-radius:50%}
.follow{border:1px solid #555;background:transparent;color:#fff;border-radius:6px;padding:4px 10px;font-weight:700;font-size:12px;margin-left:auto}
.post-media{width:100%;background:#000}
.post-media img,.post-media video{width:100%;height:auto;max-height:75vh;object-fit:contain;display:block;background:#000}
.post-actions{display:flex;gap:18px;padding:12px 14px;font-size:20px;align-items:center}
.right{margin-left:auto}
.caption{padding:0 14px 14px;font-size:14px}.small{color:#888;font-size:12px}
.modal{position:fixed;inset:0;background:#000000F2;z-index:99;display:none;align-items:center;justify-content:center}
.modal img,.modal video{max-width:100%;max-height:90vh}
#commentSheet{display:none;position:fixed;inset:0;z-index:100;background:#00000099}
#sheet{position:absolute;bottom:0;left:0;right:0;background:#1C1C1E;border-radius:22px 22px 0 0;max-height:85vh;display:flex;flex-direction:column}
::-webkit-scrollbar{display:none}
.fab{position:fixed;bottom:20px;right:20px;background:#fff;color:#000;width:56px;height:56px;border-radius:50%;border:none;font-size:28px;box-shadow:0 4px 12px rgba(0,0,0,0.6);z-index:25}
</style></head><body>
<div class="header">
 <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 14px">
  <div style="display:flex;align-items:center;gap:8px"><div style="width:34px;height:34px;border-radius:50%;border:2px solid #D4AF37;display:flex;align-items:center;justify-content:center;font-weight:900;color:#D4AF37;font-size:10px">PROVE</div><b style="color:#D4AF37;letter-spacing:2px">PROVE AM</b></div>
  <div style="display:flex;gap:16px;align-items:center"><a href="/chats" style="color:#fff;position:relative"><i class="fa-regular fa-bell" style="font-size:20px"></i><span id="notifBadge" style="position:absolute;top:-6px;right:-8px;background:#FF3040;color:#fff;border-radius:10px;font-size:10px;padding:2px 5px;display:none">0</span></a><a href="/profile" style="color:#fff"><i class="fa-regular fa-user"></i></a></div>
 </div>
 <div class="top-tabs"><a href="/stories-page">Stories</a><a href="/" class="active">Post</a><a href="/chats">Chat 💬</a></div>
</div>
<div id="feed"><div style="padding:40px;text-align:center;color:#666">Loading...</div></div>
<input type="file" id="fileIn" accept="image/*,video/*" style="display:none">
<button class="fab" onclick="document.getElementById('fileIn').click()">+</button>
<div class="modal" id="viewer" onclick="this.style.display='none'"><img id="viewImg"><video id="viewVid" controls playsinline></video></div>
<div id="commentSheet" onclick="if(event.target==this)closeComments()"><div id="sheet">
<div style="width:36px;height:4px;background:#555;border-radius:4px;margin:10px auto"></div>
<div style="text-align:center;font-weight:700;padding-bottom:12px;border-bottom:1px solid #333">Comments 💬 <span style="margin-left:8px">😂 😭 ❤️ 🔥 👏 💯</span></div>
<div id="commentList" style="overflow-y:auto;padding:12px;flex:1"></div>
<div style="display:flex;align-items:center;gap:10px;padding:10px 12px;border-top:1px solid #222">
<img src="https://i.pravatar.cc/100?u=me" style="width:32px;height:32px;border-radius:50%">
<input id="commentInput" placeholder="Add a comment... 😊" style="flex:1;background:#2C2C2E;border:none;border-radius:20px;padding:10px 14px;color:#fff;outline:none">
</div></div></div>
<script>
function openView(src,type){let m=document.getElementById('viewer');let im=document.getElementById('viewImg');let vd=document.getElementById('viewVid');if(type=='video'){im.style.display='none';vd.style.display='block';vd.src=src;}else{vd.style.display='none';im.style.display='block';im.src=src;}m.style.display='flex';}
function closeComments(){document.getElementById('commentSheet').style.display='none';}
let activePostId=null;
document.getElementById('fileIn').addEventListener('change',e=>{let f=e.target.files[0];if(!f)return;let r=new FileReader();r.onload=ev=>{let type=f.type.startsWith('video')?'video':'image';fetch('/upload',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media:ev.target.result,media_type:type})}).then(()=>loadFeed());};r.readAsDataURL(f);});
async function loadFeed(){let r=await fetch('/feed');let posts=await r.json();if(posts.length==0){document.getElementById('feed').innerHTML='<div style="padding:60px;text-align:center;color:#666">No posts yet — tap + to post</div>';return;}document.getElementById('feed').innerHTML=posts.map(p=>`
<div class="post">
 <div class="post-top"><img src="https://i.pravatar.cc/100?u=${p.username}"><b>${p.username}</b><small style="color:#888"> • PROVE AM</small><button class="follow">Follow</button></div>
 <div class="post-media" onclick="openView('${p.media}','${p.media_type}')">${p.media_type=='video'?`<video src="${p.media}" playsinline controls></video>`:`<img src="${p.media}">`}</div>
 <div class="post-actions"><span onclick="likePost(${p.id})"><i class="fa-regular fa-heart"></i> ${p.likes}</span><span onclick="toggleReplies(${p.id})"><i class="fa-regular fa-comment"></i></span><span onclick="sharePost(${p.id})"><i class="fa-regular fa-paper-plane"></i></span><span class="right" onclick="deletePost(${p.id})"><i class="fa-regular fa-trash-can"></i></span></div>
 <div class="caption"><b>${p.username}</b> PROVE AM ✨<br><span class="small">${p.created_at}</span></div>
</div>`).join('');}
async function likePost(id){await fetch('/like/'+id,{method:'POST'});loadFeed();}
async function deletePost(id){if(!confirm('Delete your post?'))return;let r=await fetch('/delete/'+id,{method:'POST'});let d=await r.json();if(!d.ok){alert(d.error);return;}loadFeed();}
async function toggleReplies(id){activePostId=id;document.getElementById('commentSheet').style.display='block';loadComments(id);}
async function loadComments(id){let r=await fetch('/replies/'+id);let reps=await r.json();document.getElementById('commentList').innerHTML=reps.length==0?'<center style="color:#666;padding:20px">No comments yet — be first 💬</center>':reps.map(c=>`<div style="padding:8px 0"><b>${c.username}</b> ${c.text}</div>`).join('');}
document.getElementById('commentInput').addEventListener('keydown',async e=>{if(e.key==='Enter'){let t=e.target.value;if(!t.trim())return;await fetch('/reply/'+activePostId,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t})});e.target.value='';loadComments(activePostId);loadFeed();}});
async function sharePost(id){let url=location.origin+'/post/'+id;if(navigator.share){try{await navigator.share({url});return;}catch(e){}}await navigator.clipboard.writeText(url);alert('Link copied ✅');}
async function updateNotif(){try{let r=await fetch('/notifications');let d=await r.json();let b=document.getElementById('notifBadge');if(d.count>0){b.style.display='block';b.innerText=d.count;}else{b.style.display='none';}}catch(e){}}
loadFeed();updateNotif();setInterval(updateNotif,4000);
</script></body></html>"""

CHATS_HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<style>*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:#000;color:#fff;overflow-x:hidden}::-webkit-scrollbar{display:none}
.header{padding:12px 16px;display:flex;align-items:center;gap:10px;border-bottom:1px solid #222;position:sticky;top:0;background:#000;z-index:10}
.top-tabs{display:flex;justify-content:space-around;padding:0;border-bottom:1px solid #222;background:#000;position:sticky;top:53px;z-index:10}
.top-tabs a{color:#888;text-decoration:none;font-weight:800;font-size:14px;padding:12px 0;border-bottom:2px solid transparent;width:33%;text-align:center}
.top-tabs a.active{color:#fff;border-bottom:2px solid #fff}
.chatRow{display:flex;gap:12px;padding:14px 16px;align-items:center;border-bottom:1px solid #111}
.chatRow img{width:52px;height:52px;border-radius:50%}.small{color:#888;font-size:13px;margin-top:2px}a{color:inherit;text-decoration:none}
</style></head><body>
<div class="header"><div style="display:flex;align-items:center;gap:8px"><div style="width:34px;height:34px;border-radius:50%;border:2px solid #D4AF37;display:flex;align-items:center;justify-content:center;font-weight:900;color:#D4AF37;font-size:10px">PROVE</div><b style="color:#D4AF37;letter-spacing:2px">PROVE AM</b></div></div>
<div class="top-tabs"><a href="/stories-page">Stories</a><a href="/">Post</a><a href="/chats" class="active">Chat 💬</a></div>
<div id="list" style="padding-top:4px">Loading...</div>
<script>
async function load(){let r=await fetch('/chats/list');let data=await r.json();if(data.length==0){document.getElementById('list').innerHTML='<div style="text-align:center;padding:60px;color:#666">No chats yet</div>';return;}
document.getElementById('list').innerHTML=data.map(c=>`
<a href="/chat/${c.username}"><div class="chatRow"><img src="https://i.pravatar.cc/100?u=${c.username}"><div style="flex:1"><div style="display:flex;justify-content:space-between"><b>${c.username}</b><small class="small">${c.time||''}</small></div><div class="small" style="display:flex;gap:6px;align-items:center">${c.is_me?`<i class="fa fa-check-double" style="color:${c.viewed?'#53BDEB':'#8696A0'}"></i>`:''} ${c.last_msg}</div></div></div></a>`).join('');}
load();setInterval(load,3000);
</script></body></html>"""

CHAT_HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<style>*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:#0B141A;color:#fff;display:flex;flex-direction:column;height:100vh;overflow:hidden}
.header{background:#202C33;padding:10px 12px;display:flex;align-items:center;gap:10px}
.header img{width:36px;height:36px;border-radius:50%}
#msgs{flex:1;overflow-y:auto;padding:12px;background:#0B141A;display:flex;flex-direction:column;gap:6px;-webkit-overflow-scrolling:touch}
.msg{padding:7px 9px 4px;border-radius:8px;max-width:78%;word-break:break-word;font-size:14.5px;box-shadow:0 1px 0.5px rgba(0,0,0,0.3)}
.me{background:#005C4B;align-self:flex-end;border-radius:12px 0 12px 12px}.other{background:#202C33;align-self:flex-start;border-radius:0 12px 12px 12px}
.time{font-size:10px;color:#ffffff99;display:block;text-align:right;margin-top:4px}
.replyBar{background:#182229;border-left:4px solid #00A884;padding:6px 8px;border-radius:6px;margin-bottom:6px;font-size:12px;color:#00A884}
.bar{padding:8px;display:flex;gap:8px;align-items:center;background:#202C33}
.bar input{flex:1;background:#2A3942;border:none;border-radius:24px;padding:12px 16px;color:#fff;outline:none;font-size:16px!important}
.iconBtn{width:44px;height:44px;border-radius:50%;display:flex;align-items:center;justify-content:center;border:none;color:#fff;font-size:18px;cursor:pointer;flex-shrink:0}
.mic{background:#00A884}.send{background:#00A884}
audio{width:180px;height:32px;display:block;margin-top:4px}
.modal{position:fixed;inset:0;background:#000000EE;z-index:99;display:none;align-items:center;justify-content:center}
.modal img,.modal video{max-width:100%;max-height:90vh}
#recDot{display:none;color:red;font-size:12px;animation:blink 1s infinite}@keyframes blink{50%{opacity:0}}
</style></head><body>
<div class="header"><a href="/chats" style="color:#fff"><i class="fa fa-arrow-left"></i></a><img src="https://i.pravatar.cc/100?u={{other}}"><div style="flex:1"><b>{{other}}</b><br><small style="color:#8696A0;font-size:11px"><span id="recDot">● REC </span>online 😊</small></div><i class="fa fa-video"></i><i class="fa fa-phone" style="margin:0 16px"></i><i class="fa fa-ellipsis-v"></i></div>
<div id="msgs"></div>
<div id="replyPreview" style="display:none;background:#182229;padding:8px 12px;border-left:4px solid #00A884"><small id="replyText"></small><i class="fa fa-times" style="float:right" onclick="cancelReply()"></i></div>
<div class="bar"><i class="fa-regular fa-face-smile" style="color:#8696A0;font-size:24px"></i><input id="txt" placeholder="Message 😊" autocomplete="off"><button class="iconBtn mic" id="micBtn" onclick="toggleRec()"><i class="fa fa-microphone" id="micIcon"></i></button><button class="iconBtn send" onclick="sendText()"><i class="fa fa-paper-plane"></i></button><input type="file" id="f" style="display:none" accept="image/*,video/*,audio/*"><button style="background:none;border:none;color:#8696A0;font-size:22px" onclick="document.getElementById('f').click()"><i class="fa fa-paperclip"></i></button></div>
<div class="modal" id="viewer" onclick="this.style.display='none'"><img id="viewImg"><video id="viewVid" controls playsinline></video></div>
<script>
let other="{{other}}";let me="{{me}}";let replyTo=null;let rec=null;let chunks=[];let isRec=false;let isNearBottom=true;
function openView(src,type){let m=document.getElementById('viewer');let im=document.getElementById('viewImg');let vd=document.getElementById('viewVid');if(type=='video'){im.style.display='none';vd.style.display='block';vd.src=src;}else{vd.style.display='none';im.style.display='block';im.src=src;}m.style.display='flex';}
function setReply(t){replyTo=t;document.getElementById('replyText').innerText=t;document.getElementById('replyPreview').style.display='block';}
function cancelReply(){replyTo=null;document.getElementById('replyPreview').style.display='none';}
document.getElementById('msgs').addEventListener('scroll',()=>{let el=document.getElementById('msgs');isNearBottom=(el.scrollHeight-el.scrollTop-el.clientHeight)<120;});
async function load(silent=false){let r=await fetch('/chat/'+other+'/messages');let msgs=await r.json();let el=document.getElementById('msgs');let wasNear=isNearBottom;
 el.innerHTML=msgs.map(m=>{
  let media='';if(m.media){
   if(m.media_type=='video') media=`<video src="${m.media}" style="width:100%;border-radius:8px" controls playsinline></video>`;
   else if(m.media_type=='audio') media=`<div style="display:flex;align-items:center;gap:8px;margin:4px 0"><div style="width:36px;height:36px;border-radius:50%;background:#00A884;display:flex;align-items:center;justify-content:center"><i class="fa fa-play"></i></div><audio controls playsinline><source src="${m.media}"></audio></div>`;
   else media=`<img src="${m.media}" style="width:100%;border-radius:8px" onclick="openView('${m.media}','${m.media_type}')">`;
  }
  let rep=m.reply_to?`<div class="replyBar">${m.reply_to}</div>`:'';
  let tick=m.sender==me?(m.viewed?`<i class="fa fa-check-double" style="color:#53BDEB"></i>`:`<i class="fa fa-check-double" style="color:#8696A0"></i>`):'';
  return `<div class="${m.sender==me?'msg me':'msg other'}" onclick="setReply('${(m.text||'').replace(/'/g,'')}')">${rep}${media}<div>${m.text||''}</div><span class="time">${m.created_at} ${tick}</span></div>`;
 }).join('');
 if(!silent||wasNear){el.scrollTop=el.scrollHeight;}
}
async function sendText(){let t=document.getElementById('txt').value;if(!t.trim())return;await fetch('/chat/'+other+'/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t,reply_to:replyTo})});document.getElementById('txt').value='';cancelReply();isNearBottom=true;load();}
document.getElementById('f').addEventListener('change',e=>{let f=e.target.files[0];let fr=new FileReader();fr.onload=ev=>{let mt=f.type.startsWith('video')?'video':f.type.startsWith('audio')?'audio':'image';fetch('/chat/'+other+'/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media:ev.target.result,media_type:mt,reply_to:replyTo})}).then(()=>{cancelReply();isNearBottom=true;load();});};fr.readAsDataURL(f);});
async function toggleRec(){if(isRec){rec.stop();return;}try{let stream=await navigator.mediaDevices.getUserMedia({audio:true});rec=new MediaRecorder(stream);chunks=[];rec.ondataavailable=e=>chunks.push(e.data);rec.onstop=async()=>{let blob=new Blob(chunks,{type:'audio/webm'});let fr=new FileReader();fr.onload=ev=>{fetch('/chat/'+other+'/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media:ev.target.result,media_type:'audio'})}).then(()=>{isNearBottom=true;load();});};fr.readAsDataURL(blob);stream.getTracks().forEach(t=>t.stop());isRec=false;document.getElementById('micIcon').className='fa fa-microphone';document.getElementById('recDot').style.display='none';document.getElementById('micBtn').style.background='#00A884';};rec.start();isRec=true;document.getElementById('micIcon').className='fa fa-stop';document.getElementById('recDot').style.display='inline';document.getElementById('micBtn').style.background='red';setTimeout(()=>{if(isRec)rec.stop();},30000);}catch(e){alert('Allow microphone 🎤');}}
load(false);setInterval(()=>load(true),3000);
</script></body></html>"""

STORIES_HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<style>*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:#fff;color:#000;overflow-x:hidden;padding-bottom:0}
.header{position:sticky;top:0;background:#fff;z-index:10;border-bottom:1px solid #eee}
.top-tabs{display:flex;justify-content:space-around;padding:0;border-bottom:1px solid #eee}
.top-tabs a{color:#888;text-decoration:none;font-weight:800;font-size:14px;padding:12px 0;border-bottom:2px solid transparent;width:33%;text-align:center}
.top-tabs a.active{color:#000;border-bottom:2px solid #000}
.friends-header{display:flex;justify-content:space-between;padding:14px 16px 8px;font-weight:800}
.friends-row{display:flex;gap:14px;overflow-x:auto;padding:8px 16px}::-webkit-scrollbar{display:none}
.story-circle{flex:0 0 70px;text-align:center;cursor:pointer}
.ring{width:64px;height:64px;border-radius:50%;border:3px solid #A259FF;display:flex;align-items:center;justify-content:center;position:relative;background:#f2f2f2;overflow:hidden}
.ring img{width:100%;height:100%;object-fit:cover;border-radius:50%}
.name{font-size:12px;font-weight:600;margin-top:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.upload-box{margin:16px;background:#f6f6f6;border-radius:16px;padding:14px;border:1px dashed #ccc}
.upload-box textarea{width:100%;padding:10px;border-radius:10px;border:1px solid #ddd;margin-top:8px;font-size:14px;outline:none}
.btn{width:100%;background:#000;color:#fff;border:none;border-radius:12px;padding:12px;font-weight:800;margin-top:10px}
.viewer{position:fixed;inset:0;background:#000;z-index:99;display:none;align-items:center;justify-content:center;flex-direction:column}
.viewer img,.viewer video{max-width:100%;max-height:85vh}
</style></head><body>
<div class="header"><div style="display:flex;align-items:center;gap:8px;padding:10px 14px"><div style="width:34px;height:34px;border-radius:50%;border:2px solid #D4AF37;display:flex;align-items:center;justify-content:center;font-weight:900;color:#D4AF37;font-size:10px">PROVE</div><b style="color:#D4AF37;letter-spacing:2px">PROVE AM</b></div>
<div class="top-tabs"><a href="/stories-page" class="active">Stories</a><a href="/">Post</a><a href="/chats">Chat 💬</a></div></div>
<div class="friends-header"><span>Friends ></span><span style="color:#A259FF;font-size:13px" onclick="document.getElementById('fileStory').click()">+ Add Story</span></div>
<div class="friends-row" id="friendsRow"><div style="color:#999;font-size:13px;padding:10px">No stories yet</div></div>
<div class="upload-box"><b>Post a Story ✨</b><br><small style="color:#888">video, picture, or text — disappears in 24h</small>
<input type="file" id="fileStory" accept="image/*,video/*" style="display:none">
<div style="display:flex;gap:8px;margin-top:10px"><button class="btn" style="background:#fff;color:#000;border:1px solid #000;flex:1" onclick="document.getElementById('fileStory').click()"><i class="fa fa-image"></i> Photo/Video</button><button class="btn" style="flex:1" onclick="postTextStory()"><i class="fa fa-font"></i> Text Story</button></div>
<textarea id="textStory" placeholder="Type your text story... 😊" style="display:none"></textarea><button id="sendTextBtn" class="btn" style="display:none;background:#A259FF" onclick="sendTextStory()">Post Text Story 🚀</button></div>
<div class="viewer" id="storyViewer" onclick="this.style.display='none'"><div style="position:absolute;top:14px;left:14px;color:#fff;display:flex;align-items:center;gap:8px"><img id="vAvatar" style="width:32px;height:32px;border-radius:50%"><b id="vName"></b></div><img id="vImg"><video id="vVid" controls autoplay playsinline></video><div id="vText" style="color:#fff;font-size:28px;font-weight:800;padding:20px;text-align:center"></div></div>
<script>
let textMode=false;
function postTextStory(){textMode=!textMode;document.getElementById('textStory').style.display=textMode?'block':'none';document.getElementById('sendTextBtn').style.display=textMode?'block':'none';}
document.getElementById('fileStory').addEventListener('change',e=>{let f=e.target.files[0];if(!f)return;let r=new FileReader();r.onload=ev=>{let type=f.type.startsWith('video')?'video':'image';fetch('/story/upload',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media:ev.target.result,media_type:type})}).then(()=>load());};r.readAsDataURL(f);});
async function sendTextStory(){let t=document.getElementById('textStory').value;if(!t.trim())return;await fetch('/story/upload',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media:t,media_type:'text'})});document.getElementById('textStory').value='';postTextStory();load();}
async function load(){let r=await fetch('/stories');let data=await r.json();if(data.length==0){document.getElementById('friendsRow').innerHTML='<div style="color:#999;font-size:13px;padding:10px">No stories yet — be first ✨</div>';return;}document.getElementById('friendsRow').innerHTML=data.map(s=>`<div class="story-circle" onclick="viewStory(${s.id},'${s.username}','${s.media_type}','${encodeURIComponent((s.media||'').slice(0,500))}' )"><div class="ring">${s.media_type=='text'?`<div style="background:#000;color:#fff;width:100%;height:100%;display:flex;align-items:center;justify-content:center;font-size:10px;padding:4px">${(s.media||'').slice(0,20)}</div>`:`<img src="${s.media_type=='video'?'https://i.pravatar.cc/100?u='+s.username:s.media}">`}</div><div class="name">${s.username}</div></div>`).join('');}
function viewStory(id,username,type,mediaEnc){let media=decodeURIComponent(mediaEnc);document.getElementById('vName').innerText=username;document.getElementById('vAvatar').src='https://i.pravatar.cc/100?u='+username;let viewer=document.getElementById('storyViewer');let img=document.getElementById('vImg');let vid=document.getElementById('vVid');let txt=document.getElementById('vText');img.style.display='none';vid.style.display='none';txt.style.display='none';if(type=='video'){vid.style.display='block';vid.src=media;}else if(type=='text'){txt.style.display='block';txt.innerText=media;}else{img.style.display='block';img.src=media;}viewer.style.display='flex';fetch('/story/view/'+id,{method:'POST'});}
load();
</script></body></html>"""

@app.route('/login', methods=['GET','POST'])
def login_route():
    if request.method=='GET': return render_template_string(LOGIN_HTML)
    data=request.json; u=data.get('username','').strip()[:20]; p=data.get('password','')
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT password FROM auth WHERE username=%s" if USE_POSTGRES else "SELECT password FROM auth WHERE username=?", (u,))
    row=c.fetchone(); conn.close()
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

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

@app.route('/')
def home():
    if 'username' not in session: return redirect('/login')
    return render_template_string(MAIN_HTML)

@app.route('/chats')
def chats_page():
    if 'username' not in session: return redirect('/login')
    return render_template_string(CHATS_HTML)

@app.route('/chat/<other>')
def chat_page(other):
    if 'username' not in session: return redirect('/login')
    return render_template_string(CHAT_HTML, other=other, me=session['username'])

@app.route('/stories-page')
def stories_page_route():
    if 'username' not in session: return redirect('/login')
    return render_template_string(STORIES_HTML)

@app.route('/profile')
def profile():
    if 'username' not in session: return redirect('/login')
    return f"<html><body style='background:#000;color:#fff;text-align:center;padding:40px;font-family:system-ui'><h1 style='color:#D4AF37'>@{session['username']}</h1><br><a href='/' style='color:#D4AF37;text-decoration:none'>Home</a> | <a href='/logout' style='color:#D4AF37;text-decoration:none'>Logout</a></body></html>"

@app.route('/upload', methods=['POST'])
def upload():
    if 'username' not in session: return jsonify({"ok":False})
    data=request.json
    conn=get_conn(); c=conn.cursor(); now=datetime.now(); exp=now+timedelta(hours=24)
    c.execute("INSERT INTO posts (username,media,media_type,created_at,expires_at,likes) VALUES (%s,%s,%s,%s,%s,0)" if USE_POSTGRES else "INSERT INTO posts (username,media,media_type,created_at,expires_at,likes) VALUES (?,?,?,?,?,0)", (session['username'],data.get('media'),data.get('media_type','image'),now.isoformat(),exp.isoformat()))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/story/upload', methods=['POST'])
def story_upload():
    if 'username' not in session: return jsonify({"ok":False})
    data=request.json; now=datetime.now(); exp=now+timedelta(hours=24)
    conn=get_conn(); c=conn.cursor()
    c.execute("INSERT INTO stories (username,media,media_type,created_at,expires_at) VALUES (%s,%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO stories (username,media,media_type,created_at,expires_at) VALUES (?,?,?,?,?)", (session['username'],data.get('media'),data.get('media_type','image'),now.isoformat(),exp.isoformat()))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/feed')
def feed():
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT id,username,media,media_type,task,likes,created_at FROM posts ORDER BY id DESC LIMIT 50")
    rows=c.fetchall(); conn.close()
    return jsonify([{"id":r[0],"username":r[1],"media":r[2],"media_type":r[3],"task":r[4],"likes":r[5],"created_at":r[6][:16] if r[6] else ""} for r in rows])

@app.route('/stories')
def stories():
    conn=get_conn(); c=conn.cursor(); now=datetime.now().isoformat()
    c.execute("DELETE FROM stories WHERE expires_at<%s" if USE_POSTGRES else "DELETE FROM stories WHERE expires_at<?", (now,))
    c.execute("SELECT id,username,media,media_type FROM stories ORDER BY id DESC LIMIT 50")
    rows=c.fetchall(); conn.commit(); conn.close()
    return jsonify([{"id":r[0],"username":r[1],"media":r[2],"media_type":r[3]} for r in rows])

@app.route('/story/view/<int:id>', methods=['POST'])
def view_story(id):
    conn=get_conn(); c=conn.cursor()
    c.execute("UPDATE stories SET views=views+1 WHERE id=%s" if USE_POSTGRES else "UPDATE stories SET views=views+1 WHERE id=?", (id,))
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
    text=request.json.get('text','')[:300]
    conn=get_conn(); c=conn.cursor()
    c.execute("INSERT INTO replies (post_id,username,text,created_at) VALUES (%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO replies (post_id,username,text,created_at) VALUES (?,?,?,?)", (id,session['username'],text,datetime.now().isoformat()))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/replies/<int:id>')
def get_replies(id):
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT username,text FROM replies WHERE post_id=%s ORDER BY id DESC" if USE_POSTGRES else "SELECT username,text FROM replies WHERE post_id=? ORDER BY id DESC", (id,))
    rows=c.fetchall(); conn.close()
    return jsonify([{"username":r[0],"text":r[1]} for r in rows])

@app.route('/delete/<int:id>', methods=['POST'])
def delete_post(id):
    if 'username' not in session: return jsonify({"ok":False,"error":"login"})
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT username FROM posts WHERE id=%s" if USE_POSTGRES else "SELECT username FROM posts WHERE id=?", (id,))
    row=c.fetchone()
    if not row: conn.close(); return jsonify({"ok":False,"error":"Not found"})
    if row[0]!=session['username']: conn.close(); return jsonify({"ok":False,"error":"You can only delete your own post ❌"})
    c.execute("DELETE FROM posts WHERE id=%s" if USE_POSTGRES else "DELETE FROM posts WHERE id=?", (id,))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/notifications')
def notifications():
    if 'username' not in session: return jsonify({"count":0})
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT COUNT(*) FROM chats WHERE receiver=%s AND viewed=0" if USE_POSTGRES else "SELECT COUNT(*) FROM chats WHERE receiver=? AND viewed=0", (session['username'],))
    row=c.fetchone(); conn.close()
    return jsonify({"count": row[0] if row else 0})

@app.route('/chats/list')
def chats_list():
    if 'username' not in session: return jsonify([])
    conn=get_conn(); c=conn.cursor(); me=session['username']
    c.execute("SELECT user2 FROM friends WHERE user1=%s" if USE_POSTGRES else "SELECT user2 FROM friends WHERE user1=?", (me,))
    rows=c.fetchall(); out=[]
    for r in rows:
        uname=r[0]
        c.execute("SELECT text,created_at,viewed,sender,media_type FROM chats WHERE (sender=%s AND receiver=%s) OR (sender=%s AND receiver=%s) ORDER BY id DESC LIMIT 1" if USE_POSTGRES else "SELECT text,created_at,viewed,sender,media_type FROM chats WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) ORDER BY id DESC LIMIT 1", (me,uname,uname,me))
        last=c.fetchone()
        if last:
            msg = last[0][:28] if last[0] else ("🎤 Voice" if last[4]=='audio' else "📷 Photo")
            out.append({"username":uname,"last_msg":msg,"time":(last[1][11:16] if last[1] else ""),"viewed":bool(last[2]),"is_me":last[3]==me})
    if not out: out=[{"username":"Samuel","last_msg":"Boi","time":"20:05","viewed":False,"is_me":True}]
    conn.close(); return jsonify(out)

@app.route('/chat/<other>/messages')
def chat_messages(other):
    if 'username' not in session: return jsonify([])
    conn=get_conn(); c=conn.cursor(); me=session['username']
    c.execute("UPDATE chats SET viewed=1 WHERE sender=%s AND receiver=%s" if USE_POSTGRES else "UPDATE chats SET viewed=1 WHERE sender=? AND receiver=?", (other,me))
    c.execute("SELECT sender,text,media,media_type,reply_to,created_at,viewed FROM chats WHERE (sender=%s AND receiver=%s) OR (sender=%s AND receiver=%s) ORDER BY id ASC LIMIT 150" if USE_POSTGRES else "SELECT sender,text,media,media_type,reply_to,created_at,viewed FROM chats WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) ORDER BY id ASC LIMIT 150", (me,other,other,me))
    rows=c.fetchall(); conn.commit(); conn.close()
    return jsonify([{"sender":r[0],"text":r[1],"media":r[2],"media_type":r[3],"reply_to":r[4],"created_at":r[5][11:16] if r[5] else "","viewed":r[6]} for r in rows])

@app.route('/chat/<other>/send', methods=['POST'])
def chat_send(other):
    if 'username' not in session: return jsonify({"ok":False})
    data=request.json; conn=get_conn(); c=conn.cursor()
    c.execute("INSERT INTO chats (sender,receiver,text,media,media_type,reply_to,created_at,viewed) VALUES (%s,%s,%s,%s,%s,%s,%s,0)" if USE_POSTGRES else "INSERT INTO chats (sender,receiver,text,media,media_type,reply_to,created_at,viewed) VALUES (?,?,?,?,?,?,?,0)", (session['username'],other,data.get('text'),data.get('media'),data.get('media_type'),data.get('reply_to'),datetime.now().isoformat()))
    for a,b in [(session['username'],other),(other,session['username'])]:
        c.execute("SELECT 1 FROM friends WHERE user1=%s AND user2=%s" if USE_POSTGRES else "SELECT 1 FROM friends WHERE user1=? AND user2=?", (a,b))
        if not c.fetchone():
            c.execute("INSERT INTO friends (user1,user2,created_at) VALUES (%s,%s,%s)" if USE_POSTGRES else "INSERT INTO friends (user1,user2,created_at) VALUES (?,?,?)", (a,b,datetime.now().isoformat()))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/post/<int:id>')
def single_post(id): return redirect('/')

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.environ.get("PORT",5000)))
