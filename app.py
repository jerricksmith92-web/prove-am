import os
from flask import Flask, request, jsonify, render_template_string, session, redirect
from datetime import datetime, timedelta, date
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "proveam-final-2026-beautiful-fast"
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
    conn = get_conn(); c = conn.cursor()
    PG = USE_POSTGRES
    def q(pg,lite): return pg if PG else lite
    c.execute(q("CREATE TABLE IF NOT EXISTS auth (username TEXT PRIMARY KEY, password TEXT, created_at TEXT)",
                "CREATE TABLE IF NOT EXISTS auth (username TEXT PRIMARY KEY, password TEXT, created_at TEXT)"))
    c.execute(q("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, streak INT, last_date TEXT, longest INT)",
                "CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, streak INTEGER, last_date TEXT, longest INTEGER)"))
    c.execute(q("CREATE TABLE IF NOT EXISTS friends (id SERIAL PRIMARY KEY, user1 TEXT, user2 TEXT, created_at TEXT)",
                "CREATE TABLE IF NOT EXISTS friends (id INTEGER PRIMARY KEY AUTOINCREMENT, user1 TEXT, user2 TEXT, created_at TEXT)"))
    c.execute(q("CREATE TABLE IF NOT EXISTS posts (id SERIAL PRIMARY KEY, username TEXT, media TEXT, media_type TEXT, task TEXT, likes INT DEFAULT 0, created_at TEXT, expires_at TEXT)",
                "CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, media TEXT, media_type TEXT, task TEXT, likes INTEGER DEFAULT 0, created_at TEXT, expires_at TEXT)"))
    c.execute(q("CREATE TABLE IF NOT EXISTS likes (id SERIAL PRIMARY KEY, post_id INT, username TEXT)",
                "CREATE TABLE IF NOT EXISTS likes (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, username TEXT)"))
    c.execute(q("CREATE TABLE IF NOT EXISTS replies (id SERIAL PRIMARY KEY, post_id INT, username TEXT, text TEXT, created_at TEXT)",
                "CREATE TABLE IF NOT EXISTS replies (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, username TEXT, text TEXT, created_at TEXT)"))
    c.execute(q("CREATE TABLE IF NOT EXISTS stories (id SERIAL PRIMARY KEY, username TEXT, media TEXT, media_type TEXT, created_at TEXT, expires_at TEXT, views INT DEFAULT 0)",
                "CREATE TABLE IF NOT EXISTS stories (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, media TEXT, media_type TEXT, created_at TEXT, expires_at TEXT, views INTEGER DEFAULT 0)"))
    c.execute(q("CREATE TABLE IF NOT EXISTS chats (id SERIAL PRIMARY KEY, sender TEXT, receiver TEXT, text TEXT, media TEXT, media_type TEXT, reply_to TEXT, created_at TEXT)",
                "CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, receiver TEXT, text TEXT, media TEXT, media_type TEXT, reply_to TEXT, created_at TEXT)"))
    conn.commit(); conn.close()
init_db()

