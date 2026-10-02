import os
from flask import Flask, request, jsonify, render_template_string, session, redirect
from datetime import datetime, timedelta
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "proveam-v10-final-full"
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
    def q(pg,lite): return pg if USE_POSTGRES else lite
    c.execute(q("CREATE TABLE IF NOT EXISTS auth (username TEXT PRIMARY KEY, password TEXT, created_at TEXT)","CREATE TABLE IF NOT EXISTS auth (username TEXT PRIMARY KEY, password TEXT, created_at TEXT)"))
    c.execute(q("CREATE TABLE IF NOT EXISTS friends (id SERIAL PRIMARY KEY, user1 TEXT, user2 TEXT, created_at TEXT)","CREATE TABLE IF NOT EXISTS friends (id INTEGER PRIMARY KEY AUTOINCREMENT, user1 TEXT, user2 TEXT, created_at TEXT)"))
    c.execute(q("CREATE TABLE IF NOT EXISTS posts (id SERIAL PRIMARY KEY, username TEXT, media TEXT, media_type TEXT, likes INT DEFAULT 0, created_at TEXT, expires_at TEXT)","CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, media TEXT, media_type TEXT, likes INTEGER DEFAULT 0, created_at TEXT, expires_at TEXT)"))
    c.execute(q("CREATE TABLE IF NOT EXISTS likes (id SERIAL PRIMARY KEY, post_id INT, username TEXT)","CREATE TABLE IF NOT EXISTS likes (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, username TEXT)"))
    c.execute(q("CREATE TABLE IF NOT EXISTS replies (id SERIAL PRIMARY KEY, post_id INT, username TEXT, text TEXT, created_at TEXT)","CREATE TABLE IF NOT EXISTS replies (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, username TEXT, text TEXT, created_at TEXT)"))
    c.execute(q("CREATE TABLE IF NOT EXISTS stories (id SERIAL PRIMARY KEY, username TEXT, media TEXT, media_type TEXT, created_at TEXT, expires_at TEXT, views INT DEFAULT 0)","CREATE TABLE IF NOT EXISTS stories (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, media TEXT, media_type TEXT, created_at TEXT, expires_at TEXT, views INTEGER DEFAULT 0)"))
    c.execute(q("CREATE TABLE IF NOT EXISTS chats (id SERIAL PRIMARY KEY, sender TEXT, receiver TEXT, text TEXT, media TEXT, media_type TEXT, reply_to TEXT, created_at TEXT, viewed INT DEFAULT 0)","CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, receiver TEXT, text TEXT, media TEXT, media_type TEXT, reply_to TEXT, created_at TEXT, viewed INTEGER DEFAULT 0)"))
    try: c.execute("ALTER TABLE chats ADD COLUMN viewed INT DEFAULT 0")
    except: pass
    conn.commit(); conn.close()
init_db()

LOGIN_HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>PROVE AM</title><style>*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:#000;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh}.box{background:#111;border:1px solid #222;padding:28px;border-radius:20px;width:90%;max-width:360px;text-align:center}input{width:100%;padding:14px;background:#000;border:1px solid #333;color:#fff;border-radius:12px;margin:7px 0;outline:none}.btn{width:100%;padding:14px;border:none;border-radius:12px;font-weight:800;margin-top:12px;background:#D4AF37;color:#000}</style></head><body><div class="box"><div style="width:86px;height:86px;border-radius:50%;border:2px solid #D4AF37;margin:0 auto;display:flex;align-items:center;justify-content:center;font-weight:900;color:#D4AF37">PROVE</div><h1 style="color:#D4AF37;margin:14px 0">PROVE AM</h1><h3 id="title">Login</h3><input id="u" placeholder="Username"><input id="p" type="password" placeholder="Password"><button class="btn" onclick="doAuth()">Continue</button><p style="margin-top:14px"><a href="#" onclick="toggleMode()" id="tog" style="color:#D4AF37">No account? Sign Up</a></p><p id="msg" style="color:#f66;font-size:12px"></p></div><script>let mode='login';function toggleMode(){mode=mode=='login'?'signup':'login';document.getElementById('title').innerText=mode=='login'?'Login':'Sign Up';document.getElementById('tog').innerText=mode=='login'?'No account? Sign Up':'Have account? Login'}async function doAuth(){let u=document.getElementById('u').value,p=document.getElementById('p').value;let r=await fetch('/'+mode,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})});let d=await r.json();if(d.ok)location.href='/';else document.getElementById('msg').innerText=d.error;}</script></body></html>"""

