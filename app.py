import os
from flask import Flask, request, jsonify, render_template_string, session, redirect
from datetime import datetime, timedelta
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import cloudinary, cloudinary.uploader

app = Flask(__name__)
app.secret_key = "proveam-v17-fast-final"
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
DB_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = bool(DB_URL)

CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME")
API_KEY = os.environ.get("CLOUDINARY_API_KEY")
API_SECRET = os.environ.get("CLOUDINARY_API_SECRET")
USE_CLOUD = bool(CLOUD_NAME and API_KEY and API_SECRET)
if USE_CLOUD:
    cloudinary.config(cloud_name=CLOUD_NAME, api_key=API_KEY, api_secret=API_SECRET, secure=True)

AVATAR_CACHE = {}
AVATAR_CACHE_TIME = None

def save_media(data_url, mtype="image"):
    if not data_url: return data_url
    if data_url.startswith("http"): return data_url
    if mtype == "text": return data_url
    if not USE_CLOUD: return data_url
    try:
        res = cloudinary.uploader.upload(data_url, resource_type="auto", folder="proveam", quality="auto:low")
        return res.get("secure_url")
    except:
        return data_url

def get_conn():
    if USE_POSTGRES:
        try:
            import psycopg
            return psycopg.connect(DB_URL)
        except:
            import psycopg2
            return psycopg2.connect(DB_URL)
    conn = sqlite3.connect("proveam.db", check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except: pass
    return conn

def init_db():
    conn = get_conn(); c = conn.cursor()
    def q(pg, lite): return pg if USE_POSTGRES else lite
    c.execute(q("CREATE TABLE IF NOT EXISTS auth (username TEXT PRIMARY KEY, password TEXT, created_at TEXT, avatar TEXT)","CREATE TABLE IF NOT EXISTS auth (username TEXT PRIMARY KEY, password TEXT, created_at TEXT, avatar TEXT)"))
    try: c.execute("ALTER TABLE auth ADD COLUMN avatar TEXT")
    except: pass
    c.execute(q("CREATE TABLE IF NOT EXISTS friends (id SERIAL PRIMARY KEY, user1 TEXT, user2 TEXT, created_at TEXT)","CREATE TABLE IF NOT EXISTS friends (id INTEGER PRIMARY KEY AUTOINCREMENT, user1 TEXT, user2 TEXT, created_at TEXT)"))
    c.execute(q("CREATE TABLE IF NOT EXISTS posts (id SERIAL PRIMARY KEY, username TEXT, media TEXT, media_type TEXT, likes INT DEFAULT 0, created_at TEXT, expires_at TEXT)","CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, media TEXT, media_type TEXT, likes INTEGER DEFAULT 0, created_at TEXT, expires_at TEXT)"))
    c.execute(q("CREATE TABLE IF NOT EXISTS likes (id SERIAL PRIMARY KEY, post_id INT, username TEXT)","CREATE TABLE IF NOT EXISTS likes (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, username TEXT)"))
    c.execute(q("CREATE TABLE IF NOT EXISTS replies (id SERIAL PRIMARY KEY, post_id INT, username TEXT, text TEXT, created_at TEXT)","CREATE TABLE IF NOT EXISTS replies (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, username TEXT, text TEXT, created_at TEXT)"))
    c.execute(q("CREATE TABLE IF NOT EXISTS stories (id SERIAL PRIMARY KEY, username TEXT, media TEXT, media_type TEXT, created_at TEXT, expires_at TEXT, views INT DEFAULT 0, viewers TEXT DEFAULT '')","CREATE TABLE IF NOT EXISTS stories (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, media TEXT, media_type TEXT, created_at TEXT, expires_at TEXT, views INTEGER DEFAULT 0, viewers TEXT DEFAULT '')"))
    c.execute(q("CREATE TABLE IF NOT EXISTS chats (id SERIAL PRIMARY KEY, sender TEXT, receiver TEXT, text TEXT, media TEXT, media_type TEXT, reply_to TEXT, created_at TEXT, viewed INT DEFAULT 0)","CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, receiver TEXT, text TEXT, media TEXT, media_type TEXT, reply_to TEXT, created_at TEXT, viewed INTEGER DEFAULT 0)"))
    c.execute(q("CREATE TABLE IF NOT EXISTS streaks (id SERIAL PRIMARY KEY, user1 TEXT, user2 TEXT, count INT DEFAULT 0, last_date TEXT)","CREATE TABLE IF NOT EXISTS streaks (id INTEGER PRIMARY KEY AUTOINCREMENT, user1 TEXT, user2 TEXT, count INTEGER DEFAULT 0, last_date TEXT)"))
    c.execute(q("CREATE TABLE IF NOT EXISTS notifs (id SERIAL PRIMARY KEY, to_user TEXT, from_user TEXT, type TEXT, text TEXT, post_id INT DEFAULT 0, is_read INT DEFAULT 0, created_at TEXT)","CREATE TABLE IF NOT EXISTS notifs (id INTEGER PRIMARY KEY AUTOINCREMENT, to_user TEXT, from_user TEXT, type TEXT, text TEXT, post_id INTEGER DEFAULT 0, is_read INTEGER DEFAULT 0, created_at TEXT)"))
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(id DESC)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_chats_users ON chats(sender, receiver, id DESC)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_stories_exp ON stories(expires_at)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_likes_post ON likes(post_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_friends_u1 ON friends(user1)")
    except: pass
    conn.commit(); conn.close()
init_db()

def add_notif(to_user, from_user, typ, text, post_id=0):
    if to_user==from_user: return
    try:
        conn=get_conn(); c=conn.cursor()
        c.execute("INSERT INTO notifs (to_user,from_user,type,text,post_id,is_read,created_at) VALUES (%s,%s,%s,%s,%s,0,%s)" if USE_POSTGRES else "INSERT INTO notifs (to_user,from_user,type,text,post_id,is_read,created_at) VALUES (?,?,?,?,?,0,?)", (to_user,from_user,typ,text,post_id,datetime.now().isoformat()))
        conn.commit(); conn.close()
    except: pass

LOGIN_HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>PROVE AM</title><style>*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:#000;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh}.box{background:#111;border:1px solid #222;padding:28px;border-radius:20px;width:90%;max-width:360px;text-align:center}input{width:100%;padding:14px;background:#000;border:1px solid #333;color:#fff;border-radius:12px;margin:7px 0;outline:none}.btn{width:100%;padding:14px;border:none;border-radius:12px;font-weight:800;margin-top:12px;background:#D4AF37;color:#000}</style></head><body><div class="box"><div style="width:86px;height:86px;border-radius:50%;border:2px solid #D4AF37;margin:0 auto;display:flex;align-items:center;justify-content:center;font-weight:900;color:#D4AF37">PROVE</div><h1 style="color:#D4AF37;margin:14px 0">PROVE AM</h1><h3 id="title">Login</h3><input id="u" placeholder="Username"><input id="p" type="password" placeholder="Password"><button class="btn" onclick="doAuth()">Continue</button><p style="margin-top:14px"><a href="#" onclick="toggleMode()" id="tog" style="color:#D4AF37">No account? Sign Up</a></p><p id="msg" style="color:#f66;font-size:12px"></p></div><script>let mode='login';function toggleMode(){mode=mode=='login'?'signup':'login';document.getElementById('title').innerText=mode=='login'?'Login':'Sign Up';document.getElementById('tog').innerText=mode=='login'?'No account? Sign Up':'Have account? Login'}async function doAuth(){let u=document.getElementById('u').value,p=document.getElementById('p').value;let r=await fetch('/'+mode,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})});let d=await r.json();if(d.ok)location.href='/';else document.getElementById('msg').innerText=d.error;}</script></body></html>"""

BASE_HEADER = """<div style="display:flex;justify-content:space-between;align-items:center;padding:12px 14px"><div style="display:flex;align-items:center;gap:8px"><div style="width:34px;height:34px;border-radius:50%;border:2px solid #D4AF37;display:flex;align-items:center;justify-content:center;font-weight:900;color:#D4AF37;font-size:10px">PROVE</div><b style="color:#D4AF37;letter-spacing:2px">PROVE AM</b></div><div style="display:flex;gap:12px;align-items:center"><button onclick="toggleTheme()" style="background:none;border:none;color:var(--text);font-size:18px"><i class="fa fa-moon"></i></button><div style="position:relative" onclick="openNotifs()"><i class="fa fa-bell" style="font-size:20px"></i><span id="notifCount" style="position:absolute;top:-8px;right:-8px;background:red;color:#fff;font-size:10px;padding:2px 5px;border-radius:10px;display:none">0</span></div><button onclick="toggleLowData()" id="lowBtn" style="border:1px solid #00A884;color:#00A884;background:none;border-radius:20px;padding:4px 10px;font-size:11px;font-weight:800">LOW: ON</button><a href="/profile" style="color:var(--text)"><i class="fa-regular fa-user"></i></a></div></div>"""

NOTIF_HTML = """<div id="notifWrap" style="display:none;position:fixed;inset:0;z-index:200;background:#000000AA"><div style="position:absolute;top:0;right:0;width:92%;max-width:380px;height:100%;background:var(--card);overflow-y:auto"><div style="padding:14px;display:flex;justify-content:space-between;border-bottom:1px solid var(--border)"><b>Notifications</b><span onclick="closeNotifs()" style="color:var(--sub)">✕ Close</span></div><div id="notifList" style="padding:10px"></div><button onclick="markAllRead()" style="width:90%;margin:10px 5%;padding:12px;background:var(--text);color:var(--bg);border:none;border-radius:12px;font-weight:800">Mark all read</button></div></div><script>
async function loadNotifCount(){try{let r=await fetch('/notifs/count');let d=await r.json();let el=document.getElementById('notifCount');if(d.count>0){el.style.display='block';el.innerText=d.count;}else{el.style.display='none';}}catch{}}
async function openNotifs(){document.getElementById('notifWrap').style.display='block';let r=await fetch('/notifs');let data=await r.json();document.getElementById('notifList').innerHTML=data.map(n=>`<div style="padding:12px;border-bottom:1px solid var(--border);${n.is_read?'opacity:0.6':''}"><b>${n.from_user}</b> ${n.text}<br><small style="color:var(--sub)">${n.created_at.slice(11,16)} • ${n.type}</small></div>`).join('')||'<div style="padding:20px;text-align:center;color:var(--sub)">No notifications</div>';}
function closeNotifs(){document.getElementById('notifWrap').style.display='none';loadNotifCount();}
async function markAllRead(){await fetch('/notifs/read',{method:'POST'});closeNotifs();}
setInterval(loadNotifCount,5000);loadNotifCount();
</script>"""

MAIN_HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css"><style>:root{--bg:#000;--card:#111;--text:#fff;--border:#222;--sub:#888}body.light{--bg:#f5f5f5;--card:#fff;--text:#000;--border:#ddd;--sub:#666}*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:var(--bg);color:var(--text)}::-webkit-scrollbar{display:none}.header{position:sticky;top:0;z-index:20;background:var(--bg);border-bottom:1px solid var(--border)}.top-tabs{display:flex;justify-content:space-around}.top-tabs a{color:var(--sub);text-decoration:none;font-weight:800;font-size:14px;padding:12px 0;border-bottom:2px solid transparent;width:33%;text-align:center}.top-tabs a.active{color:var(--text);border-bottom:2px solid var(--text)}.post{width:100%;background:var(--bg);border-bottom:8px solid var(--card)}.post-top{display:flex;align-items:center;gap:10px;padding:12px 14px}.post-top img{width:32px;height:32px;border-radius:50%;object-fit:cover}.post-media{width:100%;background:var(--card);min-height:150px;display:flex;align-items:center;justify-content:center}.post-media img,.post-media video{width:100%;max-height:70vh;object-fit:contain;display:block}.post-actions{display:flex;gap:18px;padding:12px 14px;font-size:20px}.modal{position:fixed;inset:0;background:#000000F2;z-index:99;display:none;align-items:center;justify-content:center}.modal img,.modal video{max-width:100%;max-height:90vh}#sheetWrap{display:none;position:fixed;inset:0;z-index:100;background:#00000099}#sheet{position:absolute;bottom:0;left:0;right:0;background:var(--card);border-radius:22px 22px 0 0;max-height:85vh;display:flex;flex-direction:column}.fab{position:fixed;bottom:20px;right:20px;background:var(--text);color:var(--bg);width:56px;height:56px;border-radius:50%;border:none;font-size:28px;z-index:25}.skeleton{background:linear-gradient(90deg,var(--card) 25%, var(--border) 50%, var(--card) 75%);background-size:200% 100%;animation:shim 1s infinite}@keyframes shim{0%{background-position:200% 0}100%{background-position:-200% 0}}</style></head><body id="body"><div class="header">""" + BASE_HEADER + """<div class="top-tabs"><a href="/stories-page">Stories</a><a href="/" class="active">Post</a><a href="/chats">Chat 💬</a></div></div><div id="feed"><div class="post skeleton" style="height:300px"></div><div class="post skeleton" style="height:300px;margin-top:8px"></div></div><input type="file" id="fileIn" accept="image/*,video/*" multiple style="display:none"><button class="fab" onclick="document.getElementById('fileIn').click()">+</button><div class="modal" id="viewer" onclick="this.style.display='none'"><img id="viewImg"><video id="viewVid" controls playsinline></video></div><div id="sheetWrap" onclick="if(event.target==this)closeComments()"><div id="sheet"><div style="width:36px;height:4px;background:var(--sub);border-radius:4px;margin:10px auto"></div><div id="commentList" style="overflow-y:auto;padding:12px;flex:1"></div><div style="display:flex;gap:10px;padding:10px;border-top:1px solid var(--border)"><input id="commentInput" placeholder="Add comment..." style="flex:1;background:var(--bg);border:1px solid var(--border);border-radius:20px;padding:10px 14px;color:var(--text);outline:none"></div></div></div>""" + NOTIF_HTML + """<script>
let allPosts=[];let activePostId=null;let lowData=localStorage.getItem('lowData')!=='off';let currentUser="";let avatars={};
function toggleLowData(){lowData=!lowData;localStorage.setItem('lowData',lowData?'on':'off');updateLowBtn();}
function updateLowBtn(){let b=document.getElementById('lowBtn');if(b)b.innerText=lowData?'LOW: ON':'LOW: OFF';}
function toggleTheme(){document.body.classList.toggle('light');localStorage.setItem('theme',document.body.classList.contains('light')?'light':'dark');}
if(localStorage.getItem('theme')=='light'){document.body.classList.add('light');}updateLowBtn();
async function compressImage(file){return new Promise(res=>{let img=new Image();let url=URL.createObjectURL(file);img.onload=()=>{let max=700;let w=img.width,h=img.height;if(w>max||h>max){if(w>h){h=h*max/w;w=max;}else{w=w*max/h;h=max;}}let c=document.createElement('canvas');c.width=w;c.height=h;c.getContext('2d').drawImage(img,0,0,w,h);res(c.toDataURL('image/jpeg',0.4));URL.revokeObjectURL(url);};img.src=url;});}
document.getElementById('fileIn').addEventListener('change', async e=>{
 let files=[...e.target.files]; if(!files.length)return;
 let tempUrls = [];
 for(let f of files){
   let localUrl = URL.createObjectURL(f);
   tempUrls.push(localUrl);
   let fakePost = {id:Date.now()+Math.random(),username:currentUser,media:localUrl,media_type:f.type.startsWith('video')?'video':'image',likes:0,liked:false};
   allPosts.unshift(fakePost);
 }
 renderFeed();
 for(let f of files){
  if(f.type.startsWith('video') && f.size>25*1024*1024){alert('Video >25MB');continue;}
  let dataUrl = f.type.startsWith('image')? await compressImage(f) : await new Promise(r=>{let fr=new FileReader();fr.onload=ev=>r(ev.target.result);fr.readAsDataURL(f);});
  let type=f.type.startsWith('video')?'video':'image';
  fetch('/upload',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media:dataUrl,media_type:type})}).then(()=>loadFeed());
 }
});
function openViewById(id){let p=allPosts.find(x=>x.id==id);if(!p)return;let m=document.getElementById('viewer'),im=document.getElementById('viewImg'),vd=document.getElementById('viewVid');if(p.media_type=='video'){im.style.display='none';vd.style.display='block';vd.src=p.media;vd.play();}else{vd.style.display='none';im.style.display='block';im.src=p.media;}m.style.display='flex';}
function closeComments(){document.getElementById('sheetWrap').style.display='none';}
function renderFeed(){
 document.getElementById('feed').innerHTML=allPosts.map(p=>{
  let av = avatars[p.username] || `https://i.pravatar.cc/100?u=${p.username}`;
  let mediaTag = p.media_type=='video'?`<video src="${p.media}" controls playsinline preload="metadata" loading="lazy"></video>`:`<img loading="lazy" src="${p.media}">`;
  let delBtn = p.username === currentUser? `<button style="margin-left:auto;background:#ff2222;color:#fff;border:none;border-radius:8px;padding:4px 10px;font-size:12px;font-weight:800" onclick="deletePost(${p.id})"><i class="fa fa-trash"></i></button>` : `<span style="margin-left:auto"></span>`;
  let heart = p.liked? `<i class="fa-solid fa-heart" style="color:red"></i>` : `<i class="fa-regular fa-heart"></i>`;
  return `<div class="post"><div class="post-top"><img src="${av}" loading="lazy"><b>${p.username}</b>${delBtn}</div><div class="post-media" onclick="openViewById(${p.id})">${mediaTag}</div><div class="post-actions"><span onclick="likePost(${p.id})">${heart} ${p.likes}</span><span onclick="toggleReplies(${p.id})"><i class="fa-regular fa-comment"></i></span><span onclick="sharePost(${p.id})"><i class="fa-regular fa-paper-plane"></i></span></div></div>`;
 }).join('');
}
async function loadFeed(){
 try{
  let meR = await fetch('/me'); let meD = await meR.json(); currentUser = meD.username;
  let avR = await fetch('/avatars'); avatars = await avR.json();
  let r=await fetch('/feed');allPosts=await r.json();
  if(allPosts.length==0){document.getElementById('feed').innerHTML='<div style="padding:60px;text-align:center;color:var(--sub)">No posts yet — tap +</div>';return;}
  renderFeed();
 }catch(e){console.log(e);}
}
async function likePost(id){let p=allPosts.find(x=>x.id==id); if(p){p.liked=!p.liked; p.likes+=p.liked?1:-1; renderFeed();} await fetch('/like/'+id,{method:'POST'});}
async function deletePost(id){if(!confirm('Delete?'))return;allPosts=allPosts.filter(p=>p.id!=id);renderFeed();let r=await fetch('/delete/'+id,{method:'POST'});let d=await r.json();if(!d.ok)loadFeed();}
async function toggleReplies(id){activePostId=id;document.getElementById('sheetWrap').style.display='block';loadComments(id);}
async function loadComments(id){let r=await fetch('/replies/'+id);let reps=await r.json();document.getElementById('commentList').innerHTML=reps.map(c=>`<div style="padding:8px 0"><b>${c.username}</b> ${c.text}</div>`).join('')||'<div style="color:var(--sub)">No comments</div>';}
document.getElementById('commentInput').addEventListener('keydown',async e=>{if(e.key==='Enter'){let txt=e.target.value;e.target.value='';document.getElementById('commentList').innerHTML+=`<div><b>${currentUser}</b> ${txt}</div>`;await fetch('/reply/'+activePostId,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:txt})});loadComments(activePostId);}});
async function sharePost(id){let url=location.origin+'/post/'+id;await navigator.clipboard.writeText(url);alert('Link copied');}
loadFeed();
</script></body></html>"""

STORIES_HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css"><style>:root{--bg:#000;--card:#111;--text:#fff;--border:#222;--sub:#888}body.light{--bg:#f5f5f5;--card:#fff;--text:#000;--border:#ddd;--sub:#666}*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:var(--bg);color:var(--text)}::-webkit-scrollbar{display:none}.header{position:sticky;top:0;background:var(--bg);z-index:10;border-bottom:1px solid var(--border)}.top-tabs{display:flex;justify-content:space-around;border-bottom:1px solid var(--border)}.top-tabs a{color:var(--sub);text-decoration:none;font-weight:800;font-size:14px;padding:12px 0;border-bottom:2px solid transparent;width:33%;text-align:center}.top-tabs a.active{color:var(--text);border-bottom:2px solid var(--text)}.friends-row{display:flex;gap:14px;overflow-x:auto;padding:12px 16px}.story-circle{flex:0 0 72px;text-align:center;cursor:pointer;position:relative}.ring{width:66px;height:66px;border-radius:50%;border:3px solid #A259FF;overflow:hidden}.ring img{width:100%;height:100%;object-fit:cover}.badge{position:absolute;top:-2px;right:2px;background:#A259FF;color:#fff;font-size:10px;padding:2px 5px;border-radius:10px}.viewer{position:fixed;inset:0;background:#000;z-index:99;display:none;flex-direction:column}.progress{display:flex;gap:4px;padding:8px;position:absolute;top:0;left:0;right:0;z-index:3}.progress span{flex:1;height:3px;background:#ffffff66}.progress span.active{background:#fff}}</style></head><body id="body"><div class="header">""" + BASE_HEADER + """<div class="top-tabs"><a href="/stories-page" class="active">Stories</a><a href="/">Post</a><a href="/chats">Chat</a></div></div><div class="friends-row" id="friendsRow"><div class="story-circle"><div class="ring" style="background:var(--card)"></div></div></div><div style="margin:16px;background:var(--card);border-radius:16px;padding:14px;border:1px solid var(--border)"><b>Stories</b><input type="file" id="fileStory" accept="image/*,video/*" multiple style="display:none"><div style="display:flex;gap:8px;margin-top:10px"><button style="flex:1;background:var(--text);color:var(--bg);border:none;border-radius:12px;padding:12px;font-weight:800" onclick="document.getElementById('fileStory').click()">📷 Multi</button><button style="flex:1;background:#A259FF;color:#fff;border:none;border-radius:12px;padding:12px;font-weight:800" onclick="postTextStory()">Text</button></div><textarea id="textStory" style="display:none;width:100%;padding:10px;border-radius:10px;margin-top:8px;background:var(--bg);color:var(--text)"></textarea><button id="sendTextBtn" style="display:none;width:100%;background:#A259FF;color:#fff;border:none;border-radius:12px;padding:12px;margin-top:8px" onclick="sendTextStory()">Post</button></div><div class="viewer" id="storyViewer"><div class="progress" id="progress"></div><div style="position:absolute;top:14px;left:14px;right:14px;color:#fff;display:flex;gap:8px;align-items:center;z-index:3"><a onclick="closeViewer()" style="color:#fff"><i class="fa fa-arrow-left"></i></a><img id="vAvatar" style="width:32px;height:32px;border-radius:50%"><b id="vName"></b><span style="margin-left:auto;display:flex;gap:12px;align-items:center"><span id="vViews" style="font-size:13px">👁️ 0</span><button onclick="saveStory()" style="background:var(--card);border:none;color:#fff;padding:6px 10px;border-radius:8px"><i class="fa fa-download"></i> Save</button></span></div><div style="flex:1;display:flex;align-items:center;justify-content:center" id="tapArea"><img id="vImg" style="max-width:100%;max-height:85vh;display:none"><video id="vVid" controls autoplay playsinline style="max-width:100%;max-height:85vh;display:none"></video><div id="vText" style="color:#fff;font-size:28px;font-weight:800;padding:20px;text-align:center;display:none"></div></div><div style="padding:10px;display:flex;gap:8px;background:linear-gradient(transparent, #000)"><input id="replyInput" placeholder="Reply to story..." style="flex:1;background:#222;border:none;border-radius:20px;padding:12px 16px;color:#fff;outline:none"><button onclick="sendStoryReply()" style="background:#A259FF;border:none;color:#fff;width:44px;height:44px;border-radius:50%"><i class="fa fa-paper-plane"></i></button></div></div>""" + NOTIF_HTML + """<script>
let allStories=[];let grouped={};let currentList=[];let currentIndex=0;let timer=null;let avatars={};let currentStory=null;let lowData=localStorage.getItem('lowData')!=='off';
function toggleLowData(){lowData=!lowData;localStorage.setItem('lowData',lowData?'on':'off');updateLowBtn();}
function updateLowBtn(){let b=document.getElementById('lowBtn');if(b)b.innerText=lowData?'LOW: ON':'LOW: OFF';}
function toggleTheme(){document.body.classList.toggle('light');localStorage.setItem('theme',document.body.classList.contains('light')?'light':'dark');}
if(localStorage.getItem('theme')=='light'){document.body.classList.add('light');}updateLowBtn();
async function compressImage(file){return new Promise(res=>{let img=new Image();let url=URL.createObjectURL(file);img.onload=()=>{let max=500;let w=img.width,h=img.height;if(w>max||h>max){if(w>h){h=h*max/w;w=max;}else{w=w*max/h;h=max;}}let c=document.createElement('canvas');c.width=w;c.height=h;c.getContext('2d').drawImage(img,0,0,w,h);res(c.toDataURL('image/jpeg',0.4));URL.revokeObjectURL(url);};img.src=url;});}
let textMode=false;function postTextStory(){textMode=!textMode;document.getElementById('textStory').style.display=textMode?'block':'none';document.getElementById('sendTextBtn').style.display=textMode?'block':'none';}
document.getElementById('fileStory').addEventListener('change', async e=>{
 let files=[...e.target.files];
 for(let f of files){
  let r= f.type.startsWith('image')? await compressImage(f) : await new Promise(res=>{let fr=new FileReader();fr.onload=ev=>res(ev.target.result);fr.readAsDataURL(f);});
  let type=f.type.startsWith('video')?'video':'image';
  fetch('/story/upload',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media:r,media_type:type})});
 }
 setTimeout(load,500);
});
async function sendTextStory(){let t=document.getElementById('textStory').value;if(!t.trim())return;document.getElementById('textStory').value='';postTextStory();fetch('/story/upload',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media:t,media_type:'text'})});load();}
async function load(){let avR=await fetch('/avatars');avatars=await avR.json();let r=await fetch('/stories');allStories=await r.json();grouped={};allStories.forEach(s=>{if(!grouped[s.username])grouped[s.username]=[];grouped[s.username].push(s);});document.getElementById('friendsRow').innerHTML=Object.keys(grouped).map(u=>{let list=grouped[u];let av=avatars[u]||`https://i.pravatar.cc/100?u=${u}`;return `<div class="story-circle" onclick="openUserStories('${u}')"><div class="ring"><img src="${av}" loading="lazy"><span class="badge">${list.length}</span></div><div style="font-size:12px">${u}<br><small>👁️ ${list[0].views||0}</small></div></div>`}).join('');}
function openUserStories(u){currentList=grouped[u];currentIndex=0;showStory();}
function showStory(){let s=currentList[currentIndex];currentStory=s;let av=avatars[s.username]||`https://i.pravatar.cc/100?u=${s.username}`;document.getElementById('vName').innerText=s.username;document.getElementById('vAvatar').src=av;document.getElementById('vViews').innerText='👁️ '+(s.views||0);document.getElementById('progress').innerHTML=currentList.map((_,i)=>`<span class="${i==currentIndex?'active':''}"></span>`).join('');let img=document.getElementById('vImg'),vid=document.getElementById('vVid'),txt=document.getElementById('vText');img.style.display='none';vid.style.display='none';txt.style.display='none';if(s.media_type=='video'){vid.style.display='block';vid.src=s.media;vid.play();}else if(s.media_type=='text'){txt.style.display='block';txt.innerText=s.media;}else{img.style.display='block';img.src=s.media;}document.getElementById('storyViewer').style.display='flex';if(timer)clearTimeout(timer);timer=setTimeout(()=>nextStory(),7000);fetch('/story/view/'+s.id,{method:'POST'});}
function nextStory(){currentIndex++;if(currentIndex>=currentList.length){closeViewer();return;}showStory();}
function closeViewer(){document.getElementById('storyViewer').style.display='none';if(timer)clearTimeout(timer);}
async function sendStoryReply(){let t=document.getElementById('replyInput').value;if(!t.trim()||!currentStory)return;document.getElementById('replyInput').value='';fetch('/story/reply/'+currentStory.id,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t})});alert('Reply sent!');}
function saveStory(){if(!currentStory)return;let a=document.createElement('a');a.href=currentStory.media;a.download='story';a.target='_blank';a.click();}
document.getElementById('tapArea').addEventListener('click',e=>{if(e.clientX < window.innerWidth/2){currentIndex=Math.max(0,currentIndex-1);showStory();}else nextStory();});
load();
</script></body></html>"""

CHATS_HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css"><style>:root{--bg:#000;--card:#111;--text:#fff;--border:#222;--sub:#888}body.light{--bg:#f5f5f5;--card:#fff;--text:#000;--border:#ddd;--sub:#666}*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:var(--bg);color:var(--text)}.header{padding:10px 14px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--border);position:sticky;top:0;background:var(--bg);z-index:10}.top-tabs{display:flex;justify-content:space-around;border-bottom:1px solid var(--border);position:sticky;top:53px;background:var(--bg);z-index:10}.top-tabs a{color:var(--sub);text-decoration:none;font-weight:800;font-size:14px;padding:12px 0;border-bottom:2px solid transparent;width:33%;text-align:center}.top-tabs a.active{color:var(--text);border-bottom:2px solid var(--text)}.chatRow{display:flex;gap:12px;padding:14px 16px;border-bottom:1px solid var(--border)}a{color:inherit;text-decoration:none}.skeleton{background:linear-gradient(90deg,var(--card) 25%, var(--border) 50%, var(--card) 75%);background-size:200% 100%;animation:shim 1s infinite}@keyframes shim{0%{background-position:200% 0}100%{background-position:-200% 0}}</style></head><body id="body"><div class="header"><div style="display:flex;gap:8px;align-items:center"><a href="/" style="color:var(--text)"><i class="fa fa-arrow-left"></i> Back</a><b style="color:#D4AF37">PROVE AM</b></div><div style="display:flex;gap:12px;align-items:center"><div style="position:relative" onclick="openNotifs()"><i class="fa fa-bell" style="font-size:20px"></i><span id="notifCount" style="position:absolute;top:-8px;right:-8px;background:red;color:#fff;font-size:10px;padding:2px 5px;border-radius:10px;display:none">0</span></div><button onclick="toggleTheme()" style="background:none;border:none;color:var(--text)"><i class="fa fa-moon"></i></button></div></div><div class="top-tabs"><a href="/stories-page">Stories</a><a href="/">Post</a><a href="/chats" class="active">Chat 💬</a></div><div id="list"><div class="chatRow skeleton" style="height:60px"></div><div class="chatRow skeleton" style="height:60px;margin-top:4px"></div></div>""" + NOTIF_HTML + """<script>function toggleTheme(){document.body.classList.toggle('light');localStorage.setItem('theme',document.body.classList.contains('light')?'light':'dark');}if(localStorage.getItem('theme')=='light'){document.body.classList.add('light');}async function load(){try{let r=await fetch('/chats/list');let data=await r.json();document.getElementById('list').innerHTML=data.map(c=>`<a href="/chat/${c.username}"><div class="chatRow"><img src="${c.avatar}" style="width:52px;height:52px;border-radius:50%;object-fit:cover" loading="lazy"><div><b>${c.username}</b> ${c.streak>0?`<span style="color:orange"> 🔥${c.streak}</span>`:''}<div style="color:var(--sub);font-size:13px">${c.is_me?`<i class='fa fa-check-double' style='color:${c.viewed?'#53BDEB':'#8696A0'}}'></i>`:''} ${c.last_msg}</div></div></div></a>`).join('');}catch{}}load();setInterval(load,1500);</script></body></html>"""

CHAT_HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css"><style>:root{--bg:#0B141A;--card:#202C33;--me:#005C4B;--text:#fff}body.light{--bg:#EFE7DE;--card:#fff;--me:#D9FDD3;--text:#000}*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:var(--bg);color:var(--text);display:flex;flex-direction:column;height:100vh;overflow:hidden}.header{background:var(--card);padding:10px 12px;display:flex;align-items:center;gap:10px}.header img{width:36px;height:36px;border-radius:50%;object-fit:cover}#msgs{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:6px}.msg{padding:7px 9px 4px;border-radius:8px;max-width:78%;word-break:break-word;font-size:14.5px;animation:pop.15s ease-out}@keyframes pop{0%{transform:scale(.9);opacity:0}100%{transform:scale(1);opacity:1}}.me{background:var(--me);align-self:flex-end;border-radius:12px 0 12px 12px}.other{background:var(--card);align-self:flex-start;border-radius:0 12px 12px 12px}.time{font-size:10px;color:#ffffff99;display:block;text-align:right;margin-top:4px}.replyBar{background:#182229;border-left:4px solid #00A884;padding:6px 8px;border-radius:6px;margin-bottom:6px;font-size:12px;color:#00A884}.bar{padding:8px;display:flex;gap:8px;align-items:center;background:var(--card)}.bar input{flex:1;background:var(--bg);border:none;border-radius:24px;padding:12px 16px;color:var(--text);outline:none;font-size:16px!important}.iconBtn{width:44px;height:44px;border-radius:50%;display:flex;align-items:center;justify-content:center;border:none;color:#fff;font-size:18px}.mic{background:#00A884}.send{background:#00A884}.modal{position:fixed;inset:0;background:#000000EE;z-index:99;display:none;align-items:center;justify-content:center}#recDot{display:none;color:red;font-size:12px;animation:blink 1s infinite}@keyframes blink{50%{opacity:0}}</style></head><body id="body"><div class="header"><a href="/chats" style="color:var(--text)"><i class="fa fa-arrow-left"></i> Back</a><img id="hAvatar" src="https://i.pravatar.cc/100?u={{other}}"><div style="flex:1"><b>{{other}}</b> <span id="streakShow" style="color:orange;font-size:12px"></span><br><small><span id="recDot">● REC </span>online • fast</small></div><button onclick="toggleTheme()" style="background:none;border:none;color:var(--text);margin-right:10px"><i class="fa fa-moon"></i></button></div><div id="msgs"></div><div id="replyPreview" style="display:none;background:var(--card);padding:8px 12px;border-left:4px solid #00A884"><small id="replyText"></small><i class="fa fa-times" style="float:right" onclick="cancelReply()"></i></div><div class="bar"><input id="txt" placeholder="Message 😊" autocomplete="off"><button class="iconBtn mic" id="micBtn" onclick="toggleRec()"><i class="fa fa-microphone" id="micIcon"></i></button><button class="iconBtn send" onclick="sendText()"><i class="fa fa-paper-plane"></i></button><input type="file" id="f" style="display:none" accept="image/*,video/*,audio/*" multiple><button style="background:none;border:none;color:var(--text);font-size:22px" onclick="document.getElementById('f').click()"><i class="fa fa-paperclip"></i></button></div><div class="modal" id="viewer" onclick="this.style.display='none'"><img id="viewImg"><video id="viewVid" controls playsinline></video></div><script>
let other="{{other}}";let me="{{me}}";let replyTo=null;let rec=null;let chunks=[];let isRec=false;let lowData=localStorage.getItem('lowData')!=='off';let lastCount=0;
function toggleTheme(){document.body.classList.toggle('light');localStorage.setItem('theme',document.body.classList.contains('light')?'light':'dark');}
if(localStorage.getItem('theme')=='light'){document.body.classList.add('light');}
async function compressImage(file){return new Promise(res=>{let img=new Image();let url=URL.createObjectURL(file);img.onload=()=>{let max=600;let w=img.width,h=img.height;if(w>h&&w>max){h=h*max/w;w=max;}else if(h>max){w=w*max/h;h=max;}let c=document.createElement('canvas');c.width=w;c.height=h;c.getContext('2d').drawImage(img,0,0,w,h);res(c.toDataURL('image/jpeg',0.4));URL.revokeObjectURL(url);};img.src=url;});}
function openView(src,type){let m=document.getElementById('viewer');let im=document.getElementById('viewImg');let vd=document.getElementById('viewVid');if(type=='video'){im.style.display='none';vd.style.display='block';vd.src=src;vd.play();}else{vd.style.display='none';im.style.display='block';im.src=src;}m.style.display='flex';}
function setReply(t){replyTo=t;document.getElementById('replyText').innerText=t;document.getElementById('replyPreview').style.display='block';}
function cancelReply(){replyTo=null;document.getElementById('replyPreview').style.display='none';}
async function load(silent=false){
 try{
  let r=await fetch('/chat/'+other+'/messages');let msgs=await r.json();
  let avR=await fetch('/avatars');let avs=await avR.json();if(avs[other])document.getElementById('hAvatar').src=avs[other];
  let r2=await fetch('/streak/'+other); let sd=await r2.json();
  document.getElementById('streakShow').innerText= sd.count>0? `🔥 ${sd.count}` : '';
  if(silent && msgs.length===lastCount) return;
  lastCount=msgs.length;
  let el=document.getElementById('msgs');let near=(el.scrollHeight-el.scrollTop-el.clientHeight)<250;
  el.innerHTML=msgs.map(m=>{
   let media='';if(m.media){
    if(m.media_type=='image') media=`<img src="${m.media}" style="width:100%;border-radius:8px;max-width:260px" onclick="openView('${m.media}','image')" loading="lazy"><br>`;
    else if(m.media_type=='video') media=`<video src="${m.media}" style="width:100%;max-width:260px;border-radius:8px" controls playsinline preload="metadata"></video>`;
    else if(m.media_type=='audio') media=`<audio controls playsinline src="${m.media}" style="width:200px"></audio>`;
    else media=`<img src="${m.media}" style="width:100%;border-radius:8px">`;
   }
   let rep=m.reply_to?`<div class="replyBar">${m.reply_to}</div>`:'';
   let tick=m.sender==me?(m.viewed?`<i class="fa fa-check-double" style="color:#53BDEB"></i>`:`<i class="fa fa-check-double" style="color:#8696A0"></i>`):'';
   return `<div class="msg ${m.sender==me?'me':'other'}" data-id="${m.id}" data-text="${(m.text||'').replace(/"/g,'')}">${rep}${media}<div>${m.text||''}</div><span class="time">${m.created_at} ${tick}</span></div>`;
  }).join('');
  if(!silent||near)el.scrollTop=el.scrollHeight;
 }catch{}
}
async function sendText(){
 let t=document.getElementById('txt').value;if(!t.trim())return;
 let el=document.getElementById('msgs');
 el.innerHTML+=`<div class="msg me"><div>${t}</div><span class="time">now ⏳</span></div>`;
 el.scrollTop=el.scrollHeight;
 document.getElementById('txt').value='';
 cancelReply();
 await fetch('/chat/'+other+'/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t,reply_to:replyTo})});
 load();
}
document.getElementById('f').addEventListener('change', async e=>{
 let files=[...e.target.files];
 for(let f of files){
  let localUrl=URL.createObjectURL(f);
  let el=document.getElementById('msgs');
  let preview = f.type.startsWith('video')? `<video src="${localUrl}" style="width:200px;border-radius:8px" controls></video>` : f.type.startsWith('audio')? `<audio controls src="${localUrl}"></audio>` : `<img src="${localUrl}" style="width:200px;border-radius:8px">`;
  el.innerHTML+=`<div class="msg me">${preview}<br>Uploading...</div>`;
  el.scrollTop=el.scrollHeight;
 }
 for(let f of files){
  if(f.type.startsWith('video')&&f.size>25*1024*1024){alert('Video >25MB');continue;}
  let r= f.type.startsWith('image')? await compressImage(f) : await new Promise(res=>{let fr=new FileReader();fr.onload=ev=>res(ev.target.result);fr.readAsDataURL(f);});
  let mt=f.type.startsWith('video')?'video':f.type.startsWith('audio')?'audio':'image';
  await fetch('/chat/'+other+'/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media:r,media_type:mt,reply_to:replyTo})});
 }
 cancelReply();load();
});
async function toggleRec(){if(isRec){rec.stop();return;}try{let stream=await navigator.mediaDevices.getUserMedia({audio:true});let mime=MediaRecorder.isTypeSupported('audio/mp4')?'audio/mp4':'audio/webm';rec=new MediaRecorder(stream,{mimeType:mime});chunks=[];rec.ondataavailable=e=>chunks.push(e.data);rec.onstop=async()=>{let blob=new Blob(chunks,{type:mime});let fr=new FileReader();fr.onload=ev=>{let el=document.getElementById('msgs');el.innerHTML+=`<div class="msg me"><audio controls src="${ev.target.result}"></audio><br>Uploading voice...</div>`;el.scrollTop=el.scrollHeight;fetch('/chat/'+other+'/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media:ev.target.result,media_type:'audio'})}).then(()=>load());};fr.readAsDataURL(blob);stream.getTracks().forEach(t=>t.stop());isRec=false;document.getElementById('micIcon').className='fa fa-microphone';document.getElementById('recDot').style.display='none';};rec.start();isRec=true;document.getElementById('micIcon').className='fa fa-stop';document.getElementById('recDot').style.display='inline';setTimeout(()=>{if(isRec)rec.stop();},20000);}catch(e){alert('Allow mic');}}
document.getElementById('txt').addEventListener('keydown',e=>{if(e.key==='Enter')sendText();});
load(false);setInterval(()=>load(true),1000);
</script></body></html>"""

PROFILE_HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css"><style>:root{--bg:#000;--card:#111;--text:#fff;--border:#222}body.light{--bg:#f5f5f5;--card:#fff;--text:#000;--border:#ddd}*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:var(--bg);color:var(--text);text-align:center;padding:20px}</style></head><body id="body"><a href="/" style="color:var(--text);position:absolute;left:14px;top:14px"><i class="fa fa-arrow-left"></i> Back</a><h2 style="margin-top:40px">Profile</h2><div style="margin:20px auto;width:120px;height:120px;border-radius:50%;overflow:hidden;border:3px solid #D4AF37"><img id="avatar" src="" style="width:100%;height:100%;object-fit:cover"><input type="file" id="avatarInput" accept="image/*" style="display:none"></div><h1 id="uname" style="color:#D4AF37"></h1><p id="avStatus" style="color:#888;font-size:12px"></p><button onclick="document.getElementById('avatarInput').click()" style="margin-top:16px;background:#D4AF37;color:#000;border:none;border-radius:12px;padding:12px 20px;font-weight:800"><i class="fa fa-camera"></i> Change Profile Pic</button><div style="margin-top:24px"><a href="/logout" style="color:#ff4444">Logout</a></div><script>
if(localStorage.getItem('theme')=='light')document.body.classList.add('light');
async function load(){let r=await fetch('/me');let d=await r.json();document.getElementById('uname').innerText='@'+d.username;let avR=await fetch('/avatars');let avs=await avR.json();document.getElementById('avatar').src=avs[d.username]||`https://i.pravatar.cc/200?u=${d.username}`;}
document.getElementById('avatarInput').addEventListener('change', async e=>{
 let f=e.target.files[0]; if(!f)return; document.getElementById('avStatus').innerText='Compressing...';
 let dataUrl=await new Promise(res=>{let img=new Image();let url=URL.createObjectURL(f);img.onload=()=>{let c=document.createElement('canvas');let max=400;c.width=max;c.height=max;let ctx=c.getContext('2d');ctx.drawImage(img,0,0,max,max);res(c.toDataURL('image/jpeg',0.5));URL.revokeObjectURL(url);};img.src=url;});
 document.getElementById('avStatus').innerText='Uploading...';document.getElementById('avatar').src=dataUrl;
 let r=await fetch('/upload_avatar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media:dataUrl})});
 let d=await r.json(); if(d.ok){document.getElementById('avStatus').innerText='Saved! ✅';} else document.getElementById('avStatus').innerText='Failed';
});
load();
</script></body></html>"""

@app.route('/login', methods=['GET','POST'])
def login_route():
    if request.method=='GET': return render_template_string(LOGIN_HTML)
    data=request.json; u=data.get('username','').strip()[:20]; p=data.get('password','')
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT password FROM auth WHERE username=%s" if USE_POSTGRES else "SELECT password FROM auth WHERE username=?", (u,))
    row=c.fetchone(); conn.close()
    if not row or not check_password_hash(row[0], p): return jsonify({"ok":False,"error":"Wrong"})
    session['username']=u; return jsonify({"ok":True})

@app.route('/signup', methods=['POST'])
def signup():
    data=request.json; u=data.get('username','').strip()[:20]; p=data.get('password','')
    if len(u)<3 or len(p)<3: return jsonify({"ok":False,"error":"Min 3"})
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT 1 FROM auth WHERE username=%s" if USE_POSTGRES else "SELECT 1 FROM auth WHERE username=?", (u,))
    if c.fetchone(): conn.close(); return jsonify({"ok":False,"error":"Taken"})
    c.execute("INSERT INTO auth (username,password,created_at) VALUES (%s,%s,%s)" if USE_POSTGRES else "INSERT INTO auth (username,password,created_at) VALUES (?,?,?)", (u, generate_password_hash(p), datetime.now().isoformat()))
    conn.commit(); conn.close(); session['username']=u; return jsonify({"ok":True})

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')
@app.route('/me')
def me(): return jsonify({"username": session.get('username')})
@app.route('/avatars')
def avatars():
    global AVATAR_CACHE, AVATAR_CACHE_TIME
    now = datetime.now()
    if AVATAR_CACHE and AVATAR_CACHE_TIME and (now - AVATAR_CACHE_TIME).seconds < 60:
        return jsonify(AVATAR_CACHE)
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT username,avatar FROM auth WHERE avatar IS NOT NULL")
    rows=c.fetchall(); conn.close()
    data = {r[0]: r[1] for r in rows if r[1]}
    AVATAR_CACHE = data
    AVATAR_CACHE_TIME = now
    return jsonify(data)

@app.route('/upload_avatar', methods=['POST'])
def upload_avatar():
    if 'username' not in session: return jsonify({"ok":False})
    global AVATAR_CACHE
    data=request.json
    media_url = save_media(data.get('media'), "image")
    conn=get_conn(); c=conn.cursor()
    c.execute("UPDATE auth SET avatar=%s WHERE username=%s" if USE_POSTGRES else "UPDATE auth SET avatar=? WHERE username=?", (media_url, session['username']))
    conn.commit(); conn.close()
    AVATAR_CACHE[session['username']] = media_url
    return jsonify({"ok":True, "avatar": media_url})

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
def sp():
    if 'username' not in session: return redirect('/login')
    return render_template_string(STORIES_HTML)
@app.route('/profile')
def profile_page():
    if 'username' not in session: return redirect('/login')
    return render_template_string(PROFILE_HTML)

@app.route('/notifs')
def get_notifs():
    if 'username' not in session: return jsonify([])
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT from_user,type,text,created_at,is_read FROM notifs WHERE to_user=%s ORDER BY id DESC LIMIT 20" if USE_POSTGRES else "SELECT from_user,type,text,created_at,is_read FROM notifs WHERE to_user=? ORDER BY id DESC LIMIT 20", (session['username'],))
    rows=c.fetchall(); conn.close()
    return jsonify([{"from_user":r[0],"type":r[1],"text":r[2],"created_at":r[3],"is_read":r[4]} for r in rows])
@app.route('/notifs/count')
def notif_count():
    if 'username' not in session: return jsonify({"count":0})
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT COUNT(*) FROM notifs WHERE to_user=%s AND is_read=0" if USE_POSTGRES else "SELECT COUNT(*) FROM notifs WHERE to_user=? AND is_read=0", (session['username'],))
    cnt=c.fetchone()[0]; conn.close()
    return jsonify({"count":cnt})
@app.route('/notifs/read', methods=['POST'])
def notif_read():
    if 'username' not in session: return jsonify({"ok":False})
    conn=get_conn(); c=conn.cursor()
    c.execute("UPDATE notifs SET is_read=1 WHERE to_user=%s" if USE_POSTGRES else "UPDATE notifs SET is_read=1 WHERE to_user=?", (session['username'],))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/upload', methods=['POST'])
def upload():
    if 'username' not in session: return jsonify({"ok":False})
    data=request.json; conn=get_conn(); c=conn.cursor(); now=datetime.now(); exp=now+timedelta(hours=72)
    media_url = save_media(data.get('media'), data.get('media_type','image'))
    c.execute("INSERT INTO posts (username,media,media_type,created_at,expires_at,likes) VALUES (%s,%s,%s,%s,%s,0)" if USE_POSTGRES else "INSERT INTO posts (username,media,media_type,created_at,expires_at,likes) VALUES (?,?,?,?,?,0)", (session['username'],media_url,data.get('media_type','image'),now.isoformat(),exp.isoformat()))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/story/upload', methods=['POST'])
def story_upload():
    if 'username' not in session: return jsonify({"ok":False})
    data=request.json; now=datetime.now(); exp=now+timedelta(hours=24)
    conn=get_conn(); c=conn.cursor()
    media_url = save_media(data.get('media'), data.get('media_type','image'))
    c.execute("INSERT INTO stories (username,media,media_type,created_at,expires_at,views,viewers) VALUES (%s,%s,%s,%s,%s,0,'')" if USE_POSTGRES else "INSERT INTO stories (username,media,media_type,created_at,expires_at,views,viewers) VALUES (?,?,?,?,?,0,'')", (session['username'],media_url,data.get('media_type','image'),now.isoformat(),exp.isoformat()))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/feed')
def feed():
    if 'username' not in session: return jsonify([])
    me=session['username']
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT p.id,p.username,p.media,p.media_type,p.likes,p.created_at, CASE WHEN l.username IS NOT NULL THEN 1 ELSE 0 END as liked FROM posts p LEFT JOIN likes l ON l.post_id=p.id AND l.username=%s ORDER BY p.id DESC LIMIT 30" if USE_POSTGRES else "SELECT p.id,p.username,p.media,p.media_type,p.likes,p.created_at, CASE WHEN l.username IS NOT NULL THEN 1 ELSE 0 END as liked FROM posts p LEFT JOIN likes l ON l.post_id=p.id AND l.username=? ORDER BY p.id DESC LIMIT 30", (me,))
    rows=c.fetchall(); conn.close()
    return jsonify([{"id":r[0],"username":r[1],"media":r[2],"media_type":r[3],"likes":r[4],"created_at":r[5][:16] if r[5] else "", "liked": bool(r[6])} for r in rows])

@app.route('/stories')
def stories():
    conn=get_conn(); c=conn.cursor(); now=datetime.now().isoformat()
    c.execute("DELETE FROM stories WHERE expires_at<%s" if USE_POSTGRES else "DELETE FROM stories WHERE expires_at<?", (now,))
    c.execute("SELECT id,username,media,media_type,views,viewers FROM stories ORDER BY id DESC LIMIT 100")
    rows=c.fetchall(); conn.commit(); conn.close()
    return jsonify([{"id":r[0],"username":r[1],"media":r[2],"media_type":r[3],"views":r[4],"viewers":r[5]} for r in rows])

@app.route('/story/view/<int:id>', methods=['POST'])
def view_story(id):
    if 'username' not in session: return jsonify({"ok":False})
    me=session['username']
    try:
        conn=get_conn(); c=conn.cursor()
        c.execute("SELECT viewers,views,username FROM stories WHERE id=%s" if USE_POSTGRES else "SELECT viewers,views,username FROM stories WHERE id=?", (id,))
        row=c.fetchone()
        if row:
            viewers=row[0] or ""; views=row[1] or 0; owner=row[2]
            if me not in viewers and me!=owner:
                new_viewers = viewers+","+me if viewers else me
                c.execute("UPDATE stories SET views=%s,viewers=%s WHERE id=%s" if USE_POSTGRES else "UPDATE stories SET views=?,viewers=? WHERE id=?", (views+1,new_viewers,id))
                conn.commit()
        conn.close()
    except: pass
    return jsonify({"ok":True})

@app.route('/story/reply/<int:id>', methods=['POST'])
def story_reply(id):
    if 'username' not in session: return jsonify({"ok":False})
    txt=request.json.get('text','')[:200]; me=session['username']
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT username FROM stories WHERE id=%s" if USE_POSTGRES else "SELECT username FROM stories WHERE id=?", (id,))
    row=c.fetchone()
    if not row: conn.close(); return jsonify({"ok":False})
    owner=row[0]
    c.execute("INSERT INTO chats (sender,receiver,text,media,media_type,reply_to,created_at,viewed) VALUES (%s,%s,%s,%s,%s,%s,%s,0)" if USE_POSTGRES else "INSERT INTO chats (sender,receiver,text,media,media_type,reply_to,created_at,viewed) VALUES (?,?,?,?,?,?,?,0)", (me,owner,f"Replied to your story: {txt}",None,None,f"Story reply",datetime.now().isoformat()))
    conn.commit(); conn.close()
    add_notif(owner, me, "story_reply", f"replied to your story: {txt[:20]}")
    return jsonify({"ok":True})

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
    else:
        c.execute("INSERT INTO likes (post_id,username) VALUES (%s,%s)" if USE_POSTGRES else "INSERT INTO likes (post_id,username) VALUES (?,?)", (id,session['username']))
        c.execute("UPDATE posts SET likes=likes+1 WHERE id=%s" if USE_POSTGRES else "UPDATE posts SET likes=likes+1 WHERE id=?", (id,))
        if owner: add_notif(owner[0], session['username'], "like", "liked your post", id)
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/reply/<int:id>', methods=['POST'])
def reply(id):
    if 'username' not in session: return jsonify({"ok":False})
    txt=request.json.get('text','')[:300]
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT username FROM posts WHERE id=%s" if USE_POSTGRES else "SELECT username FROM posts WHERE id=?", (id,))
    owner=c.fetchone()
    c.execute("INSERT INTO replies (post_id,username,text,created_at) VALUES (%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO replies (post_id,username,text,created_at) VALUES (?,?,?,?)", (id,session['username'],txt,datetime.now().isoformat()))
    conn.commit(); conn.close()
    if owner: add_notif(owner[0], session['username'], "comment", f"commented: {txt[:20]}", id)
    return jsonify({"ok":True})

@app.route('/replies/<int:id>')
def get_replies(id):
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT username,text FROM replies WHERE post_id=%s ORDER BY id DESC LIMIT 30" if USE_POSTGRES else "SELECT username,text FROM replies WHERE post_id=? ORDER BY id DESC LIMIT 30", (id,))
    rows=c.fetchall(); conn.close()
    return jsonify([{"username":r[0],"text":r[1]} for r in rows])

@app.route('/delete/<int:id>', methods=['POST'])
def delete_post(id):
    if 'username' not in session: return jsonify({"ok":False})
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT username FROM posts WHERE id=%s" if USE_POSTGRES else "SELECT username FROM posts WHERE id=?", (id,))
    row=c.fetchone()
    if not row or row[0]!=session['username']: conn.close(); return jsonify({"ok":False,"error":"Only your post"})
    c.execute("DELETE FROM posts WHERE id=%s" if USE_POSTGRES else "DELETE FROM posts WHERE id=?", (id,))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/chat/delete/<int:id>', methods=['POST'])
def delete_chat(id):
    if 'username' not in session: return jsonify({"ok":False})
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT sender FROM chats WHERE id=%s" if USE_POSTGRES else "SELECT sender FROM chats WHERE id=?", (id,))
    row=c.fetchone()
    if row and row[0]==session['username']:
        c.execute("DELETE FROM chats WHERE id=%s" if USE_POSTGRES else "DELETE FROM chats WHERE id=?", (id,))
        conn.commit()
    conn.close(); return jsonify({"ok":True})

@app.route('/streak/<other>')
def get_streak(other):
    if 'username' not in session: return jsonify({"count":0})
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT count FROM streaks WHERE user1=%s AND user2=%s" if USE_POSTGRES else "SELECT count FROM streaks WHERE user1=? AND user2=?", (session['username'],other))
    row=c.fetchone(); conn.close()
    return jsonify({"count":row[0] if row else 0})

@app.route('/chats/list')
def chats_list():
    if 'username' not in session: return jsonify([])
    conn=get_conn(); c=conn.cursor(); me=session['username']
    c.execute("SELECT DISTINCT CASE WHEN sender=%s THEN receiver ELSE sender END as other_user FROM chats WHERE sender=%s OR receiver=%s UNION SELECT user2 as other_user FROM friends WHERE user1=%s" if USE_POSTGRES else "SELECT DISTINCT CASE WHEN sender=? THEN receiver ELSE sender END as other_user FROM chats WHERE sender=? OR receiver=? UNION SELECT user2 as other_user FROM friends WHERE user1=?", (me,me,me,me))
    others=[r[0] for r in c.fetchall() if r[0]]
    out=[]
    for uname in others[:50]:
        c.execute("SELECT text,created_at,viewed,sender,media_type FROM chats WHERE (sender=%s AND receiver=%s) OR (sender=%s AND receiver=%s) ORDER BY id DESC LIMIT 1" if USE_POSTGRES else "SELECT text,created_at,viewed,sender,media_type FROM chats WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) ORDER BY id DESC LIMIT 1", (me,uname,uname,me))
        last=c.fetchone()
        c.execute("SELECT avatar FROM auth WHERE username=%s" if USE_POSTGRES else "SELECT avatar FROM auth WHERE username=?", (uname,))
        av_row=c.fetchone()
        av = av_row[0] if av_row and av_row[0] else f"https://i.pravatar.cc/100?u={uname}"
        c.execute("SELECT count FROM streaks WHERE user1=%s AND user2=%s" if USE_POSTGRES else "SELECT count FROM streaks WHERE user1=? AND user2=?", (me,uname))
        s=c.fetchone(); streak=s[0] if s else 0
        if last:
            msg = last[0][:28] if last[0] else ("🎤 Voice" if last[4]=='audio' else "📷 Media")
            out.append({"username":uname,"avatar":av,"last_msg":msg,"time":(last[1][11:16] if last[1] else ""),"viewed":bool(last[2]),"is_me":last[3]==me,"streak":streak})
        else:
            out.append({"username":uname,"avatar":av,"last_msg":"Say hi 👋","time":"","viewed":True,"is_me":False,"streak":streak})
    conn.close(); return jsonify(out)

@app.route('/chat/<other>/messages')
def chat_messages(other):
    if 'username' not in session: return jsonify([])
    conn=get_conn(); c=conn.cursor(); me=session['username']
    c.execute("UPDATE chats SET viewed=1 WHERE sender=%s AND receiver=%s" if USE_POSTGRES else "UPDATE chats SET viewed=1 WHERE sender=? AND receiver=?", (other,me))
    c.execute("SELECT id,sender,text,media,media_type,reply_to,created_at,viewed FROM chats WHERE (sender=%s AND receiver=%s) OR (sender=%s AND receiver=%s) ORDER BY id ASC LIMIT 150" if USE_POSTGRES else "SELECT id,sender,text,media,media_type,reply_to,created_at,viewed FROM chats WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) ORDER BY id ASC LIMIT 150", (me,other,other,me))
    rows=c.fetchall(); conn.commit(); conn.close()
    return jsonify([{"id":r[0],"sender":r[1],"text":r[2],"media":r[3],"media_type":r[4],"reply_to":r[5],"created_at":r[6][11:16] if r[6] else "","viewed":r[7]} for r in rows])

@app.route('/chat/<other>/send', methods=['POST'])
def chat_send(other):
    if 'username' not in session: return jsonify({"ok":False})
    data=request.json; conn=get_conn(); c=conn.cursor(); me=session['username']; today=datetime.now().date().isoformat()
    txt=data.get('text') or ("📷 Media" if data.get('media') else "")
    media_url = save_media(data.get('media'), data.get('media_type','image'))
    c.execute("INSERT INTO chats (sender,receiver,text,media,media_type,reply_to,created_at,viewed) VALUES (%s,%s,%s,%s,%s,%s,%s,0)" if USE_POSTGRES else "INSERT INTO chats (sender,receiver,text,media,media_type,reply_to,created_at,viewed) VALUES (?,?,?,?,?,?,?,0)", (me,other,data.get('text'),media_url,data.get('media_type'),data.get('reply_to'),datetime.now().isoformat()))
    for a,b in [(me,other),(other,me)]:
        c.execute("SELECT 1 FROM friends WHERE user1=%s AND user2=%s" if USE_POSTGRES else "SELECT 1 FROM friends WHERE user1=? AND user2=?", (a,b))
        if not c.fetchone():
            c.execute("INSERT INTO friends (user1,user2,created_at) VALUES (%s,%s,%s)" if USE_POSTGRES else "INSERT INTO friends (user1,user2,created_at) VALUES (?,?,?)", (a,b,datetime.now().isoformat()))
    def update_streak(u1,u2):
        c.execute("SELECT count,last_date FROM streaks WHERE user1=%s AND user2=%s" if USE_POSTGRES else "SELECT count,last_date FROM streaks WHERE user1=? AND user2=?", (u1,u2))
        row=c.fetchone()
        if not row:
            c.execute("INSERT INTO streaks (user1,user2,count,last_date) VALUES (%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO streaks (user1,user2,count,last_date) VALUES (?,?,?,?)", (u1,u2,1,today))
            return 1
        else:
            cnt,last=row[0],row[1]
            new_cnt=cnt
            if last!=today:
                try:
                    last_d=datetime.fromisoformat(last).date()
                    today_d=datetime.fromisoformat(today).date()
                    if (today_d - last_d).days==1: new_cnt=cnt+1
                    elif (today_d - last_d).days>1: new_cnt=1
                except: new_cnt=1
                c.execute("UPDATE streaks SET count=%s,last_date=%s WHERE user1=%s AND user2=%s" if USE_POSTGRES else "UPDATE streaks SET count=?,last_date=? WHERE user1=? AND user2=?", (new_cnt,today,u1,u2))
            return new_cnt
    cnt1=update_streak(me,other); update_streak(other,me)
    conn.commit(); conn.close()
    add_notif(other, me, "message", f"sent: {txt[:25]}")
    return jsonify({"ok":True})

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.environ.get("PORT",5000)), threaded=True)
