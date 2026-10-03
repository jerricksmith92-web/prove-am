import os
from flask import Flask, request, jsonify, session, render_template_string, redirect, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import sqlite3

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET","prove-am-v31-clean")
DB_URL = os.environ.get("DATABASE_URL","")
USE_POSTGRES = DB_URL.startswith("postgres")

def get_conn():
    if USE_POSTGRES:
        try:
            import psycopg2
            return psycopg2.connect(DB_URL)
        except:
            import psycopg
            return psycopg.connect(DB_URL)
    return sqlite3.connect("app.db")

def repair_db():
    conn = get_conn()
    c = conn.cursor()
    print("REPAIR CHECK")
    for tbl in ["stories","posts","messages"]:
        try:
            c.execute(f"SELECT media_url FROM {tbl} LIMIT 1")
        except:
            conn.rollback()
            try:
                c.execute(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS media_url TEXT")
                c.execute(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS text TEXT")
                conn.commit()
                print(f"REPAIRED {tbl}")
            except:
                conn.rollback()
                try:
                    if tbl=="stories":
                        c.execute("DROP TABLE IF EXISTS story_views")
                    if tbl=="posts":
                        c.execute("DROP TABLE IF EXISTS post_likes")
                        c.execute("DROP TABLE IF EXISTS comments")
                    c.execute(f"DROP TABLE IF EXISTS {tbl}")
                    conn.commit()
                    print(f"DROPPED {tbl}")
                except:
                    conn.rollback()
    conn.close()

def init_db():
    repair_db()
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("CREATE TABLE IF NOT EXISTS auth (username TEXT PRIMARY KEY, password TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS profiles (username TEXT PRIMARY KEY, pic_url TEXT, bio TEXT, last_seen TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS posts (id SERIAL PRIMARY KEY, username TEXT, text TEXT, media_url TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS post_likes (post_id INT, username TEXT, PRIMARY KEY(post_id,username))")
        c.execute("CREATE TABLE IF NOT EXISTS comments (id SERIAL PRIMARY KEY, post_id INT, username TEXT, text TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS messages (id SERIAL PRIMARY KEY, sender TEXT, receiver TEXT, text TEXT, media_url TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS stories (id SERIAL PRIMARY KEY, username TEXT, media_url TEXT, text TEXT, created_at TEXT, expires_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS story_views (story_id INT, viewer TEXT, PRIMARY KEY(story_id,viewer))")
    else:
        c.execute("CREATE TABLE IF NOT EXISTS auth (username TEXT PRIMARY KEY, password TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS profiles (username TEXT PRIMARY KEY, pic_url TEXT, bio TEXT, last_seen TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, text TEXT, media_url TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS post_likes (post_id INT, username TEXT, PRIMARY KEY(post_id,username))")
        c.execute("CREATE TABLE IF NOT EXISTS comments (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INT, username TEXT, text TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, receiver TEXT, text TEXT, media_url TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS stories (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, media_url TEXT, text TEXT, created_at TEXT, expires_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS story_views (story_id INT, viewer TEXT, PRIMARY KEY(story_id,viewer))")
    conn.commit()
    conn.close()
    print("DB READY")

init_db()

LOGIN_HTML="""<!DOCTYPE html><html><head><meta name=viewport content="width=device-width,initial-scale=1"><style>body{background:#000;color:#fff;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}.box{background:#111;padding:24px;border-radius:22px;width:330px;text-align:center;border:1px solid #222}input{width:100%;padding:13px;margin:8px 0;border-radius:12px;border:none;background:#222;color:#fff;font-size:16px}button{width:100%;padding:13px;background:#ffcc00;border:none;border-radius:12px;font-weight:bold}</style></head><body><div class=box><h2 style=color:#ffcc00>PROVE AM</h2><input id=u placeholder=Username><input id=p type=password placeholder=Password><button onclick=login()>Login</button><button onclick=signup() style=background:#222;color:#fff;margin-top:8px>Sign Up</button><p id=msg style=color:#ff5555></p></div><script>async function login(){let r=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u.value,password:p.value})});let d=await r.json();if(d.ok)location.href='/';else msg.innerText=d.error}async function signup(){let r=await fetch('/signup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u.value,password:p.value})});let d=await r.json();if(d.ok)location.href='/';else msg.innerText=d.error}</script></body></html>"""

MAIN_HTML="""<!DOCTYPE html><html><head><meta name=viewport content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"><style>
:root{--bg:#f6f6f6;--card:#fff;--text:#000;--sec:#efefef;--border:#e5e5e5}
body.dark{--bg:#000;--card:#111;--text:#fff;--sec:#222;--border:#222}
body{background:var(--bg);color:var(--text);font-family:-apple-system,sans-serif;margin:0}
.top{position:fixed;top:0;left:0;right:0;background:var(--card);padding:8px 12px;display:flex;align-items:center;justify-content:space-between;z-index:100;border-bottom:1px solid var(--border);height:50px;box-sizing:border-box}
.logo{display:flex;align-items:center;gap:8px;font-weight:900;color:#c9a227}
.logo-circle{width:36px;height:36px;border:2px solid #c9a227;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:9px}
.tabs{position:fixed;top:50px;left:0;right:0;background:var(--card);display:flex;z-index:99;border-bottom:1px solid var(--border);height:50px}
.tab{flex:1;display:flex;align-items:center;justify-content:center;font-weight:bold;color:#888;cursor:pointer;border-bottom:3px solid transparent}
.tab.active{color:var(--text);border-color:var(--text)}
.content{margin-top:100px;padding-bottom:150px}
.story-bar{display:flex;gap:14px;overflow-x:auto;padding:12px;background:var(--card);min-height:80px}
.s-item{text-align:center;min-width:72px;cursor:pointer}
.s-ring{width:66px;height:66px;border-radius:50%;background:#000;display:flex;align-items:center;justify-content:center;color:#fff;border:3px solid #ffcc00;overflow:hidden}
.s-ring img{width:100%;height:100%;object-fit:cover}
.story-card{border:1.5px dashed #aaa;border-radius:16px;padding:16px;background:var(--card);margin:12px}
.btn-row{display:flex;gap:10px;margin-top:10px}
.btn-light{flex:1;padding:12px;border-radius:20px;border:1.5px solid var(--text);background:var(--card);color:var(--text);font-weight:bold}
.btn-dark{flex:1;padding:12px;border-radius:20px;background:var(--text);color:var(--bg);font-weight:bold}
.card{background:var(--card);margin:10px;padding:12px;border-radius:16px;border:1px solid var(--border)}
input,textarea{width:100%;background:var(--sec);border:none;border-radius:12px;padding:14px;margin:6px 0;box-sizing:border-box;color:var(--text);font-size:16px}
.send-btn{width:100%;background:#ffcc00;color:#000;padding:16px;border-radius:14px;font-weight:900;margin-top:10px;border:none}
.preview-box{margin-top:12px;border-radius:12px;border:2px solid #ffcc00;display:none;background:#000;overflow:hidden}
.preview-box img,.preview-box video{width:100%;max-height:300px;object-fit:contain}
.viewer{position:fixed;top:0;left:0;right:0;bottom:0;background:#000;z-index:999;display:none;flex-direction:column}
.pic{width:32px;height:32px;border-radius:50%;background:#000;color:#fff;display:flex;align-items:center;justify-content:center;overflow:hidden}
.pic img{width:100%;height:100%;object-fit:cover}
.sticker{width:46px;height:46px;background:#e9e9e9;border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:22px;cursor:pointer;border:1px solid #ddd}
.chat-bar{position:fixed;bottom:0;left:0;right:0;background:var(--card);padding:10px;display:flex;gap:8px;border-top:1px solid var(--border)}
.pill{flex:1;background:#e9e9e9;border:none;border-radius:25px;padding:14px 18px}
.yellow{ background:#ffcc00;border:none;border-radius:25px;padding:0 20px;height:46px;font-weight:800}
.del{font-size:11px;color:#ff4444;background:rgba(255,0,0,0.1);padding:3px 8px;border-radius:10px;margin-left:8px;cursor:pointer}
</style></head><body>
<div class=top><div class=logo><div class=logo-circle>PROVE</div> PROVE AM</div><div style="display:flex;gap:8px;align-items:center"><span onclick="toggleTheme()">🌙</span><div class=pic id=topPic onclick="openProfile()">J</div></div></div>
<div class=tabs><div class=tab active id=tStories onclick="switchTab('stories')">Stories</div><div class=tab id=tPost onclick="switchTab('post')">Post</div><div class=tab id=tChat onclick="switchTab('chat')">Chat</div></div>
<div class=content>
<div id=storiesDiv>
<div style="display:flex;justify-content:space-between;padding:12px;background:var(--card)"><b>Friends ></b><b style=color:#a855f7;cursor:pointer" onclick="document.getElementById('storyFile').click()">+ Add Story</b><input type=file id=storyFile accept="image/*,video/*" style=display:none></div>
<div class=story-bar id=storyBar></div>
<div class=story-card>
<b>Post a Story ✨</b><br><small>Goes to Friends bar top - 24h</small>
<div class=btn-row><button class=btn-light onclick="document.getElementById('storyFile').click()">📷 Photo/Video</button><button class=btn-dark onclick="createTextStory()">A Text Story</button></div>
<div id=storyPreview class=preview-box><img id=storyPreviewImg style="display:none"><video id=storyPreviewVid controls playsinline style="display:none"></video></div>
<textarea id=storyCaption placeholder="Caption under story..." style="display:none;margin-top:10px" rows=2></textarea>
<button id=storySendBtn class=send-btn style="display:none" onclick="uploadStory()">🚀 SEND STORY - TAP HERE</button>
<p id=storyMsg style="text-align:center;color:#c9a227;font-weight:bold;margin-top:8px"></p>
</div>
</div>
<div id=postDiv style=display:none>
<div class=card>
<textarea id=postText placeholder="What's up? Prove Am..."></textarea>
<div style="display:flex;gap:8px;align-items:center;margin:8px 0">
<input type=file id=postFile accept="image/*,video/*" style="display:none">
<div class=sticker onclick="document.getElementById('postFile').click()">📎</div>
<span id=postFileName style="font-size:12px;color:#888">Tap 📎 for pic/video</span>
</div>
<div id=postPreview class=preview-box><img id=postPreviewImg style="display:none"><video id=postPreviewVid controls playsinline style="display:none"></video></div>
<button id=postSendBtn class=send-btn onclick="createPost()">🚀 SEND POST</button>
<p id=postMsg style="text-align:center;color:#c9a227;font-weight:bold"></p>
</div>
<div id=postsList></div>
</div>
<div id=chatDiv style=display:none><input id=searchChat placeholder="Search users..." oninput=filterChat()><div id=chatUsers></div><div id=chatBox style=display:none></div></div>
<div id=profileDiv style=display:none class=card><h3>Profile</h3><div class=pic style="width:90px;height:90px;font-size:32px;margin:10px auto" id=profilePicBig>J</div><p id=profileName style=text-align:center></p><input type=file id=profilePicInput accept="image/*"><button onclick="uploadProfilePic()" style="width:100%;margin-top:10px;background:#ffcc00;padding:12px;border-radius:12px;font-weight:bold;border:none">Update Pic</button><br><br><button onclick="switchTab('stories')">Back</button> <button onclick="logout()" style=background:#ff4444;color:#fff;padding:8px;border-radius:8px;border:none>Logout</button></div>
</div>
<div class=viewer id=viewerModal style="position:fixed;top:0;left:0;right:0;bottom:0;background:#000;z-index:999;display:none;flex-direction:column"><div style="padding:12px;display:flex;justify-content:space-between;color:#fff"><b id=viewerUser></b><div><button onclick="deleteStory()" id=delStoryBtn style="background:#ff4444;color:#fff;padding:6px 10px;border-radius:8px;border:none;margin-right:8px;display:none">🗑️</button><button onclick=closeViewer() style="background:#fff;padding:6px 10px;border-radius:8px;border:none">X</button></div></div><div style="flex:1;display:flex;align-items:center;justify-content:center;flex-direction:column" onclick="nextStory()"><img id=viewerMedia style="max-width:100%;max-height:70vh;display:none"><video id=viewerVideo controls playsinline style="max-width:100%;max-height:70vh;display:none"></video><div id=viewerText style="color:#fff;font-size:28px;font-weight:bold;display:none;text-align:center;padding:20px"></div><div id=viewerCaption style="color:#fff;background:rgba(0,0,0,0.5);padding:10px;border-radius:8px;display:none;margin-top:8px"></div></div></div>
<script>
let curUser='',chatWith='',stories=[],storyIdx=0,allUsers=[],storyTimer=null,profiles={},selectedStoryFile=null,selectedPostFile=null,selectedChatFile=null;
let dark=localStorage.getItem('theme')=='dark'; if(dark)document.body.classList.add('dark');
function toggleTheme(){dark=!dark;localStorage.setItem('theme',dark?'dark':'light');document.body.classList.toggle('dark');}
function switchTab(t){
  document.querySelectorAll('.tab').forEach(e=>e.classList.remove('active'));
  let el=document.getElementById('t'+t.charAt(0).toUpperCase()+t.slice(1));
  if(el)el.classList.add('active');
  document.getElementById('storiesDiv').style.display=t=='stories'?'block':'none';
  document.getElementById('postDiv').style.display=t=='post'?'block':'none';
  document.getElementById('chatDiv').style.display=t=='chat'?'block':'none';
  document.getElementById('profileDiv').style.display='none';
  if(t=='stories')loadStories();
  if(t=='post')loadPosts();
  if(t=='chat')loadChatUsers();
}
async function loadMe(){let r=await fetch('/api/me');let d=await r.json();curUser=d.username;document.getElementById('profileName').innerText=curUser;loadProfiles()}
async function loadProfiles(){let r=await fetch('/api/users');let users=await r.json();allUsers=users;users.forEach(u=>{profiles[u.username]=u.pic_url});let url=profiles[curUser];let el=document.getElementById('topPic');let big=document.getElementById('profilePicBig');if(url){el.innerHTML=`<img src="${url}">`;big.innerHTML=`<img src="${url}">`}else{el.innerText=curUser.charAt(0).toUpperCase();big.innerText=curUser.charAt(0).toUpperCase()}renderChatUsers(users)}
function openProfile(){document.getElementById('storiesDiv').style.display='none';document.getElementById('postDiv').style.display='none';document.getElementById('chatDiv').style.display='none';document.getElementById('profileDiv').style.display='block';}
document.getElementById('storyFile').addEventListener('change', function(e){
  let f=e.target.files[0]; if(!f)return;
  selectedStoryFile=f;
  let preview=document.getElementById('storyPreview');
  let img=document.getElementById('storyPreviewImg');
  let vid=document.getElementById('storyPreviewVid');
  preview.style.display='block';
  document.getElementById('storySendBtn').style.display='block';
  document.getElementById('storyCaption').style.display='block';
  if(f.type.startsWith('video')){
    img.style.display='none'; vid.style.display='block'; vid.src=URL.createObjectURL(f);
  } else {
    vid.style.display='none'; img.style.display='block'; img.src=URL.createObjectURL(f);
  }
  document.getElementById('storyMsg').innerText='Preview OK - tap SEND STORY below';
});
document.getElementById('postFile').addEventListener('change', function(e){
  let f=e.target.files[0]; if(!f)return;
  selectedPostFile=f;
  document.getElementById('postFileName').innerText='📎 '+f.name.slice(0,18);
  let preview=document.getElementById('postPreview');
  let img=document.getElementById('postPreviewImg');
  let vid=document.getElementById('postPreviewVid');
  preview.style.display='block';
  if(f.type.startsWith('video')){
    img.style.display='none'; vid.style.display='block'; vid.src=URL.createObjectURL(f);
  } else {
    vid.style.display='none'; img.style.display='block'; img.src=URL.createObjectURL(f);
  }
});
async function uploadStory(){
  if(!selectedStoryFile){alert('Pick photo first');return}
  let cap=document.getElementById('storyCaption').value||'';
  document.getElementById('storyMsg').innerText='Uploading...';
  let fd=new FormData();
  fd.append('media', selectedStoryFile);
  fd.append('text', cap);
  try{
    let r=await fetch('/api/story',{method:'POST',body:fd});
    let d=await r.json();
    if(d.ok){
      document.getElementById('storyMsg').innerText='✅ Story Posted! Look top Friends bar 👆';
      document.getElementById('storyPreview').style.display='none';
      document.getElementById('storySendBtn').style.display='none';
      document.getElementById('storyCaption').style.display='none';
      document.getElementById('storyCaption').value='';
      selectedStoryFile=null;
      document.getElementById('storyFile').value='';
      setTimeout(loadStories,800);
    } else {
      document.getElementById('storyMsg').innerText='Failed: '+(d.error||'');
    }
  } catch(e){
    document.getElementById('storyMsg').innerText='Error: '+e;
  }
}
async function createTextStory(){let t=prompt('Text story (24h):');if(!t)return;let r=await fetch('/api/story/text',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t})});let d=await r.json();if(d.ok){alert('Posted! Check top bar');loadStories()}else{alert('Fail: '+d.error)}}
async function loadStories(){
  let r=await fetch('/api/stories'); stories=await r.json();
  let h='';
  stories.forEach((s,i)=>{
    let m=s.media_url||''; let isV=m.toLowerCase().includes('.mp4')||m.toLowerCase().includes('.mov')||m.toLowerCase().includes('.webm');
    let inner=''; if(s.text &&!m) inner=`<div class=s-ring>${s.text.slice(0,15)}</div>`; else if(isV) inner=`<div class=s-ring>▶️</div>`; else if(m) inner=`<div class=s-ring><img src="${m}"></div>`; else inner=`<div class=s-ring>${(s.text||'').slice(0,10)}</div>`;
    let cnt=s.view_count?` 👁️${s.view_count}`:''; h+=`<div class=s-item onclick="openViewer(${i})">${inner}<br><small><b>${s.username.slice(0,8)}${cnt}</b></small></div>`;
  });
  document.getElementById('storyBar').innerHTML=h||'<small style=color:#888;padding:12px>No stories - post goes to top Friends bar 👆</small>';
}
function openViewer(i){storyIdx=i;showStory();document.getElementById('viewerModal').style.display='flex';}
function showStory(){
  clearTimeout(storyTimer); let s=stories[storyIdx]; if(!s){closeViewer();return;}
  document.getElementById('viewerUser').innerText=s.username;
  document.getElementById('delStoryBtn').style.display=(s.username==curUser)?'inline-block':'none';
  let img=document.getElementById('viewerMedia'),vid=document.getElementById('viewerVideo'),txt=document.getElementById('viewerText'),cap=document.getElementById('viewerCaption');
  img.style.display=vid.style.display=txt.style.display=cap.style.display='none';
  let m=s.media_url||''; let isV=m.toLowerCase().includes('.mp4')||m.toLowerCase().includes('.mov')||m.toLowerCase().includes('.webm');
  if(s.text &&!m){txt.style.display='block';txt.innerText=s.text;}
  else if(isV){vid.style.display='block';vid.src=m;vid.play().catch(()=>{}); if(s.text){cap.style.display='block';cap.innerText=s.text;}}
  else if(m){img.style.display='block';img.src=m; if(s.text){cap.style.display='block';cap.innerText=s.text;}}
  fetch('/api/story/view',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:s.id})});
  storyTimer=setTimeout(()=>{nextStory()},6000);
}
function nextStory(){if(storyIdx<stories.length-1){storyIdx++;showStory();}else{closeViewer();loadStories();}}
function closeViewer(){clearTimeout(storyTimer);document.getElementById('viewerModal').style.display='none';let v=document.getElementById('viewerVideo');v.pause();}
async function deleteStory(){if(!confirm('Delete story?'))return;let s=stories[storyIdx];await fetch('/api/story/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:s.id})});closeViewer();loadStories();}
async function loadPosts(){let r=await fetch('/api/posts');let posts=await r.json();let h=''; if(posts.length==0)h='<div class=card style=text-align:center;color:#888>No posts</div>'; posts.forEach(p=>{let pic=profiles[p.username];let picHtml=pic?`<img src="${pic}">`:p.username[0]; let m=p.media_url||''; let isV=m.toLowerCase().includes('.mp4')||m.toLowerCase().includes('.mov')||m.toLowerCase().includes('.webm'); let media=''; if(m){if(isV)media=`<video src="${m}" controls playsinline style="width:100%"></video>`; else media=`<img src="${m}" style="width:100%">`;} let del=(p.username==curUser)?`<span class=del onclick="deletePost(${p.id})">🗑️ Delete</span>`:''; h+=`<div class=card style="padding:0;overflow:hidden"><div style="padding:10px;display:flex;align-items:center;gap:10px"><div class=pic>${picHtml}</div><b>${p.username}</b><small style="margin-left:auto">${(p.created_at||'').slice(0,16)}</small>${del}</div>${p.text?`<div style="padding:0 12px 8px">${p.text}</div>`:''}${media}<div style="padding:10px;display:flex;gap:12px"><span onclick="likePost(${p.id})">${p.liked?'❤️':'🤍'} ${p.like_count||0}</span><span onclick="commentPost(${p.id})">💬</span></div></div>`;}); document.getElementById('postsList').innerHTML=h;}
async function createPost(){
  let txt=document.getElementById('postText').value;
  let f=selectedPostFile || document.getElementById('postFile').files[0];
  if(!txt &&!f){document.getElementById('postMsg').innerText='Add text or tap 📎';return;}
  document.getElementById('postMsg').innerText='Posting...';
  let fd=new FormData(); fd.append('text',txt); if(f) fd.append('media',f);
  try{
    let r=await fetch('/api/post',{method:'POST',body:fd});
    let d=await r.json();
    if(d.ok){
      document.getElementById('postMsg').innerText='✅ Posted!';
      document.getElementById('postText').value=''; document.getElementById('postFile').value=''; document.getElementById('postPreview').style.display='none'; document.getElementById('postFileName').innerText='Tap 📎 for pic/video'; selectedPostFile=null;
      setTimeout(loadPosts,600);
    } else {
      document.getElementById('postMsg').innerText='Failed: '+(d.error||'');
    }
  } catch(e){document.getElementById('postMsg').innerText='Error: '+e;}
}
async function deletePost(id){if(!confirm('Delete?'))return; await fetch('/api/post/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:id})}); loadPosts();}
async function likePost(id){await fetch('/api/like',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:id})});loadPosts();}
async function commentPost(id){let t=prompt('Comment:');if(!t)return;await fetch('/api/comment',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:id,text:t})});loadPosts();}
function renderChatUsers(users){let h='';users.forEach(u=>{if(u.username==curUser)return;let pic=u.pic_url?`<img src="${u.pic_url}">`:u.username[0];h+=`<div class=card style="display:flex;align-items:center;gap:10px;cursor:pointer" onclick="openChat('${u.username}')"><div class=pic>${pic}</div><b>${u.username}</b></div>`});document.getElementById('chatUsers').innerHTML=h}
function filterChat(){let q=document.getElementById('searchChat').value.toLowerCase();renderChatUsers(allUsers.filter(u=>u.username.toLowerCase().includes(q)))}
function loadChatUsers(){renderChatUsers(allUsers)}
async function openChat(username){
  chatWith=username;
  document.getElementById('chatUsers').style.display='none';document.getElementById('searchChat').style.display='none';
  let box=document.getElementById('chatBox');box.style.display='block';
  box.innerHTML=`<div style="padding:10px"><button onclick="backChat()" style="background:var(--sec);padding:8px;border-radius:8px;border:1px solid var(--border)">← ${username}</button></div><div id=msgs style="padding:10px;padding-bottom:130px"></div><div class=chat-bar><input id=chatText class=pill placeholder="Write message..." /><input type=file id=chatFileHidden accept="image/*,video/*" style="display:none"><div class=sticker onclick="document.getElementById('chatFileHidden').click()">📎</div><button class=yellow onclick=sendMsg()>Send</button></div>`;
  document.getElementById('chatFileHidden').addEventListener('change',function(e){let f=e.target.files[0]; if(f)selectedChatFile=f;});
  loadMsgs();
}
function backChat(){chatWith='';document.getElementById('chatBox').style.display='none';document.getElementById('chatUsers').style.display='block';document.getElementById('searchChat').style.display='block';}
async function loadMsgs(){if(!chatWith)return;let r=await fetch('/api/messages?with='+chatWith);let msgs=await r.json();let h='';msgs.forEach(m=>{let mu=m.media_url||'';let isV=mu.toLowerCase().includes('.mp4')||mu.toLowerCase().includes('.mov')||mu.toLowerCase().includes('.webm');let media='';if(mu){if(isV)media=`<br><video src="${mu}" controls playsinline style="max-width:220px;border-radius:12px;margin-top:6px"></video>`;else media=`<br><img src="${mu}" style="max-width:220px;border-radius:12px;margin-top:6px">`;}let isMe=m.sender==curUser;let del=isMe?`<br><span class=del onclick="deleteMsg(${m.id})">🗑️ Delete</span>`:'';h+=`<div style="margin:12px 0;text-align:${isMe?'right':'left'}"><span style="background:${isMe?'#000':'#eee'};color:${isMe?'#fff':'#000'};padding:12px 16px;border-radius:22px;display:inline-block;max-width:76%;word-break:break-word">${m.text||''}${media}${del}</span></div>`;});document.getElementById('msgs').innerHTML=h;}
async function sendMsg(){let tEl=document.getElementById('chatText');let t=tEl.value;let f=selectedChatFile;if(!t&&!f)return;let fd=new FormData();fd.append('receiver',chatWith);fd.append('text',t);if(f)fd.append('media',f);tEl.value='';selectedChatFile=null;let hid=document.getElementById('chatFileHidden');if(hid)hid.value='';await fetch('/api/send',{method:'POST',body:fd});setTimeout(loadMsgs,400);}
async function deleteMsg(id){if(!confirm('Delete?'))return;await fetch('/api/message/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:id})});loadMsgs();}
async function uploadProfilePic(){let f=document.getElementById('profilePicInput').files[0];if(!f){alert('Pick pic');return}let fd=new FormData();fd.append('media',f);let r=await fetch('/api/profile/pic',{method:'POST',body:fd});let d=await r.json();if(d.ok){alert('Updated');loadProfiles()}}
async function logout(){await fetch('/logout');location.href='/login'}
loadMe();switchTab('stories');
</script></body></html>"""

@app.route('/')
def home():
    if 'username' not in session:
        return redirect('/login')
    return render_template_string(MAIN_HTML)

@app.route('/login', methods=['GET'])
def login_page():
    return render_template_string(LOGIN_HTML)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/login', methods=['POST'])
def login_api():
    data = request.json
    u = data.get('username','').strip()[:20]
    p = data.get('password','')
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("SELECT password FROM auth WHERE username=%s", (u,))
    else:
        c.execute("SELECT password FROM auth WHERE username=?", (u,))
    row = c.fetchone()
    conn.close()
    if not row or not check_password_hash(row[0], p):
        return jsonify({"ok":False,"error":"Wrong pass"})
    session['username'] = u
    return jsonify({"ok":True})

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    u = data.get('username','').strip()[:20]
    p = data.get('password','')
    if len(u)<3 or len(p)<3:
        return jsonify({"ok":False,"error":"Min 3"})
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("SELECT 1 FROM auth WHERE username=%s", (u,))
    else:
        c.execute("SELECT 1 FROM auth WHERE username=?", (u,))
    if c.fetchone():
        conn.close()
        return jsonify({"ok":False,"error":"Taken"})
    if USE_POSTGRES:
        c.execute("INSERT INTO auth VALUES (%s,%s,%s)", (u, generate_password_hash(p), datetime.now().isoformat()))
        c.execute("INSERT INTO profiles (username,pic_url,last_seen) VALUES (%s,%s,%s) ON CONFLICT (username) DO NOTHING", (u, "", datetime.now().isoformat()))
    else:
        c.execute("INSERT INTO auth VALUES (?,?,?)", (u, generate_password_hash(p), datetime.now().isoformat()))
        c.execute("INSERT OR IGNORE INTO profiles (username,pic_url,last_seen) VALUES (?,?,?)", (u, "", datetime.now().isoformat()))
    conn.commit()
    conn.close()
    session['username'] = u
    return jsonify({"ok":True})

@app.route('/api/me')
def api_me():
    return jsonify({"username":session.get('username','')})

@app.route('/api/users')
def api_users():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT username,pic_url FROM profiles")
    rows = c.fetchall()
    conn.close()
    return jsonify([{"username":r[0],"pic_url":r[1] or ""} for r in rows])

@app.route('/api/posts')
def api_posts():
    me = session.get('username')
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id,username,text,media_url,created_at FROM posts ORDER BY id DESC LIMIT 50")
    rows = c.fetchall()
    out = []
    for r in rows:
        pid = r[0]
        like_count = 0
        liked = False
        try:
            if USE_POSTGRES:
                c.execute("SELECT COUNT(*) FROM post_likes WHERE post_id=%s", (pid,))
            else:
                c.execute("SELECT COUNT(*) FROM post_likes WHERE post_id=?", (pid,))
            like_count = c.fetchone()[0]
            if USE_POSTGRES:
                c.execute("SELECT 1 FROM post_likes WHERE post_id=%s AND username=%s", (pid,me))
            else:
                c.execute("SELECT 1 FROM post_likes WHERE post_id=? AND username=?", (pid,me))
            if c.fetchone():
                liked = True
        except:
            pass
        out.append({"id":pid,"username":r[1],"text":r[2],"media_url":r[3],"created_at":r[4],"like_count":like_count,"liked":liked})
    conn.close()
    return jsonify(out)

@app.route('/api/post', methods=['POST'])
def api_post():
    me = session.get('username')
    if not me:
        return jsonify({"ok":False,"error":"not login"}), 401
    txt = request.form.get('text','')[:500]
    f = request.files.get('media')
    url = ''
    if f and f.filename:
        import uuid
        ext = f.filename.rsplit('.',1)[-1].lower() if '.' in f.filename else 'jpg'
        name = str(uuid.uuid4())[:8]+'.'+ext
        os.makedirs('static/uploads', exist_ok=True)
        path = os.path.join('static/uploads', name)
        f.save(path)
        url = '/'+path
    if not txt and not url:
        return jsonify({"ok":False,"error":"empty"}), 400
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("INSERT INTO posts (username,text,media_url,created_at) VALUES (%s,%s,%s,%s)", (me,txt,url,datetime.now().isoformat()))
    else:
        c.execute("INSERT INTO posts (username,text,media_url,created_at) VALUES (?,?,?,?)", (me,txt,url,datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return jsonify({"ok":True})

@app.route('/api/post/delete', methods=['POST'])
def api_post_delete():
    me = session.get('username')
    data = request.json
    pid = data.get('id')
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("DELETE FROM posts WHERE id=%s AND username=%s", (pid,me))
    else:
        c.execute("DELETE FROM posts WHERE id=? AND username=?", (pid,me))
    conn.commit()
    conn.close()
    return jsonify({"ok":True})

@app.route('/api/like', methods=['POST'])
def api_like():
    me = session.get('username')
    data = request.json
    pid = data.get('post_id')
    conn = get_conn()
    c = conn.cursor()
    try:
        if USE_POSTGRES:
            c.execute("SELECT 1 FROM post_likes WHERE post_id=%s AND username=%s", (pid,me))
        else:
            c.execute("SELECT 1 FROM post_likes WHERE post_id=? AND username=?", (pid,me))
        if c.fetchone():
            if USE_POSTGRES:
                c.execute("DELETE FROM post_likes WHERE post_id=%s AND username=%s", (pid,me))
            else:
                c.execute("DELETE FROM post_likes WHERE post_id=? AND username=?", (pid,me))
        else:
            if USE_POSTGRES:
                c.execute("INSERT INTO post_likes VALUES (%s,%s)", (pid,me))
            else:
                c.execute("INSERT INTO post_likes VALUES (?,?)", (pid,me))
        conn.commit()
    except:
        pass
    conn.close()
    return jsonify({"ok":True})

@app.route('/api/comment', methods=['POST'])
def api_comment():
    me = session.get('username')
    data = request.json
    pid = data.get('post_id')
    txt = data.get('text','')[:200]
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("INSERT INTO comments (post_id,username,text,created_at) VALUES (%s,%s,%s,%s)", (pid,me,txt,datetime.now().isoformat()))
    else:
        c.execute("INSERT INTO comments (post_id,username,text,created_at) VALUES (?,?,?,?)", (pid,me,txt,datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return jsonify({"ok":True})

@app.route('/api/stories')
def api_stories():
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now().isoformat()
    try:
        if USE_POSTGRES:
            c.execute("SELECT id,username,media_url,text,created_at FROM stories WHERE expires_at>%s ORDER BY id DESC", (now,))
        else:
            c.execute("SELECT id,username,media_url,text,created_at FROM stories WHERE expires_at>? ORDER BY id DESC", (now,))
    except:
        conn.rollback()
        c.execute("SELECT id,username,media_url,text,created_at FROM stories ORDER BY id DESC")
    rows = c.fetchall()
    out = []
    for r in rows:
        cnt = 0
        try:
            if USE_POSTGRES:
                c.execute("SELECT COUNT(*) FROM story_views WHERE story_id=%s", (r[0],))
            else:
                c.execute("SELECT COUNT(*) FROM story_views WHERE story_id=?", (r[0],))
            cnt = c.fetchone()[0]
        except:
            pass
        out.append({"id":r[0],"username":r[1],"media_url":r[2],"text":r[3],"created_at":r[4],"view_count":cnt})
    conn.close()
    return jsonify(out)

@app.route('/api/story', methods=['POST'])
def api_story():
    me = session.get('username')
    f = request.files.get('media')
    txt = request.form.get('text','')[:200]
    if not f or not f.filename:
        return jsonify({"ok":False,"error":"no file"})
    import uuid
    ext = f.filename.rsplit('.',1)[-1].lower() if '.' in f.filename else 'jpg'
    name = str(uuid.uuid4())[:8]+'.'+ext
    os.makedirs('static/uploads', exist_ok=True)
    path = os.path.join('static/uploads', name)
    f.save(path)
    url = '/'+path
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now()
    exp = now+timedelta(hours=24)
    if USE_POSTGRES:
        c.execute("INSERT INTO stories (username,media_url,text,created_at,expires_at) VALUES (%s,%s,%s,%s,%s)", (me,url,txt,now.isoformat(),exp.isoformat()))
    else:
        c.execute("INSERT INTO stories (username,media_url,text,created_at,expires_at) VALUES (?,?,?,?,?)", (me,url,txt,now.isoformat(),exp.isoformat()))
    conn.commit()
    conn.close()
    return jsonify({"ok":True})

@app.route('/api/story/delete', methods=['POST'])
def api_story_delete():
    me = session.get('username')
    data = request.json
    sid = data.get('id')
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("DELETE FROM stories WHERE id=%s AND username=%s", (sid,me))
    else:
        c.execute("DELETE FROM stories WHERE id=? AND username=?", (sid,me))
    conn.commit()
    conn.close()
    return jsonify({"ok":True})

@app.route('/api/story/text', methods=['POST'])
def api_story_text():
    me = session.get('username')
    data = request.json
    txt = data.get('text','')[:100]
    if not txt:
        return jsonify({"ok":False,"error":"empty"})
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now()
    exp = now+timedelta(hours=24)
    if USE_POSTGRES:
        c.execute("INSERT INTO stories (username,media_url,text,created_at,expires_at) VALUES (%s,%s,%s,%s,%s)", (me,"",txt,now.isoformat(),exp.isoformat()))
    else:
        c.execute("INSERT INTO stories (username,media_url,text,created_at,expires_at) VALUES (?,?,?,?,?)", (me,"",txt,now.isoformat(),exp.isoformat()))
    conn.commit()
    conn.close()
    return jsonify({"ok":True})

@app.route('/api/story/view', methods=['POST'])
def api_story_view():
    me = session.get('username')
    data = request.json
    sid = data.get('id')
    conn = get_conn()
    c = conn.cursor()
    try:
        if USE_POSTGRES:
            c.execute("INSERT INTO story_views VALUES (%s,%s) ON CONFLICT DO NOTHING", (sid,me))
        else:
            c.execute("INSERT OR IGNORE INTO story_views VALUES (?,?)", (sid,me))
        conn.commit()
    except:
        pass
    conn.close()
    return jsonify({"ok":True})

@app.route('/api/profile/pic', methods=['POST'])
def api_profile_pic():
    me = session.get('username')
    f = request.files.get('media')
    if not f or not f.filename:
        return jsonify({"ok":False})
    import uuid
    ext = f.filename.rsplit('.',1)[-1].lower() if '.' in f.filename else 'jpg'
    name = 'pic_'+me+'_'+str(uuid.uuid4())[:6]+'.'+ext
    os.makedirs('static/uploads', exist_ok=True)
    path = os.path.join('static/uploads', name)
    f.save(path)
    url = '/'+path
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("UPDATE profiles SET pic_url=%s WHERE username=%s", (url,me))
    else:
        c.execute("UPDATE profiles SET pic_url=? WHERE username=?", (url,me))
    conn.commit()
    conn.close()
    return jsonify({"ok":True,"url":url})

@app.route('/api/messages')
def api_messages():
    me = session.get('username')
    other = request.args.get('with','')
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("SELECT id,sender,text,media_url FROM messages WHERE (sender=%s AND receiver=%s) OR (sender=%s AND receiver=%s) ORDER BY id ASC", (me,other,other,me))
    else:
        c.execute("SELECT id,sender,text,media_url FROM messages WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) ORDER BY id ASC", (me,other,other,me))
    rows = c.fetchall()
    conn.close()
    return jsonify([{"id":r[0],"sender":r[1],"text":r[2],"media_url":r[3]} for r in rows])

@app.route('/api/send', methods=['POST'])
def api_send():
    me = session.get('username')
    other = request.form.get('receiver','')
    txt = request.form.get('text','')[:500]
    f = request.files.get('media')
    url = ''
    if f and f.filename:
        import uuid
        ext = f.filename.rsplit('.',1)[-1].lower() if '.' in f.filename else 'jpg'
        name = str(uuid.uuid4())[:8]+'.'+ext
        os.makedirs('static/uploads', exist_ok=True)
        path = os.path.join('static/uploads', name)
        f.save(path)
        url = '/'+path
    if not txt and not url:
        return jsonify({"ok":False})
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("INSERT INTO messages (sender,receiver,text,media_url,created_at) VALUES (%s,%s,%s,%s,%s)", (me,other,txt,url,datetime.now().isoformat()))
    else:
        c.execute("INSERT INTO messages (sender,receiver,text,media_url,created_at) VALUES (?,?,?,?,?)", (me,other,txt,url,datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return jsonify({"ok":True})

@app.route('/api/message/delete', methods=['POST'])
def api_message_delete():
    me = session.get('username')
    data = request.json
    mid = data.get('id')
    conn = get_conn()
    c = conn.cursor()
    if USE_POSTGRES:
        c.execute("DELETE FROM messages WHERE id=%s AND sender=%s", (mid,me))
    else:
        c.execute("DELETE FROM messages WHERE id=? AND sender=?", (mid,me))
    conn.commit()
    conn.close()
    return jsonify({"ok":True})

@app.route('/static/uploads/<path:filename>')
def uploads(filename):
    return send_from_directory('static/uploads', filename)

if __name__=='__main__':
    port=int(os.environ.get("PORT",5000))
    app.run(host='0.0.0.0',port=port)