MAIN_HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css"><style>:root{--bg:#000;--card:#111;--text:#fff;--border:#222;--sub:#888}body.light{--bg:#f5f5f5;--card:#fff;--text:#000;--border:#ddd;--sub:#666}*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:var(--bg);color:var(--text);overflow-x:hidden}::-webkit-scrollbar{display:none}.header{position:sticky;top:0;z-index:20;background:var(--bg);border-bottom:1px solid var(--border)}.top-tabs{display:flex;justify-content:space-around}.top-tabs a{color:var(--sub);text-decoration:none;font-weight:800;font-size:14px;padding:12px 0;border-bottom:2px solid transparent;width:33%;text-align:center}.top-tabs a.active{color:var(--text);border-bottom:2px solid var(--text)}.post{width:100%;background:var(--bg);border-bottom:8px solid var(--card)}.post-top{display:flex;align-items:center;gap:10px;padding:12px 14px}.post-top img{width:32px;height:32px;border-radius:50%}.post-media{width:100%;background:var(--card)}.post-media img,.post-media video{width:100%;max-height:75vh;object-fit:contain;display:block}.post-actions{display:flex;gap:18px;padding:12px 14px;font-size:20px;align-items:center}.right{margin-left:auto}.caption{padding:0 14px 14px;font-size:14px}.modal{position:fixed;inset:0;background:#000000F2;z-index:99;display:none;align-items:center;justify-content:center}.modal img,.modal video{max-width:100%;max-height:90vh}#commentSheet{display:none;position:fixed;inset:0;z-index:100;background:#00000099}#sheet{position:absolute;bottom:0;left:0;right:0;background:var(--card);border-radius:22px 22px 0 0;max-height:85vh;display:flex;flex-direction:column}.fab{position:fixed;bottom:20px;right:20px;background:var(--text);color:var(--bg);width:56px;height:56px;border-radius:50%;border:none;font-size:28px;z-index:25;box-shadow:0 4px 12px rgba(0,0,0,.6)}</style></head><body id="body"><div class="header"><div style="display:flex;justify-content:space-between;align-items:center;padding:12px 14px"><div style="display:flex;align-items:center;gap:8px"><div style="width:34px;height:34px;border-radius:50%;border:2px solid #D4AF37;display:flex;align-items:center;justify-content:center;font-weight:900;color:#D4AF37;font-size:10px">PROVE</div><b style="color:#D4AF37;letter-spacing:2px">PROVE AM</b></div><div style="display:flex;gap:16px;align-items:center"><button onclick="toggleTheme()" style="background:none;border:none;color:var(--text);font-size:20px"><i class="fa fa-moon" id="themeIcon"></i></button><a href="/profile" style="color:var(--text)"><i class="fa-regular fa-user"></i></a></div></div><div class="top-tabs"><a href="/stories-page">Stories</a><a href="/" class="active">Post</a><a href="/chats">Chat 💬</a></div></div><div id="feed" style="padding-top:4px"><div style="padding:40px;text-align:center;color:var(--sub)">Loading...</div></div><input type="file" id="fileIn" accept="image/*,video/*" multiple style="display:none"><button class="fab" onclick="document.getElementById('fileIn').click()">+</button><div class="modal" id="viewer" onclick="this.style.display='none'"><img id="viewImg"><video id="viewVid" controls playsinline></video></div><div id="commentSheet" onclick="if(event.target==this)closeComments()"><div id="sheet"><div style="width:36px;height:4px;background:var(--sub);border-radius:4px;margin:10px auto"></div><div style="text-align:center;font-weight:700;padding-bottom:12px;border-bottom:1px solid var(--border)">Comments 💬 😂 😭 ❤️ 🔥</div><div id="commentList" style="overflow-y:auto;padding:12px;flex:1"></div><div style="display:flex;gap:10px;padding:10px 12px;border-top:1px solid var(--border)"><input id="commentInput" placeholder="Add comment... 😊" style="flex:1;background:var(--bg);border:1px solid var(--border);border-radius:20px;padding:10px 14px;color:var(--text);outline:none"></div></div></div><script>
let allPosts=[]; let activePostId=null;
function toggleTheme(){document.getElementById('body').classList.toggle('light');let ic=document.getElementById('themeIcon');ic.className=document.getElementById('body').classList.contains('light')?'fa fa-sun':'fa fa-moon';localStorage.setItem('theme',document.getElementById('body').classList.contains('light')?'light':'dark');}
if(localStorage.getItem('theme')=='light'){document.getElementById('body').classList.add('light');document.getElementById('themeIcon').className='fa fa-sun';}
function openViewById(id){let p=allPosts.find(x=>x.id==id);if(!p)return;let m=document.getElementById('viewer'),im=document.getElementById('viewImg'),vd=document.getElementById('viewVid');if(p.media_type=='video'){im.style.display='none';vd.style.display='block';vd.src=p.media;}else{vd.style.display='none';im.style.display='block';im.src=p.media;}m.style.display='flex';}
function closeComments(){document.getElementById('commentSheet').style.display='none';}
document.getElementById('fileIn').addEventListener('change', async e=>{let files=[...e.target.files];for(let f of files){let r=await new Promise(res=>{let fr=new FileReader();fr.onload=ev=>res(ev.target.result);fr.readAsDataURL(f);});let type=f.type.startsWith('video')?'video':'image';await fetch('/upload',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media:r,media_type:type})});}loadFeed();});
async function loadFeed(){let r=await fetch('/feed');allPosts=await r.json();if(allPosts.length==0){document.getElementById('feed').innerHTML='<div style="padding:60px;text-align:center;color:var(--sub)">No posts yet — tap + to post multiple pics/videos</div>';return;}document.getElementById('feed').innerHTML=allPosts.map(p=>`<div class="post"><div class="post-top"><img src="https://i.pravatar.cc/100?u=${p.username}"><b>${p.username}</b><small style="color:var(--sub)"> • PROVE AM</small><button class="follow" style="margin-left:auto;border:1px solid var(--border);background:transparent;color:var(--text);border-radius:6px;padding:4px 10px;font-size:12px">Follow</button></div><div class="post-media" onclick="openViewById(${p.id})">${p.media_type=='video'?`<video src="${p.media}" controls playsinline></video>`:`<img src="${p.media}">`}</div><div class="post-actions"><span onclick="likePost(${p.id})"><i class="fa-regular fa-heart"></i> ${p.likes}</span><span onclick="toggleReplies(${p.id})"><i class="fa-regular fa-comment"></i></span><span onclick="sharePost(${p.id})"><i class="fa-regular fa-paper-plane"></i></span><span class="right" onclick="deletePost(${p.id})"><i class="fa-regular fa-trash-can"></i> Delete</span></div><div class="caption"><b>${p.username}</b> PROVE AM ✨<br><span style="color:var(--sub);font-size:12px">${p.created_at}</span></div></div>`).join('');}
async function likePost(id){await fetch('/like/'+id,{method:'POST'});loadFeed();}
async function deletePost(id){if(!confirm('Delete your post?'))return;let r=await fetch('/delete/'+id,{method:'POST'});let d=await r.json();if(!d.ok){alert(d.error);return;}loadFeed();}
async function toggleReplies(id){activePostId=id;document.getElementById('commentSheet').style.display='block';loadComments(id);}
async function loadComments(id){let r=await fetch('/replies/'+id);let reps=await r.json();document.getElementById('commentList').innerHTML=reps.length==0?'<center style="color:var(--sub);padding:20px">No comments</center>':reps.map(c=>`<div style="padding:8px 0"><b>${c.username}</b> ${c.text}</div>`).join('');}
document.getElementById('commentInput').addEventListener('keydown',async e=>{if(e.key==='Enter'){let t=e.target.value;if(!t.trim())return;await fetch('/reply/'+activePostId,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t})});e.target.value='';loadComments(activePostId);loadFeed();}});
async function sharePost(id){let url=location.origin+'/post/'+id;if(navigator.share){try{await navigator.share({url});return;}catch(e){}}await navigator.clipboard.writeText(url);alert('Link copied ✅');}
loadFeed();
</script></body></html>"""

STORIES_HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css"><style>:root{--bg:#000;--card:#111;--text:#fff;--border:#222;--sub:#888}body.light{--bg:#f5f5f5;--card:#fff;--text:#000;--border:#ddd;--sub:#666}*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:var(--bg);color:var(--text);overflow-x:hidden}::-webkit-scrollbar{display:none}.header{position:sticky;top:0;background:var(--bg);z-index:10;border-bottom:1px solid var(--border)}.top-tabs{display:flex;justify-content:space-around;border-bottom:1px solid var(--border)}.top-tabs a{color:var(--sub);text-decoration:none;font-weight:800;font-size:14px;padding:12px 0;border-bottom:2px solid transparent;width:33%;text-align:center}.top-tabs a.active{color:var(--text);border-bottom:2px solid var(--text)}.friends-row{display:flex;gap:14px;overflow-x:auto;padding:12px 16px}.story-circle{flex:0 0 72px;text-align:center;cursor:pointer;position:relative}.ring{width:66px;height:66px;border-radius:50%;border:3px solid #A259FF;background:var(--card);overflow:hidden;position:relative}.ring img{width:100%;height:100%;object-fit:cover}.badge{position:absolute;top:-2px;right:2px;background:#A259FF;color:#fff;font-size:10px;font-weight:800;padding:2px 5px;border-radius:10px}.name{font-size:12px;font-weight:600;margin-top:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.upload-box{margin:16px;background:var(--card);border-radius:16px;padding:14px;border:1px solid var(--border)}.viewer{position:fixed;inset:0;background:#000;z-index:99;display:none;flex-direction:column}.progress{display:flex;gap:4px;padding:8px;position:absolute;top:0;left:0;right:0;z-index:3}.progress span{flex:1;height:3px;background:#ffffff66;border-radius:3px}.progress span.active{background:#fff}</style></head><body id="body"><div class="header"><div style="display:flex;justify-content:space-between;align-items:center;padding:10px 14px"><div style="display:flex;align-items:center;gap:8px"><a href="/" style="color:var(--text)"><i class="fa fa-arrow-left"></i> Back</a><div style="width:34px;height:34px;border-radius:50%;border:2px solid #D4AF37;display:flex;align-items:center;justify-content:center;font-weight:900;color:#D4AF37;font-size:10px">PROVE</div><b style="color:#D4AF37;letter-spacing:2px">PROVE AM</b></div><div style="display:flex;gap:14px;align-items:center"><button onclick="toggleTheme()" style="background:none;border:none;color:var(--text);font-size:18px"><i class="fa fa-moon" id="themeIcon"></i></button><span style="color:#A259FF;font-size:13px" onclick="document.getElementById('fileStory').click()">+ Add</span></div></div><div class="top-tabs"><a href="/stories-page" class="active">Stories</a><a href="/" >Post</a><a href="/chats">Chat 💬</a></div></div><div class="friends-row" id="friendsRow"></div><div class="upload-box"><b>Post Stories ✨ (Multi)</b><br><small style="color:var(--sub)">Select many pics/videos at once — grouped by your name</small><input type="file" id="fileStory" accept="image/*,video/*" multiple style="display:none"><div style="display:flex;gap:8px;margin-top:10px"><button style="flex:1;background:var(--text);color:var(--bg);border:none;border-radius:12px;padding:12px;font-weight:800" onclick="document.getElementById('fileStory').click()">📷 Photo/Video (Multi)</button><button style="flex:1;background:#A259FF;color:#fff;border:none;border-radius:12px;padding:12px;font-weight:800" onclick="postTextStory()">Text</button></div><textarea id="textStory" placeholder="Type story... 😊" style="display:none;width:100%;padding:10px;border-radius:10px;border:1px solid var(--border);margin-top:8px;background:var(--bg);color:var(--text)"></textarea><button id="sendTextBtn" style="display:none;width:100%;background:#A259FF;color:#fff;border:none;border-radius:12px;padding:12px;font-weight:800;margin-top:8px" onclick="sendTextStory()">Post 🚀</button></div><div class="viewer" id="storyViewer"><div class="progress" id="progress"></div><div style="position:absolute;top:14px;left:14px;color:#fff;display:flex;align-items:center;gap:8px;z-index:3"><a onclick="closeViewer()" style="color:#fff;margin-right:6px"><i class="fa fa-arrow-left"></i> Back</a><img id="vAvatar" style="width:32px;height:32px;border-radius:50%"><b id="vName"></b></div><div style="flex:1;display:flex;align-items:center;justify-content:center;width:100%" onclick="nextStory(event)"><img id="vImg" style="max-width:100%;max-height:85vh;display:none"><video id="vVid" controls autoplay playsinline style="max-width:100%;max-height:85vh;display:none"></video><div id="vText" style="color:#fff;font-size:28px;font-weight:800;padding:20px;text-align:center;display:none"></div></div><div style="position:absolute;bottom:20px;left:0;right:0;display:flex;justify-content:space-between;padding:0 20px;color:#fff;font-size:14px"><span onclick="prevStory()">◀ Prev</span><span onclick="nextStory()">Next ▶</span></div></div><script>
let allStories=[]; let grouped={}; let currentList=[]; let currentIndex=0; let timer=null;
function toggleTheme(){document.getElementById('body').classList.toggle('light');let ic=document.getElementById('themeIcon');ic.className=document.getElementById('body').classList.contains('light')?'fa fa-sun':'fa fa-moon';localStorage.setItem('theme',document.getElementById('body').classList.contains('light')?'light':'dark');}
if(localStorage.getItem('theme')=='light'){document.getElementById('body').classList.add('light');}
let textMode=false;function postTextStory(){textMode=!textMode;document.getElementById('textStory').style.display=textMode?'block':'none';document.getElementById('sendTextBtn').style.display=textMode?'block':'none';}
document.getElementById('fileStory').addEventListener('change', async e=>{let files=[...e.target.files];for(let f of files){let r=await new Promise(res=>{let fr=new FileReader();fr.onload=ev=>res(ev.target.result);fr.readAsDataURL(f);});let type=f.type.startsWith('video')?'video':'image';await fetch('/story/upload',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media:r,media_type:type})});}load();});
async function sendTextStory(){let t=document.getElementById('textStory').value;if(!t.trim())return;await fetch('/story/upload',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media:t,media_type:'text'})});document.getElementById('textStory').value='';postTextStory();load();}
async function load(){let r=await fetch('/stories');allStories=await r.json();grouped={};allStories.forEach(s=>{if(!grouped[s.username])grouped[s.username]=[];grouped[s.username].push(s);});let html=Object.keys(grouped).map(u=>{let list=grouped[u];return `<div class="story-circle" onclick="openUserStories('${u}')"><div class="ring"><img src="${list[0].media_type=='text'?'https://i.pravatar.cc/100?u='+u:list[0].media_type=='video'?'https://i.pravatar.cc/100?u='+u:list[0].media}"><span class="badge">${list.length}</span></div><div class="name">${u}</div></div>`}).join('');document.getElementById('friendsRow').innerHTML=html||'<div style="color:var(--sub);padding:10px">No stories yet</div>';}
function openUserStories(u){currentList=grouped[u];currentIndex=0;showStory();}
function showStory(){let s=currentList[currentIndex];if(!s)return;document.getElementById('vName').innerText=s.username;document.getElementById('vAvatar').src='https://i.pravatar.cc/100?u='+s.username;document.getElementById('progress').innerHTML=currentList.map((_,i)=>`<span class="${i==currentIndex?'active':''}"></span>`).join('');let img=document.getElementById('vImg'),vid=document.getElementById('vVid'),txt=document.getElementById('vText');img.style.display='none';vid.style.display='none';txt.style.display='none';if(s.media_type=='video'){vid.style.display='block';vid.src=s.media;vid.play();}else if(s.media_type=='text'){txt.style.display='block';txt.innerText=s.media;}else{img.style.display='block';img.src=s.media;}document.getElementById('storyViewer').style.display='flex';if(timer)clearTimeout(timer);timer=setTimeout(()=>{nextStory();},5000);fetch('/story/view/'+s.id,{method:'POST'});}
function nextStory(e){if(e){let x=e.clientX;let w=window.innerWidth;if(x<w/3){prevStory();return;}}currentIndex++;if(currentIndex>=currentList.length){closeViewer();return;}showStory();}
function prevStory(){currentIndex=Math.max(0,currentIndex-1);showStory();}
function closeViewer(){document.getElementById('storyViewer').style.display='none';if(timer)clearTimeout(timer);}
load();
</script></body></html>"""