LOGIN_HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>PROVE AM</title><style>*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:#000;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh}
.box{background:#111;border:1px solid #222;padding:28px;border-radius:20px;width:90%;max-width:360px;text-align:center;box-shadow:0 10px 30px #000}
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
<title>PROVE AM</title><style>
*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui;-webkit-tap-highlight-color:transparent}
body{background:#000;color:#fff;padding-bottom:70px}
.header{position:sticky;top:0;z-index:20;background:#000000F2;backdrop-filter:blur(10px);padding:12px 16px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #1A1A1A}
.nav{position:fixed;bottom:0;left:0;right:0;background:#000;border-top:1px solid #222;display:flex;justify-content:space-around;padding:12px 0;z-index:30}
.nav a{color:#fff;font-size:22px;text-decoration:none}
.reel{position:relative;width:100%;height:78vh;background:#111;overflow:hidden}
.reel video,.reel img{width:100%;height:100%;object-fit:cover}
.reel-top{position:absolute;top:12px;left:12px;right:12px;display:flex;align-items:center;gap:8px;z-index:2}
.follow{border:1px solid #fff;background:transparent;color:#fff;border-radius:6px;padding:4px 12px;font-weight:700;font-size:12px}
.reel-bottom{position:absolute;bottom:0;left:0;right:0;padding:12px;background:linear-gradient(transparent,#000000E6)}
.actions{display:flex;gap:20px;padding:12px 14px;background:#000;font-size:14px;border-bottom:8px solid #0F0F0F;align-items:center}
.modal{position:fixed;inset:0;background:#000000F2;z-index:99;display:none;align-items:center;justify-content:center}
.modal img,.modal video{max-width:100%;max-height:90vh;border-radius:12px}
#commentSheet{display:none;position:fixed;inset:0;z-index:100;background:#00000099}
#sheet{position:absolute;bottom:0;left:0;right:0;background:#1C1C1E;border-radius:22px 22px 0 0;max-height:85vh;display:flex;flex-direction:column;animation:slideUp.25s ease}
@keyframes slideUp{from{transform:translateY(100%)}to{transform:translateY(0)}}
</style></head><body>
<div class="header"><h2 style="letter-spacing:3px;font-weight:900">PROVE AM</h2><div><a href="/stories-page" style="color:#fff;margin-right:16px"><i class="fa-regular fa-circle-play"></i></a><a href="/chats" style="color:#fff"><i class="fa-regular fa-paper-plane"></i></a></div></div>
<div id="feed" style="min-height:60vh;display:flex;align-items:center;justify-content:center;color:#666">Loading feed...</div>

<div class="nav"><a href="/"><i class="fa-solid fa-house"></i></a><a href="/stories-page"><i class="fa-solid fa-clapperboard"></i></a><a href="#" onclick="document.getElementById('fileIn').click()"><i class="fa-regular fa-square-plus"></i></a><a href="/chats"><i class="fa-regular fa-comment-dots"></i></a><a href="/profile"><i class="fa-regular fa-user"></i></a></div>
<input type="file" id="fileIn" accept="image/*,video/*" style="display:none">
<div class="modal" id="viewer" onclick="this.style.display='none'"><img id="viewImg"><video id="viewVid" controls playsinline></video></div>

<!-- COMMENTS BOTTOM SHEET LIKE YOUR PIC -->
<div id="commentSheet" onclick="if(event.target==this)closeComments()"><div id="sheet">
<div style="width:36px;height:4px;background:#555;border-radius:4px;margin:10px auto"></div>
<div style="text-align:center;font-weight:700;padding-bottom:12px;border-bottom:1px solid #333">Comments</div>
<div id="commentList" style="overflow-y:auto;padding:12px;flex:1"></div>
<div style="display:flex;gap:18px;padding:8px 16px;overflow-x:auto;border-top:1px solid #222;font-size:20px"><span>🤣</span><span>😭</span><span>🔥</span><span>👏</span><span>😩</span><span>💯</span><span>😲</span><span>😂</span></div>
<div style="display:flex;align-items:center;gap:10px;padding:10px 12px;background:#1C1C1E;border-top:1px solid #222">
<img src="https://i.pravatar.cc/100?u=me" style="width:32px;height:32px;border-radius:50%">
<div style="flex:1;background:#2C2C2E;border-radius:20px;padding:8px 14px;display:flex;align-items:center">
<input id="commentInput" placeholder="Add a comment..." style="flex:1;background:transparent;border:none;color:#fff;outline:none;font-size:14px">
<button style="background:#444;border:none;color:#fff;border-radius:6px;padding:4px 8px;font-size:11px;font-weight:800;margin-left:6px">GIF</button>
</div><i class="fa-solid fa-gift" style="font-size:20px"></i></div>
</div></div>

<script>
let activePostId=null;
function openView(src,type){let m=document.getElementById('viewer');let im=document.getElementById('viewImg');let vd=document.getElementById('viewVid');if(type=='video'){im.style.display='none';vd.style.display='block';vd.src=src;}else{vd.style.display='none';im.style.display='block';im.src=src;}m.style.display='flex';}
function closeComments(){document.getElementById('commentSheet').style.display='none';}

document.getElementById('fileIn').addEventListener('change',e=>{
 let f=e.target.files[0];if(!f)return;let r=new FileReader();r.onload=ev=>{
  let type=f.type.startsWith('video')?'video':'image';
  fetch('/upload',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media:ev.target.result,media_type:type})}).then(()=>{loadFeed();});
 };r.readAsDataURL(f);
});

async function loadFeed(){
 let r=await fetch('/feed');let posts=await r.json();
 if(posts.length==0){document.getElementById('feed').innerHTML='<div style="padding:40px;text-align:center;color:#666">No posts yet<br><small>Tap + to post pic or video</small></div>';return;}
 document.getElementById('feed').innerHTML=posts.map(p=>`
 <div class="reel">
  ${p.media_type=='video'?`<video src="${p.media}" autoplay muted loop playsinline onclick="this.paused?this.play():this.pause()" ondblclick="likePost(${p.id})"></video>`:`<img src="${p.media}" onclick="openView('${p.media}','${p.media_type}')">`}
  <div class="reel-top"><img src="https://i.pravatar.cc/100?u=${p.username}" style="width:32px;height:32px;border-radius:50%;border:1px solid #fff"><b>${p.username}</b><span style="font-size:11px;color:#ccc"> • Original audio</span><button class="follow">Follow</button></div>
  <div class="reel-bottom"><b>${p.username}</b> ${p.task||'PROVE AM'}<br><small style="color:#aaa">${p.created_at}</small></div>
 </div>
 <div class="actions">
  <span onclick="likePost(${p.id})"><i class="fa-regular fa-heart"></i> ${p.likes}</span>
  <span onclick="toggleReplies(${p.id})"><i class="fa-regular fa-comment"></i> Comment</span>
  <span onclick="sharePost(${p.id})"><i class="fa-regular fa-paper-plane"></i> Share</span>
  <span style="margin-left:auto" onclick="deletePost(${p.id})"><i class="fa-regular fa-trash-can"></i></span>
 </div>
 `).join('');
}
async function likePost(id){await fetch('/like/'+id,{method:'POST'});loadFeed();}
async function deletePost(id){if(!confirm('Delete this post?'))return;let r=await fetch('/delete/'+id,{method:'POST'});let d=await r.json();if(!d.ok){alert(d.error);return;}loadFeed();}
async function toggleReplies(id){activePostId=id;document.getElementById('commentSheet').style.display='block';loadComments(id);}
async function loadComments(id){
 let r=await fetch('/replies/'+id);let reps=await r.json();
 document.getElementById('commentList').innerHTML=reps.length==0?'<center style="color:#666;padding:30px">No comments yet</center>':reps.map((c,i)=>`
 <div style="display:flex;gap:10px;padding:10px 0">
  <img src="https://i.pravatar.cc/100?u=${c.username}" style="width:32px;height:32px;border-radius:50%;border:2px solid #F7B733">
  <div style="flex:1">
   <div style="font-size:13px"><b>${c.username}</b> <span style="color:#888;font-size:11px">5d</span> ${i==0?'<span style="color:#888"> • ❤️ by author</span>':''}</div>
   <div style="font-size:13.5px;margin:4px 0;color:#eee">${c.text}</div>
   <div style="color:#888;font-size:12px;font-weight:600">Reply</div>
   ${i==0?'<div style="color:#888;font-size:12px;margin-top:6px;font-weight:600">— View 267 more replies</div>':''}
  </div>
  <div style="text-align:center"><i class="fa-regular fa-heart" style="color:#888"></i><br><small style="color:#888;font-size:11px">${['33K','474','30.7K','14K'][i]||'12'}</small></div>
 </div>`).join('');
}
document.getElementById('commentInput').addEventListener('keydown',async e=>{
 if(e.key==='Enter'){let t=e.target.value;if(!t.trim())return;await fetch('/reply/'+activePostId,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t})});e.target.value='';loadComments(activePostId);loadFeed();}
});
async function sharePost(id){
 let url=location.origin+'/post/'+id;
 if(navigator.share){try{await navigator.share({title:'PROVE AM',text:'Check this',url});return;}catch(e){}}
 await navigator.clipboard.writeText(url);alert('Link copied! Share am');
}
loadFeed();setInterval(loadFeed,8000);
</script></body></html>"""

CHATS_HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<style>*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:#111B21;color:#fff}
.top{padding:14px 16px;display:flex;justify-content:space-between;align-items:center}.tabs{display:flex;gap:8px;padding:8px 12px;overflow-x:auto}
.tab{background:#182229;color:#8696A0;padding:7px 14px;border-radius:20px;font-size:13px;white-space:nowrap}.tab.active{background:#0A332C;color:#00A884}
.chatRow{display:flex;gap:12px;padding:12px 16px;align-items:center;border-bottom:0.5px solid #222D34}.chatRow img{width:49px;height:49px;border-radius:50%;object-fit:cover}
.badge{background:#00A884;color:#111B21;border-radius:12px;padding:2px 7px;font-size:12px;font-weight:700}.small{color:#8696A0;font-size:13px}a{color:inherit;text-decoration:none}</style></head><body>
<div class="top"><h2 style="font-weight:400">WhatsApp</h2><div><i class="fa fa-camera" style="margin-right:18px"></i><i class="fa fa-ellipsis-v"></i></div></div>
<div style="padding:0 16px 8px"><div style="background:#202C33;border-radius:12px;padding:8px 12px;display:flex;gap:8px;align-items:center;color:#8696A0"><i class="fa fa-search"></i><input placeholder="Search" style="background:transparent;border:none;color:#fff;flex:1;outline:none;font-size:15px"></div></div>
<div class="tabs"><div class="tab active">All</div><div class="tab">Unread 104</div><div class="tab">Favourites</div><div class="tab">Groups 5</div></div>
<div style="padding:14px 16px;display:flex;justify-content:space-between" class="small"><span><i class="fa fa-archive"></i> Archived</span><span>34</span></div>
<div id="list"></div>
<script>async function load(){let r=await fetch('/chats/list');let data=await r.json();document.getElementById('list').innerHTML=data.map(c=>`
<a href="/chat/${c.username}"><div class="chatRow"><img src="https://i.pravatar.cc/100?u=${c.username}"><div style="flex:1"><div style="display:flex;justify-content:space-between"><b>${c.username}</b><small class="small">${c.time}</small></div><div class="small" style="display:flex;justify-content:space-between"><span><i class="fa fa-check-double" style="color:#53BDEB"></i> ${c.last_msg}</span>${c.unread?`<span class="badge">${c.unread}</span>`:''}</div></div></div></a>`).join('');}load();</script></body></html>"""

CHAT_HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<style>*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:#0B141A;color:#fff;display:flex;flex-direction:column;height:100vh;overflow:hidden}
.header{background:#202C33;padding:10px 12px;display:flex;align-items:center;gap:10px}.header img{width:36px;height:36px;border-radius:50%}
#msgs{flex:1;overflow-y:auto;padding:12px;background:url('https://user-images.githubusercontent.com/15075759/28719144-86dc0f70-73b1-11e7-911d-60d70fcded21.png');background-color:#0B141A;display:flex;flex-direction:column;gap:6px}
.msg{padding:7px 9px 4px;border-radius:8px;max-width:78%;position:relative;word-break:break-word;font-size:14.5px;line-height:1.3;box-shadow:0 1px 0.5px rgba(0,0,0,0.3);cursor:pointer}
.me{background:#005C4B;align-self:flex-end;border-radius:12px 0 12px 12px}.other{background:#202C33;align-self:flex-start;border-radius:0 12px 12px 12px}
.time{font-size:10px;color:#ffffff99;display:block;text-align:right;margin-top:4px}.replyBar{background:#182229;border-left:4px solid #00A884;padding:6px 8px;border-radius:6px;margin-bottom:6px;font-size:12px;color:#00A884}
.bar{padding:6px 8px;display:flex;gap:8px;align-items:center;background:#202C33}.bar input{flex:1;background:#2A3942;border:none;border-radius:24px;padding:11px 16px;color:#fff;outline:none;font-size:16px!important}
.iconBtn{width:42px;height:42px;border-radius:50%;background:#00A884;display:flex;align-items:center;justify-content:center;border:none;color:#fff;font-size:18px}
audio{width:190px;height:32px}.modal{position:fixed;inset:0;background:#000000EE;z-index:99;display:none;align-items:center;justify-content:center}.modal img,.modal video{max-width:100%;max-height:90vh;border-radius:12px}</style></head><body>
<div class="header"><a href="/chats" style="color:#fff"><i class="fa fa-arrow-left"></i></a><img src="https://i.pravatar.cc/100?u={{other}}"><div style="flex:1"><b>{{other}}</b><br><small style="color:#8696A0;font-size:11px">online</small></div><i class="fa fa-video"></i><i class="fa fa-phone" style="margin:0 16px"></i><i class="fa fa-ellipsis-v"></i></div>
<div id="msgs"></div>
<div id="replyPreview" style="display:none;background:#182229;padding:8px 12px;border-left:4px solid #00A884"><small id="replyText"></small><i class="fa fa-times" style="float:right" onclick="cancelReply()"></i></div>
<div class="bar"><i class="fa-regular fa-face-smile" style="color:#8696A0;font-size:22px"></i><input id="txt" placeholder="Message" autocomplete="off"><button class="iconBtn" id="mic" onclick="handleSend()"><i class="fa fa-paper-plane" id="micIcon"></i></button><input type="file" id="f" style="display:none" accept="image/*,video/*,audio/*"><button style="background:none;border:none;color:#8696A0;font-size:20px" onclick="document.getElementById('f').click()"><i class="fa fa-paperclip"></i></button></div>
<div class="modal" id="viewer" onclick="this.style.display='none'"><img id="viewImg"><video id="viewVid" controls playsinline></video></div>
<script>
let other="{{other}}";let me="{{me}}";let replyTo=null;let rec=null;let recChunks=[];let isRec=false;
function openView(src,type){let m=document.getElementById('viewer');let im=document.getElementById('viewImg');let vd=document.getElementById('viewVid');if(type=='video'){im.style.display='none';vd.style.display='block';vd.src=src;}else{vd.style.display='none';im.style.display='block';im.src=src;}m.style.display='flex';}
function setReply(t){replyTo=t;document.getElementById('replyText').innerText=t;document.getElementById('replyPreview').style.display='block';}
function cancelReply(){replyTo=null;document.getElementById('replyPreview').style.display='none';}
async function load(){let r=await fetch('/chat/'+other+'/messages');let msgs=await r.json();document.getElementById('msgs').innerHTML=msgs.map(m=>{
 let media='';if(m.media){
  if(m.media_type=='video') media=`<video src="${m.media}" style="width:100%;border-radius:8px" controls playsinline></video>`;
  else if(m.media_type=='audio') media=`<div style="display:flex;align-items:center;gap:6px"><button style="width:32px;height:32px;border-radius:50%;background:#00A884;border:none;color:#fff"><i class="fa fa-play"></i></button><audio controls playsinline preload="metadata" style="width:170px"><source src="${m.media}"></audio></div>`;
  else media=`<img src="${m.media}" style="width:100%;border-radius:8px;cursor:pointer" onclick="openView('${m.media}','${m.media_type}')">`;
 }
 let rep=m.reply_to?`<div class="replyBar">${m.reply_to}</div>`:'';
 return `<div class="${m.sender==me?'msg me':'msg other'}" onclick="setReply('${(m.text||'').replace(/'/g,'')}')">${rep}${media}<div>${m.text||''}</div><span class="time">${m.created_at} ${m.sender==me?'✓✓':''}</span></div>`;
}).join('');let d=document.getElementById('msgs');d.scrollTop=d.scrollHeight;}
async function handleSend(){let t=document.getElementById('txt').value;if(!t &&!isRec){startRec();return;}if(t){await fetch('/chat/'+other+'/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t,reply_to:replyTo})});document.getElementById('txt').value='';cancelReply();load();}}
document.getElementById('txt').addEventListener('input',e=>{document.getElementById('micIcon').className=e.target.value.trim()?'fa fa-paper-plane':'fa fa-microphone';});
document.getElementById('f').addEventListener('change',e=>{let f=e.target.files[0];let r=new FileReader();r.onload=ev=>{let mt=f.type.startsWith('video')?'video':f.type.startsWith('audio')?'audio':'image';fetch('/chat/'+other+'/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media:ev.target.result,media_type:mt,reply_to:replyTo})}).then(()=>{cancelReply();load();});};r.readAsDataURL(f);});
async function startRec(){try{let stream=await navigator.mediaDevices.getUserMedia({audio:true});rec=new MediaRecorder(stream);recChunks=[];rec.ondataavailable=e=>recChunks.push(e.data);rec.onstop=async()=>{let blob=new Blob(recChunks,{type:'audio/webm'});let fr=new FileReader();fr.onload=ev=>{fetch('/chat/'+other+'/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media:ev.target.result,media_type:'audio'})}).then(()=>load());};fr.readAsDataURL(blob);stream.getTracks().forEach(t=>t.stop());isRec=false;document.getElementById('micIcon').className='fa fa-microphone';};rec.start();isRec=true;document.getElementById('micIcon').className='fa fa-stop';setTimeout(()=>{if(isRec)rec.stop();},30000);}catch(e){alert('Mic permission needed');}}
document.getElementById('mic').addEventListener('click',()=>{if(isRec)rec.stop();});setInterval(load,3000);load();
</script></body></html>"""

STORIES_HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<style>*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:#fff;color:#000}
.top{display:flex;justify-content:space-between;align-items:center;padding:10px 12px}.icon{width:36px;height:36px;background:#EFEFEF;border-radius:50%;display:flex;align-items:center;justify-content:center;position:relative}
.friends{display:flex;gap:14px;overflow-x:auto;padding:10px 12px}.friend{flex:0 0 72px;text-align:center}
.ring{width:64px;height:64px;border-radius:50%;border:3px solid #A259FF;display:flex;align-items:center;justify-content:center;position:relative;background:#fff}.ring img{width:58px;height:58px;border-radius:50%;object-fit:cover}
.add{position:absolute;bottom:-6px;left:50%;transform:translateX(-50%);background:#A259FF;color:#fff;font-size:10px;padding:2px 6px;border-radius:10px}.name{font-size:12px;font-weight:600;margin-top:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.user{font-size:10px;color:#999;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.discover{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:10px;padding-bottom:80px}.card{height:220px;border-radius:16px;background:#000;color:#fff;position:relative;padding:10px;display:flex;align-items:flex-end;font-weight:700;font-size:15px;line-height:1.2;overflow:hidden}.card img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:0}.card span{position:relative;z-index:1}
.bottomNav{position:fixed;bottom:0;left:0;right:0;display:flex;justify-content:space-around;padding:12px 0;border-top:1px solid #eee;background:#fff}.badge{position:absolute;top:-6px;right:-8px;background:#FF3040;color:#fff;border-radius:12px;font-size:11px;padding:2px 6px}a{color:inherit;text-decoration:none}</style></head><body>
<div class="top"><div class="icon"><i class="fa fa-user" style="color:#FFD400"></i></div><div class="icon"><i class="fa fa-search"></i></div><b>Stories</b><div class="icon"><i class="fa-regular fa-bell"></i></div><div class="icon"><i class="fa fa-user-plus"></i><span class="badge">28</span></div><div class="icon"><i class="fa fa-ellipsis"></i></div></div>
<div style="padding:0 12px;font-weight:700">Friends <i class="fa fa-chevron-right" style="font-size:10px"></i></div><div class="friends" id="friendsRow"></div>
<div style="padding:10px 12px 0;font-weight:700">Discover</div><div class="discover" id="disc"></div>
<div class="bottomNav"><a href="/"><i class="fa-solid fa-location-dot"></i></a><div style="position:relative"><a href="/chats"><i class="fa-regular fa-comment-dots"></i><span class="badge">39</span></a></div><a href="/"><i class="fa-solid fa-camera"></i></a><i class="fa-solid fa-user-group"></i><i class="fa-solid fa-play"></i></div>
<script>async function load(){let r=await fetch('/stories');let stories=await r.json();document.getElementById('friendsRow').innerHTML=stories.map(s=>`<div class="friend" onclick="viewStory(${s.id})"><div class="ring"><img src="https://i.pravatar.cc/100?u=${s.username}"><span class="add"><i class="fa fa-user-plus"></i></span></div><div class="name">${s.username}</div><div class="user">${s.username.toLowerCase()}</div></div>`).join('')||`<div style="color:#999;padding:10px;font-size:12px">No stories yet</div>`;let r2=await fetch('/feed');let posts=await r2.json();document.getElementById('disc').innerHTML=posts.slice(0,6).map(p=>`<div class="card" onclick="location.href='/'">${p.media_type=='video'?`<video src="${p.media}" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover"></video>`:`<img src="${p.media}">`}<span>${p.task||'PROVE AM'} 👀</span></div>`).join('')+`<div class="card" style="background:#00AEEF"></div><div class="card" style="background:#111"></div>`;}
async function viewStory(id){await fetch('/story/view/'+id,{method:'POST'});alert('Viewed');}load();</script></body></html>"""

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
    return f"<html><body style='background:#000;color:#fff;text-align:center;padding:40px;font-family:system-ui'><h1 style='color:#D4AF37'>@{session['username']}</h1><a href='/' style='color:#D4AF37'>Home</a> | <a href='/logout' style='color:#D4AF37'>Logout</a></body></html>"

@app.route('/upload', methods=['POST'])
def upload():
    if 'username' not in session: return jsonify({"ok":False})
    data=request.json; media=data.get('media'); mtype=data.get('media_type','image')
    now=datetime.now(); exp=now+timedelta(hours=24)
    conn=get_conn(); c=conn.cursor()
    c.execute("INSERT INTO posts (username,media,media_type,created_at,expires_at,likes) VALUES (%s,%s,%s,%s,%s,0)" if USE_POSTGRES else "INSERT INTO posts (username,media,media_type,created_at,expires_at,likes) VALUES (?,?,?,?,?,0)", (session['username'],media,mtype,now.isoformat(),exp.isoformat()))
    c.execute("INSERT INTO stories (username,media,media_type,created_at,expires_at) VALUES (%s,%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO stories (username,media,media_type,created_at,expires_at) VALUES (?,?,?,?,?)", (session['username'],media,mtype,now.isoformat(),exp.isoformat()))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/feed')
def feed():
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT id,username,media,media_type,task,likes,created_at FROM posts ORDER BY id DESC LIMIT 50")
    rows=c.fetchall(); conn.close()
    return jsonify([{"id":r[0],"username":r[1],"media":r[2],"media_type":r[3],"task":r[4],"likes":r[5],"created_at":r[6][:16] if r[6] else ""} for r in rows])

@app.route('/stories')
def stories():
    conn=get_conn(); c=conn.cursor()
    now=datetime.now().isoformat()
    c.execute("DELETE FROM stories WHERE expires_at<%s" if USE_POSTGRES else "DELETE FROM stories WHERE expires_at<?", (now,))
    c.execute("SELECT id,username,media_type FROM stories ORDER BY id DESC LIMIT 30")
    rows=c.fetchall(); conn.commit(); conn.close()
    return jsonify([{"id":r[0],"username":r[1],"media_type":r[2]} for r in rows])

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
    if row[0]!=session['username']: conn.close(); return jsonify({"ok":False,"error":"You can only delete your own"})
    c.execute("DELETE FROM posts WHERE id=%s" if USE_POSTGRES else "DELETE FROM posts WHERE id=?", (id,))
    c.execute("DELETE FROM likes WHERE post_id=%s" if USE_POSTGRES else "DELETE FROM likes WHERE post_id=?", (id,))
    c.execute("DELETE FROM replies WHERE post_id=%s" if USE_POSTGRES else "DELETE FROM replies WHERE post_id=?", (id,))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/chats/list')
def chats_list():
    if 'username' not in session: return jsonify([])
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT user2 FROM friends WHERE user1=%s" if USE_POSTGRES else "SELECT user2 FROM friends WHERE user1=?", (session['username'],))
    rows=c.fetchall(); out=[]
    for r in rows:
        uname=r[0]
        c.execute("SELECT text,created_at FROM chats WHERE (sender=%s AND receiver=%s) OR (sender=%s AND receiver=%s) ORDER BY id DESC LIMIT 1" if USE_POSTGRES else "SELECT text,created_at FROM chats WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) ORDER BY id DESC LIMIT 1", (session['username'],uname,uname,session['username']))
        last=c.fetchone()
        out.append({"username":uname,"last_msg":(last[0][:30] if last and last[0] else "Tap to chat"),"time":(last[1][11:16] if last and last[1] else "6:26 pm"),"unread":0})
    if not out:
        out=[{"username":"Maud","last_msg":"@sophie reacted ❤️ to...","time":"6:26 pm","unread":1},{"username":"Sweet Girl","last_msg":"Voice message","time":"5:10 pm","unread":0}]
    conn.close(); return jsonify(out)

@app.route('/friends/list')
def friends_list():
    if 'username' not in session: return jsonify([])
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT user2 FROM friends WHERE user1=%s" if USE_POSTGRES else "SELECT user2 FROM friends WHERE user1=?", (session['username'],))
    rows=c.fetchall(); conn.close()
    return jsonify([{"username":r[0]} for r in rows])

@app.route('/chat/<other>/messages')
def chat_messages(other):
    if 'username' not in session: return jsonify([])
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT sender,text,media,media_type,reply_to,created_at FROM chats WHERE (sender=%s AND receiver=%s) OR (sender=%s AND receiver=%s) ORDER BY id ASC LIMIT 100" if USE_POSTGRES else "SELECT sender,text,media,media_type,reply_to,created_at FROM chats WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) ORDER BY id ASC LIMIT 100", (session['username'],other,other,session['username']))
    rows=c.fetchall(); conn.close()
    return jsonify([{"sender":r[0],"text":r[1],"media":r[2],"media_type":r[3],"reply_to":r[4],"created_at":r[5][11:16] if r[5] else ""} for r in rows])

@app.route('/chat/<other>/send', methods=['POST'])
def chat_send(other):
    if 'username' not in session: return jsonify({"ok":False})
    data=request.json
    conn=get_conn(); c=conn.cursor()
    c.execute("INSERT INTO chats (sender,receiver,text,media,media_type,reply_to,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO chats (sender,receiver,text,media,media_type,reply_to,created_at) VALUES (?,?,?,?,?,?,?)", (session['username'],other,data.get('text'),data.get('media'),data.get('media_type'),data.get('reply_to'),datetime.now().isoformat()))
    # auto add friend if not exists
    c.execute("SELECT 1 FROM friends WHERE user1=%s AND user2=%s" if USE_POSTGRES else "SELECT 1 FROM friends WHERE user1=? AND user2=?", (session['username'],other))
    if not c.fetchone():
        c.execute("INSERT INTO friends (user1,user2,created_at) VALUES (%s,%s,%s)" if USE_POSTGRES else "INSERT INTO friends (user1,user2,created_at) VALUES (?,?,?)", (session['username'],other,datetime.now().isoformat()))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/post/<int:id>')
def single_post(id): return redirect('/')

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.environ.get("PORT",5000)))