CHATS_HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css"><style>:root{--bg:#000;--card:#111;--text:#fff;--border:#222;--sub:#888}body.light{--bg:#f5f5f5;--card:#fff;--text:#000;--border:#ddd;--sub:#666}*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:var(--bg);color:var(--text)}::-webkit-scrollbar{display:none}.header{padding:10px 14px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--border);position:sticky;top:0;background:var(--bg);z-index:10}.top-tabs{display:flex;justify-content:space-around;border-bottom:1px solid var(--border);position:sticky;top:53px;background:var(--bg);z-index:10}.top-tabs a{color:var(--sub);text-decoration:none;font-weight:800;font-size:14px;padding:12px 0;border-bottom:2px solid transparent;width:33%;text-align:center}.top-tabs a.active{color:var(--text);border-bottom:2px solid var(--text)}.chatRow{display:flex;gap:12px;padding:14px 16px;align-items:center;border-bottom:1px solid var(--border)}a{color:inherit;text-decoration:none}</style></head><body id="body"><div class="header"><div style="display:flex;align-items:center;gap:8px"><a href="/" style="color:var(--text)"><i class="fa fa-arrow-left"></i> Back</a><div style="width:34px;height:34px;border-radius:50%;border:2px solid #D4AF37;display:flex;align-items:center;justify-content:center;font-weight:900;color:#D4AF37;font-size:10px">PROVE</div><b style="color:#D4AF37">PROVE AM</b></div><button onclick="toggleTheme()" style="background:none;border:none;color:var(--text);font-size:18px"><i class="fa fa-moon" id="themeIcon"></i></button></div><div class="top-tabs"><a href="/stories-page">Stories</a><a href="/">Post</a><a href="/chats" class="active">Chat 💬</a></div><div id="list">Loading...</div><script>function toggleTheme(){document.getElementById('body').classList.toggle('light');localStorage.setItem('theme',document.getElementById('body').classList.contains('light')?'light':'dark');}if(localStorage.getItem('theme')=='light'){document.getElementById('body').classList.add('light');}async function load(){let r=await fetch('/chats/list');let data=await r.json();if(data.length==0){document.getElementById('list').innerHTML='<div style="text-align:center;padding:60px;color:var(--sub)">No chats yet</div>';return;}document.getElementById('list').innerHTML=data.map(c=>`<a href="/chat/${c.username}"><div class="chatRow"><img src="https://i.pravatar.cc/100?u=${c.username}" style="width:52px;height:52px;border-radius:50%"><div style="flex:1"><div style="display:flex;justify-content:space-between"><b>${c.username}</b><small style="color:var(--sub)">${c.time||''}</small></div><div style="color:var(--sub);font-size:13px;display:flex;gap:6px;align-items:center">${c.is_me?`<i class="fa fa-check-double" style="color:${c.viewed?'#53BDEB':'#8696A0'}"></i>`:''} ${c.last_msg}</div></div></div></a>`).join('');}load();setInterval(load,3000);</script></body></html>"""

CHAT_HTML = """<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css"><style>:root{--bg:#0B141A;--card:#202C33;--me:#005C4B;--text:#fff}body.light{--bg:#EFE7DE;--card:#fff;--me:#D9FDD3;--text:#000}*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:var(--bg);color:var(--text);display:flex;flex-direction:column;height:100vh;overflow:hidden}.header{background:var(--card);padding:10px 12px;display:flex;align-items:center;gap:10px}.header img{width:36px;height:36px;border-radius:50%}#msgs{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:6px}.msg{padding:7px 9px 4px;border-radius:8px;max-width:78%;word-break:break-word;font-size:14.5px;position:relative;touch-action:pan-y}.me{background:var(--me);align-self:flex-end;border-radius:12px 0 12px 12px}.other{background:var(--card);align-self:flex-start;border-radius:0 12px 12px 12px}.time{font-size:10px;color:#ffffff99;display:block;text-align:right;margin-top:4px}.replyBar{background:#182229;border-left:4px solid #00A884;padding:6px 8px;border-radius:6px;margin-bottom:6px;font-size:12px;color:#00A884}.bar{padding:8px;display:flex;gap:8px;align-items:center;background:var(--card)}.bar input{flex:1;background:var(--bg);border:none;border-radius:24px;padding:12px 16px;color:var(--text);outline:none;font-size:16px!important}.iconBtn{width:44px;height:44px;border-radius:50%;display:flex;align-items:center;justify-content:center;border:none;color:#fff;font-size:18px;flex-shrink:0}.mic{background:#00A884}.send{background:#00A884}audio{width:180px;height:32px;display:block;margin-top:4px}.modal{position:fixed;inset:0;background:#000000EE;z-index:99;display:none;align-items:center;justify-content:center}#recDot{display:none;color:red;font-size:12px;animation:blink 1s infinite}@keyframes blink{50%{opacity:0}}</style></head><body id="body"><div class="header"><a href="/chats" style="color:var(--text)"><i class="fa fa-arrow-left"></i> Back</a><img src="https://i.pravatar.cc/100?u={{other}}"><div style="flex:1"><b>{{other}}</b><br><small style="color:var(--text);font-size:11px;opacity:.6"><span id="recDot">● REC </span>online 😊</small></div><button onclick="toggleTheme()" style="background:none;border:none;color:var(--text);margin-right:10px"><i class="fa fa-moon" id="themeIcon"></i></button><i class="fa fa-video"></i><i class="fa fa-phone" style="margin:0 12px"></i></div><div id="msgs"></div><div id="replyPreview" style="display:none;background:var(--card);padding:8px 12px;border-left:4px solid #00A884"><small id="replyText"></small><i class="fa fa-times" style="float:right" onclick="cancelReply()"></i></div><div class="bar"><i class="fa-regular fa-face-smile" style="color:var(--text);opacity:.6;font-size:24px"></i><input id="txt" placeholder="Message 😊" autocomplete="off"><button class="iconBtn mic" id="micBtn" onclick="toggleRec()"><i class="fa fa-microphone" id="micIcon"></i></button><button class="iconBtn send" onclick="sendText()"><i class="fa fa-paper-plane"></i></button><input type="file" id="f" style="display:none" accept="image/*,video/*,audio/*" multiple><button style="background:none;border:none;color:var(--text);font-size:22px;opacity:.6" onclick="document.getElementById('f').click()"><i class="fa fa-paperclip"></i></button></div><div class="modal" id="viewer" onclick="this.style.display='none'"><img id="viewImg"><video id="viewVid" controls playsinline></video></div><script>
let other="{{other}}";let me="{{me}}";let replyTo=null;let rec=null;let chunks=[];let isRec=false;let isNearBottom=true;
function toggleTheme(){document.getElementById('body').classList.toggle('light');localStorage.setItem('theme',document.getElementById('body').classList.contains('light')?'light':'dark');}
if(localStorage.getItem('theme')=='light'){document.getElementById('body').classList.add('light');}
function openView(src,type){let m=document.getElementById('viewer');let im=document.getElementById('viewImg');let vd=document.getElementById('viewVid');if(type=='video'){im.style.display='none';vd.style.display='block';vd.src=src;}else{vd.style.display='none';im.style.display='block';im.src=src;}m.style.display='flex';}
function setReply(t){replyTo=t;document.getElementById('replyText').innerText=t;document.getElementById('replyPreview').style.display='block';}
function cancelReply(){replyTo=null;document.getElementById('replyPreview').style.display='none';}
document.getElementById('msgs').addEventListener('scroll',()=>{let el=document.getElementById('msgs');isNearBottom=(el.scrollHeight-el.scrollTop-el.clientHeight)<120;});
async function load(silent=false){let r=await fetch('/chat/'+other+'/messages');let msgs=await r.json();let el=document.getElementById('msgs');let wasNear=isNearBottom;
 el.innerHTML=msgs.map(m=>{
  let media='';if(m.media){
   if(m.media_type=='video') media=`<video src="${m.media}" style="width:100%;border-radius:8px" controls playsinline></video>`;
   else if(m.media_type=='audio') media=`<div style="display:flex;align-items:center;gap:8px;background:#0A332C;padding:8px;border-radius:20px;margin:4px 0"><i class="fa fa-microphone" style="color:#00A884"></i><audio controls playsinline preload="auto" src="${m.media}" style="width:180px;height:32px"></audio></div>`;
   else media=`<img src="${m.media}" style="width:100%;border-radius:8px" onclick="openView('${m.media}','${m.media_type}')">`;
  }
  let rep=m.reply_to?`<div class="replyBar">${m.reply_to}</div>`:'';
  let tick=m.sender==me?(m.viewed?`<i class="fa fa-check-double" style="color:#53BDEB"></i>`:`<i class="fa fa-check-double" style="color:#8696A0"></i>`):'';
  return `<div class="msg ${m.sender==me?'me':'other'}" data-id="${m.id}" data-text="${(m.text||'').replace(/"/g,'')}"><div class="swipe-hint" style="font-size:10px;opacity:.4">swipe ← to reply, hold to delete</div>${rep}${media}<div>${m.text||''}</div><span class="time">${m.created_at} ${tick}</span></div>`;
 }).join('');
 // attach swipe and long-press
 document.querySelectorAll('.msg').forEach(div=>{
   let sx=0;
   div.addEventListener('touchstart',e=>{sx=e.touches[0].clientX;});
   div.addEventListener('touchend',e=>{let dx=e.changedTouches[0].clientX - sx; if(dx < -60){ setReply(div.dataset.text); } });
   let pressTimer;
   div.addEventListener('touchstart',()=>{pressTimer=setTimeout(()=>{ if(confirm('Delete this message?')){ fetch('/chat/delete/'+div.dataset.id,{method:'POST'}).then(()=>load()); } },700);});
   div.addEventListener('touchend',()=>{clearTimeout(pressTimer);});
   div.addEventListener('mousedown',()=>{pressTimer=setTimeout(()=>{ if(confirm('Delete this message?')){ fetch('/chat/delete/'+div.dataset.id,{method:'POST'}).then(()=>load()); } },700);});
   div.addEventListener('mouseup',()=>{clearTimeout(pressTimer);});
 });
 if(!silent||wasNear){el.scrollTop=el.scrollHeight;}
}
async function sendText(){let t=document.getElementById('txt').value;if(!t.trim())return;await fetch('/chat/'+other+'/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t,reply_to:replyTo})});document.getElementById('txt').value='';cancelReply();isNearBottom=true;load();}
document.getElementById('f').addEventListener('change', async e=>{let files=[...e.target.files];for(let f of files){let r=await new Promise(res=>{let fr=new FileReader();fr.onload=ev=>res(ev.target.result);fr.readAsDataURL(f);});let mt=f.type.startsWith('video')?'video':f.type.startsWith('audio')?'audio':'image';await fetch('/chat/'+other+'/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media:r,media_type:mt,reply_to:replyTo})});}cancelReply();isNearBottom=true;load();});
async function toggleRec(){if(isRec){rec.stop();return;}try{let stream=await navigator.mediaDevices.getUserMedia({audio:true});let mime='';if(MediaRecorder.isTypeSupported('audio/mp4'))mime='audio/mp4';else if(MediaRecorder.isTypeSupported('audio/webm;codecs=opus'))mime='audio/webm;codecs=opus';else mime='audio/webm';rec=new MediaRecorder(stream,{mimeType:mime});chunks=[];rec.ondataavailable=e=>chunks.push(e.data);rec.onstop=async()=>{let blob=new Blob(chunks,{type:mime});let fr=new FileReader();fr.onload=ev=>{fetch('/chat/'+other+'/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media:ev.target.result,media_type:'audio'})}).then(()=>{isNearBottom=true;load();});};fr.readAsDataURL(blob);stream.getTracks().forEach(t=>t.stop());isRec=false;document.getElementById('micIcon').className='fa fa-microphone';document.getElementById('recDot').style.display='none';document.getElementById('micBtn').style.background='#00A884';};rec.start();isRec=true;document.getElementById('micIcon').className='fa fa-stop';document.getElementById('recDot').style.display='inline';document.getElementById('micBtn').style.background='red';setTimeout(()=>{if(isRec)rec.stop();},30000);}catch(e){alert('Allow mic 🎤');}}
load(false);setInterval(()=>load(true),3000);
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
def profile(): return f"<html><body style='background:#000;color:#fff;text-align:center;padding:40px'><h1>@{session.get('username')}</h1><a href='/' style='color:#D4AF37'>Back to Home</a> | <a href='/logout' style='color:#D4AF37'>Logout</a><br><br><button onclick=\"localStorage.clear();alert('Theme reset')\">Reset Theme</button></body></html>"

@app.route('/upload', methods=['POST'])
def upload():
    if 'username' not in session: return jsonify({"ok":False})
    data=request.json; conn=get_conn(); c=conn.cursor(); now=datetime.now(); exp=now+timedelta(hours=24)
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
    c.execute("SELECT id,username,media,media_type,likes,created_at FROM posts ORDER BY id DESC LIMIT 50")
    rows=c.fetchall(); conn.close()
    return jsonify([{"id":r[0],"username":r[1],"media":r[2],"media_type":r[3],"likes":r[4],"created_at":r[5][:16] if r[5] else ""} for r in rows])

@app.route('/stories')
def stories():
    conn=get_conn(); c=conn.cursor(); now=datetime.now().isoformat()
    c.execute("DELETE FROM stories WHERE expires_at<%s" if USE_POSTGRES else "DELETE FROM stories WHERE expires_at<?", (now,))
    c.execute("SELECT id,username,media,media_type FROM stories ORDER BY id DESC LIMIT 100")
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
    conn=get_conn(); c=conn.cursor()
    c.execute("INSERT INTO replies (post_id,username,text,created_at) VALUES (%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO replies (post_id,username,text,created_at) VALUES (?,?,?,?)", (id,session['username'],request.json.get('text','')[:300],datetime.now().isoformat()))
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

@app.route('/notifications')
def notifs():
    if 'username' not in session: return jsonify({"count":0})
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT COUNT(*) FROM chats WHERE receiver=%s AND viewed=0" if USE_POSTGRES else "SELECT COUNT(*) FROM chats WHERE receiver=? AND viewed=0", (session['username'],))
    row=c.fetchone(); conn.close()
    return jsonify({"count":row[0] if row else 0})

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
            msg = last[0][:28] if last[0] else ("🎤 Voice" if last[4]=='audio' else "📷 Media")
            out.append({"username":uname,"last_msg":msg,"time":(last[1][11:16] if last[1] else ""),"viewed":bool(last[2]),"is_me":last[3]==me})
    if not out: out=[{"username":"Samuel","last_msg":"Boi","time":"20:05","viewed":False,"is_me":True}]
    conn.close(); return jsonify(out)

@app.route('/chat/<other>/messages')
def chat_messages(other):
    if 'username' not in session: return jsonify([])
    conn=get_conn(); c=conn.cursor(); me=session['username']
    c.execute("UPDATE chats SET viewed=1 WHERE sender=%s AND receiver=%s" if USE_POSTGRES else "UPDATE chats SET viewed=1 WHERE sender=? AND receiver=?", (other,me))
    c.execute("SELECT id,sender,text,media,media_type,reply_to,created_at,viewed FROM chats WHERE (sender=%s AND receiver=%s) OR (sender=%s AND receiver=%s) ORDER BY id ASC LIMIT 200" if USE_POSTGRES else "SELECT id,sender,text,media,media_type,reply_to,created_at,viewed FROM chats WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) ORDER BY id ASC LIMIT 200", (me,other,other,me))
    rows=c.fetchall(); conn.commit(); conn.close()
    return jsonify([{"id":r[0],"sender":r[1],"text":r[2],"media":r[3],"media_type":r[4],"reply_to":r[5],"created_at":r[6][11:16] if r[6] else "","viewed":r[7]} for r in rows])

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
