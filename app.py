import os
from flask import Flask, request, jsonify, session, render_template_string, redirect, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import sqlite3, traceback

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET","prove-am-v35-all-in-one")
DB_URL = os.environ.get("DATABASE_URL","")
USE_POSTGRES = DB_URL.startswith("postgres")
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
import cloudinary, cloudinary.uploader
cloudinary.config(cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'), api_key=os.environ.get('CLOUDINARY_API_KEY'), api_secret=os.environ.get('CLOUDINARY_API_SECRET'))
os.makedirs('static/uploads', exist_ok=True)
def get_conn():
    if USE_POSTGRES:
        try:
            import psycopg2
            return psycopg2.connect(DB_URL)
        except:
            import psycopg
            return psycopg.connect(DB_URL)
    return sqlite3.connect("app.db")
def upload_to_cloud(file):
    try:
        r = cloudinary.uploader.upload(file, resource_type="auto")
        return r.get('secure_url','')
    except Exception as e:
        print(f"CLOUD FAIL {e}")
        return ''

def run_alter(sql):
    conn=get_conn(); c=conn.cursor()
    try:
        c.execute(sql); conn.commit(); print(f"ALTER OK: {sql}")
    except Exception as e:
        conn.rollback(); print(f"ALTER FAIL {sql}: {e}")
    conn.close()

def nuclear_repair():
    print("=== NUCLEAR REPAIR V35 ===")
    # Force add missing columns - individually
    cols = [
        ("posts","text","TEXT"), ("posts","media_url","TEXT"), ("posts","username","TEXT"), ("posts","created_at","TEXT"),
        ("stories","text","TEXT"), ("stories","media_url","TEXT"), ("stories","expires_at","TEXT"), ("stories","created_at","TEXT"), ("stories","username","TEXT"),
        ("messages","text","TEXT"), ("messages","media_url","TEXT"), ("messages","receiver","TEXT"), ("messages","sender","TEXT"), ("messages","created_at","TEXT"),
        ("profiles","pic_url","TEXT"),
    ]
    for tbl,col,typ in cols:
        run_alter(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS {col} {typ}" if USE_POSTGRES else f"ALTER TABLE {tbl} ADD COLUMN {col} {typ}")
    print("REPAIR DONE")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, password TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS friend_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, from_user TEXT, to_user TEXT, status TEXT DEFAULT 'pending')")
    c.execute("CREATE TABLE IF NOT EXISTS user_status (username TEXT PRIMARY KEY, online INTEGER, last_seen REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS profiles (username TEXT PRIMARY KEY, pic_url TEXT, bio TEXT, last_seen TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, text TEXT, media_url TEXT, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, receiver TEXT, message TEXT, timestamp REAL, read INTEGER DEFAULT 0, reply_to INTEGER DEFAULT 0, media_url TEXT)")

    # Safe column upgrades - DO NOT use IF NOT EXISTS here
    for sql in [
        "ALTER TABLE messages ADD COLUMN read INTEGER DEFAULT 0",
        "ALTER TABLE messages ADD COLUMN reply_to INTEGER DEFAULT 0",
        "ALTER TABLE messages ADD COLUMN media_url TEXT",
        "ALTER TABLE messages ADD COLUMN receiver TEXT"
    ]:
        try:
            c.execute(sql)
        except:
            pass

    conn.commit()
    conn.close()
    
def init_db():
    nuclear_repair()
    conn=get_conn(); c=conn.cursor()
    if USE_POSTGRES:
        c.execute("CREATE TABLE IF NOT EXISTS auth (username TEXT PRIMARY KEY, password TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS profiles (username TEXT PRIMARY KEY, pic_url TEXT, bio TEXT, last_seen TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS posts (id SERIAL PRIMARY KEY, username TEXT, text TEXT, media_url TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS post_likes (post_id INT, username TEXT, PRIMARY KEY(post_id,username))")
        c.execute("CREATE TABLE IF NOT EXISTS comments (id SERIAL PRIMARY KEY, post_id INT, username TEXT, text TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS messages (id SERIAL PRIMARY KEY, sender TEXT, receiver TEXT, text TEXT, media_url TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS stories (id SERIAL PRIMARY KEY, username TEXT, media_url TEXT, text TEXT, created_at TEXT, expires_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS story_views (story_id INT, viewer TEXT, PRIMARY KEY(story_id,viewer))")
        c.execute("CREATE TABLE IF NOT EXISTS friends (id SERIAL PRIMARY KEY, sender TEXT, receiver TEXT, status TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS notifications (id SERIAL PRIMARY KEY, username TEXT, type TEXT, from_user TEXT, text TEXT, created_at TEXT, is_read INT DEFAULT 0)")
    c.execute("CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, password TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS friend_requests (id SERIAL PRIMARY KEY, from_user TEXT, to_user TEXT, status TEXT DEFAULT 'pending')")
    try:
        c.execute("ALTER TABLE messages ADD COLUMN IF NOT EXISTS media_url TEXT")
    except:
        pass
    try:
        c.execute("ALTER TABLE messages ADD COLUMN IF NOT EXISTS receiver TEXT")
    except:
        pass
    try:
        c.execute("ALTER TABLE messages ADD COLUMN IF NOT EXISTS sender TEXT")
    except:
        pass
    try:
        c.execute("ALTER TABLE messages ADD COLUMN IF NOT EXISTS created_at TEXT")
    except:
        pass
    try:
        c.execute("ALTER TABLE profiles ADD COLUMN IF NOT EXISTS pic_url TEXT")
    except:
        pass

    conn.commit(); conn.close()
    print("DB READY V35 FRIENDS+NOTIF")

init_db()

LOGIN_HTML="""<!DOCTYPE html><html><head><meta name=viewport content="width=device-width,initial-scale=1"><style>body{background:#000;color:#fff;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}.box{background:#111;padding:24px;border-radius:22px;width:330px;text-align:center;border:1px solid #222}input{width:100%;padding:13px;margin:8px 0;border-radius:12px;border:none;background:#222;color:#fff;font-size:16px}button{width:100%;padding:13px;background:#ffcc00;border:none;border-radius:12px;font-weight:bold}</style></head><body><div class=box><h2 style=color:#ffcc00>PROVE AM</h2><input id=u placeholder=Username><input id=p type=password placeholder=Password><button onclick=login()>Login</button><button onclick=signup() style=background:#222;color:#fff;margin-top:8px>Sign Up</button><p id=msg style=color:#ff5555></p></div><script>async function login(){let r=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u.value,password:p.value})});let d=await r.json();if(d.ok)location.href='/';else msg.innerText=d.error}async function signup(){let r=await fetch('/signup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u.value,password:p.value})});let d=await r.json();if(d.ok)location.href='/';else msg.innerText=d.error}</script></body></html>"""

MAIN_HTML="""<!DOCTYPE html><html><head><meta name=viewport content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"><style>
:root{--bg:#f6f6f6;--card:#fff;--text:#000;--sec:#efefef;--border:#e5e5e5}
body.dark{--bg:#000;--card:#111;--text:#fff;--sec:#222;--border:#222}
body{background:var(--bg);color:var(--text);font-family:-apple-system,sans-serif;margin:0}
.top{position:fixed;top:0;left:0;right:0;background:var(--card);padding:8px 10px;display:flex;align-items:center;justify-content:space-between;z-index:100;border-bottom:1px solid var(--border);height:50px;box-sizing:border-box}
.logo{display:flex;align-items:center;gap:6px;font-weight:900;color:#c9a227;font-size:15px}
.logo-circle{width:34px;height:34px;border:2px solid #c9a227;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:8px}
.tabs{position:fixed;top:50px;left:0;right:0;background:var(--card);display:flex;z-index:99;border-bottom:1px solid var(--border);height:50px}
.tab{flex:1;display:flex;align-items:center;justify-content:center;font-weight:bold;color:#888;cursor:pointer;border-bottom:3px solid transparent;font-size:13px}
.tab.active{color:var(--text);border-color:var(--text)}
.content{margin-top:100px;padding-bottom:160px}
.story-bar{display:flex;gap:12px;overflow-x:auto;padding:12px;background:var(--card);min-height:80px}
.s-item{text-align:center;min-width:68px;cursor:pointer}
.s-ring{width:62px;height:62px;border-radius:50%;background:#000;display:flex;align-items:center;justify-content:center;color:#fff;border:3px solid #ffcc00;overflow:hidden;position:relative}
.s-ring img{width:100%;height:100%;object-fit:cover}
.s-count{position:absolute;bottom:-2px;right:-2px;background:#ffcc00;color:#000;font-size:10px;font-weight:900;padding:2px 5px;border-radius:10px;border:2px solid var(--card)}
.story-card{border:1.5px dashed #aaa;border-radius:16px;padding:14px;background:var(--card);margin:10px}
.btn-row{display:flex;gap:8px;margin-top:10px}
.btn-light{flex:1;padding:11px;border-radius:20px;border:1.5px solid var(--text);background:var(--card);color:var(--text);font-weight:bold;font-size:13px}
.btn-dark{flex:1;padding:11px;border-radius:20px;background:var(--text);color:var(--bg);font-weight:bold;font-size:13px}
.card{background:var(--card);margin:8px;padding:12px;border-radius:16px;border:1px solid var(--border)}
input,textarea{width:100%;background:var(--sec);border:none;border-radius:12px;padding:14px;margin:6px 0;box-sizing:border-box;color:var(--text);font-size:16px}
.send-btn{width:100%;background:#ffcc00;color:#000;padding:14px;border-radius:14px;font-weight:900;margin-top:8px;border:none}
.preview-box{margin-top:10px;border-radius:12px;border:2px solid #ffcc00;display:none;background:#000;overflow:hidden}
.preview-box img,.preview-box video{width:100%;max-height:280px;object-fit:contain}
.pic{width:32px;height:32px;border-radius:50%;background:#000;color:#fff;display:flex;align-items:center;justify-content:center;overflow:hidden;flex-shrink:0}
.pic img{width:100%;height:100%;object-fit:cover}
.sticker{width:42px;height:42px;background:#e9e9e9;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:20px;cursor:pointer;border:1px solid #ddd}
.chat-bar{position:fixed;bottom:0;left:0;right:0;background:var(--card);padding:10px;display:flex;gap:8px;border-top:1px solid var(--border);align-items:center;z-index:50}
.pill{flex:1;background:#e9e9e9;border:none;border-radius:25px;padding:13px 16px;outline:none;font-size:15px}
.yellow{background:#ffcc00;border:none;border-radius:25px;padding:0 18px;height:44px;font-weight:800;color:#0040ff}
.del{font-size:11px;color:#ff4444;background:rgba(255,0,0,0.1);padding:3px 8px;border-radius:10px;margin-left:6px;cursor:pointer}
.bar{height:4px;background:#333;display:flex;gap:3px;padding:4px}
.bar div{flex:1;background:rgba(255,255,255,0.3);height:4px;border-radius:2px}
.bar div.active{background:#fff}
.bar div.seen{background:#fff}
.notif-dot{position:absolute;top:-4px;right:-6px;background:#ff4444;color:#fff;font-size:10px;font-weight:900;padding:2px 6px;border-radius:12px;min-width:10px;text-align:center}
.low-on{background:#ffcc00!important;color:#000!important}
.friend-btn{padding:6px 12px;border-radius:20px;border:none;font-weight:700;font-size:12px;cursor:pointer}
.f-add{background:#ffcc00;color:#000}
.f-pending{background:#ddd;color:#666}
.f-friends{background:#00c851;color:#fff}
</style></head><body>
<div class=top>
<div class=logo><div class=logo-circle>PROVE</div> PROVE AM</div>
<div style="display:flex;gap:10px;align-items:center">
<button onclick="toggleLow()" id=lowBtn style="padding:5px 8px;font-size:11px;border:1px solid var(--border);background:var(--sec);color:var(--text);border-radius:8px">📶 Low: OFF</button>
<div style="position:relative;cursor:pointer" onclick="openNotifs()">🔔<span id=notifCount class=notif-dot style="display:none">0</span></div>
<span onclick="toggleTheme()" style="cursor:pointer">🌙</span>
<div class=pic id=topPic onclick="openProfile()">J</div>
</div>
</div>
<div class=tabs>
<div class=tab active id=tStories onclick="switchTab('stories')">Stories</div>
<div class=tab id=tPost onclick="switchTab('post')">Post</div>
<div class=tab id=tChat onclick="switchTab('chat')">Chat</div>
<div class=tab id=tSearch onclick="switchTab('search')">Search</div>
</div>
<div class=content>
<div id=storiesDiv>
<div style="display:flex;justify-content:space-between;padding:12px;background:var(--card)"><b>Friends ></b><small style=color:#888">Private - friends only</small><b style=color:#a855f7;cursor:pointer" onclick="document.getElementById('storyFile').click()">+ Add</b><input type=file id=storyFile accept="image/*,video/*" style=display:none></div>
<div class=story-bar id=storyBar></div>
<div class=story-card>
<b>Post a Story ✨</b><br><small>1 user = 1 circle - Only friends can view - Reply goes to chat</small>
<div class=btn-row><button class=btn-light onclick="document.getElementById('storyFile').click()">📷 Photo/Video</button><button class=btn-dark onclick="createTextStory()">A Text Story</button></div>
<div id=storyPreview class=preview-box><img id=storyPreviewImg style="display:none"><video id=storyPreviewVid controls playsinline style="display:none"></video></div>
<textarea id=storyCaption placeholder="Caption..." style="display:none;margin-top:8px" rows=2></textarea>
<button id=storySendBtn class=send-btn style="display:none" onclick="uploadStory()">🚀 SEND STORY</button>
<p id=storyMsg style="text-align:center;color:#c9a227;font-weight:bold"></p>
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
<button class=send-btn onclick="createPost()">🚀 SEND POST (Public)</button>
<p id=postMsg style="text-align:center;color:#c9a227;font-weight:bold;margin-top:8px"></p>
</div>
<div id=postsList></div>
</div>
<div id=chatDiv style=display:none><input id=searchChat placeholder="Search friends..." oninput=filterChat()><div id=chatUsers></div><div id=chatBox style=display:none></div></div>
<div id=searchDiv style=display:none class=card>
<h3>🔍 Search Users</h3>
<input id=searchUsersInput placeholder="Search username..." oninput="searchUsers()" style="background:var(--sec)">
<div id=searchResults style="margin-top:10px"></div>
<h4 style="margin-top:20px">Friend Requests <span id=reqCount style="background:#ff4444;color:#fff;padding:2px 8px;border-radius:12px;font-size:11px">0</span></h4>
<div id=friendRequests></div>
<h4>My Friends</h4>
<div id=myFriendsList></div>
</div>
<div id=notifDiv style=display:none class=card>
<h3>🔔 Notifications</h3>
<button onclick="switchTab('stories')" style="background:var(--sec);padding:6px 10px;border-radius:8px;border:1px solid var(--border)">Back</button>
<button onclick="clearNotifs()" style="background:#ffcc00;padding:6px 10px;border-radius:8px;border:none;margin-left:8px">Clear All</button>
<div id=notifList style="margin-top:12px"></div>
</div>
<div id=profileDiv style=display:none class=card>
<h3>Profile</h3>
<div class=pic style="width:100px;height:100px;font-size:38px;margin:10px auto;border:3px solid #ffcc00" id=profilePicBig>J</div>
<p id=profileName style=text-align:center;font-weight:bold></p>
<p id=profileMsg style="text-align:center;color:#c9a227;font-size:12px"></p>
<div style="display:flex;gap:8px;align-items:center;margin:10px 0;justify-content:center">
<input type=file id=profilePicInput accept="image/*" style="display:none">
<div class=sticker onclick="document.getElementById('profilePicInput').click()" style="width:56px;height:56px">📎</div>
<span id=profileFileName style="font-size:12px;color:#888">Tap 📎 to pick new pic</span>
</div>
<button onclick="uploadProfilePic()" style="width:100%;margin-top:8px;background:#ffcc00;padding:12px;border-radius:12px;font-weight:900;border:none">Update Pic</button>
<br><br>
<button onclick="switchTab('stories')" style="background:var(--sec);padding:8px 12px;border-radius:12px;border:1px solid var(--border)">Back</button>
<button onclick="logout()" style=background:#ff4444;color:#fff;padding:8px 12px;border-radius:12px;border:none;margin-left:6px>Logout</button>
</div>
</div>
<div class=viewer id=viewerModal style="position:fixed;top:0;left:0;right:0;bottom:0;background:#000;z-index:999;display:none;flex-direction:column">
<div class=bar id=progressBar></div>
<div style="padding:10px;display:flex;justify-content:space-between;color:#fff;align-items:center">
<div><b id=viewerUser></b> <small id=viewerCounter style="margin-left:6px;color:#aaa"></small></div>
<div><button onclick="deleteStory()" id=delStoryBtn style="background:#ff4444;color:#fff;padding:5px 8px;border-radius:8px;border:none;margin-right:6px;display:none">🗑️</button><button onclick=closeViewer() style="background:#fff;padding:5px 10px;border-radius:8px;border:none">X</button></div>
</div>
<div style="flex:1;display:flex;align-items:center;justify-content:center;flex-direction:column;position:relative" onclick="nextStory()">
<img id=viewerMedia style="max-width:100%;max-height:60vh;display:none">
<video id=viewerVideo controls playsinline style="max-width:100%;max-height:60vh;display:none"></video>
<div id=viewerText style="color:#fff;font-size:26px;font-weight:bold;display:none;text-align:center;padding:16px"></div>
<div id=viewerCaption style="color:#fff;background:rgba(0,0,0,0.6);padding:8px;border-radius:8px;display:none;margin-top:6px;text-align:center;max-width:90%"></div>
<div style="position:absolute;bottom:70px;left:0;right:0;display:flex;justify-content:space-between;padding:0 16px">
<button onclick="event.stopPropagation();prevStory()" style="background:rgba(255,255,255,0.2);color:#fff;border:none;border-radius:50%;width:36px;height:36px">‹</button>
<button onclick="event.stopPropagation();nextStory()" style="background:rgba(255,255,255,0.2);color:#fff;border:none;border-radius:50%;width:36px;height:36px">›</button>
</div>
</div>
<div style="background:rgba(0,0,0,0.8);padding:10px;display:flex;gap:8px;align-items:center">
<input id=storyReplyInput placeholder="Reply to story... (goes to chat)" style="flex:1;background:#222;color:#fff;border:none;border-radius:20px;padding:10px 14px">
<button onclick="replyStory()" style="background:#ffcc00;border:none;border-radius:20px;padding:10px 16px;font-weight:800">Send</button>
</div>
</div>
<script>
let curUser='',chatWith='',stories=[],groupedStories={},currentGroup=[],currentGroupIdx=0,storyTimer=null,allUsers=[],profiles={},selectedStoryFile=null,selectedPostFile=null,selectedChatFile=null,selectedProfileFile=null;
let lowData = localStorage.getItem('lowData')=='1';
let dark=localStorage.getItem('theme')=='dark'; if(dark)document.body.classList.add('dark');
updateLowBtn();
function updateLowBtn(){let b=document.getElementById('lowBtn'); if(!b)return; b.innerText=lowData?'📶 Low: ON':'📶 Low: OFF'; if(lowData) b.classList.add('low-on'); else b.classList.remove('low-on');}
function toggleLow(){lowData=!lowData;localStorage.setItem('lowData',lowData?'1':'0'); updateLowBtn(); alert(lowData?'Low Data ON: videos wont autoplay, tap to play':'Low Data OFF: autoplay ON'); loadPosts();}
function toggleTheme(){dark=!dark;localStorage.setItem('theme',dark?'dark':'light');document.body.classList.toggle('dark');}
function switchTab(t){
  document.querySelectorAll('.tab').forEach(e=>e.classList.remove('active'));
  let el=document.getElementById('t'+t.charAt(0).toUpperCase()+t.slice(1)); if(el)el.classList.add('active');
  document.getElementById('storiesDiv').style.display=t=='stories'?'block':'none';
  document.getElementById('postDiv').style.display=t=='post'?'block':'none';
  document.getElementById('chatDiv').style.display=t=='chat'?'block':'none';
  document.getElementById('searchDiv').style.display=t=='search'?'block':'none';
  document.getElementById('profileDiv').style.display='none';
  document.getElementById('notifDiv').style.display='none';
  if(t=='stories')loadStories();
  if(t=='post')loadPosts();
  if(t=='chat')loadChatUsers();
  if(t=='search'){searchUsers(); loadFriendRequests(); loadMyFriends();}
}
function openNotifs(){document.getElementById('storiesDiv').style.display='none';document.getElementById('postDiv').style.display='none';document.getElementById('chatDiv').style.display='none';document.getElementById('searchDiv').style.display='none';document.getElementById('profileDiv').style.display='none';document.getElementById('notifDiv').style.display='block';loadNotifs();}
function openProfile(){document.getElementById('storiesDiv').style.display='none';document.getElementById('postDiv').style.display='none';document.getElementById('chatDiv').style.display='none';document.getElementById('searchDiv').style.display='none';document.getElementById('notifDiv').style.display='none';document.getElementById('profileDiv').style.display='block'; loadProfiles();}
async function loadMe(){let r=await fetch('/api/me');let d=await r.json();curUser=d.username;document.getElementById('profileName').innerText=curUser;loadProfiles();loadNotifCount();setInterval(loadNotifCount,5000);}
async function loadProfiles(){
  let r=await fetch('/api/users');let users=await r.json();allUsers=users;users.forEach(u=>{profiles[u.username]=u.pic_url});
  renderTopPic(); renderChatUsers(users);
  let url=profiles[curUser]; let big=document.getElementById('profilePicBig');
  if(url && big){ let bust=url+'?t='+Date.now(); big.innerHTML=`<img src="${bust}" style="width:100%;height:100%;object-fit:cover">`; }
}
function renderTopPic(){let url=profiles[curUser];let el=document.getElementById('topPic'); if(!el)return; if(url){let bust=url+'?t='+Date.now(); el.innerHTML=`<img src="${bust}" style="width:100%;height:100%;object-fit:cover">`;} else {el.innerText=curUser.charAt(0).toUpperCase();}}
document.getElementById('profilePicInput').addEventListener('change', function(e){let f=e.target.files[0]; if(!f)return; selectedProfileFile=f; document.getElementById('profileFileName').innerText='📎 '+f.name.slice(0,18); let big=document.getElementById('profilePicBig'); big.innerHTML=`<img src="${URL.createObjectURL(f)}" style="width:100%;height:100%;object-fit:cover">`; document.getElementById('profileMsg').innerText='Preview - tap Update';});
document.getElementById('storyFile').addEventListener('change', function(e){let f=e.target.files[0]; if(!f)return; selectedStoryFile=f; let preview=document.getElementById('storyPreview'); let img=document.getElementById('storyPreviewImg'); let vid=document.getElementById('storyPreviewVid'); preview.style.display='block'; document.getElementById('storySendBtn').style.display='block'; document.getElementById('storyCaption').style.display='block'; if(f.type.startsWith('video')){img.style.display='none';vid.style.display='block';vid.src=URL.createObjectURL(f);} else {vid.style.display='none';img.style.display='block';img.src=URL.createObjectURL(f);} });
document.getElementById('postFile').addEventListener('change', function(e){let f=e.target.files[0]; if(!f)return; selectedPostFile=f; document.getElementById('postFileName').innerText='📎 '+f.name.slice(0,16); let preview=document.getElementById('postPreview'); let img=document.getElementById('postPreviewImg'); let vid=document.getElementById('postPreviewVid'); preview.style.display='block'; if(f.type.startsWith('video')){img.style.display='none';vid.style.display='block';vid.src=URL.createObjectURL(f);} else {vid.style.display='none';img.style.display='block';img.src=URL.createObjectURL(f);} });
async function uploadStory(){
  if(!selectedStoryFile){alert('Pick photo');return}
  let cap=document.getElementById('storyCaption').value||''; document.getElementById('storyMsg').innerText='Uploading...';
  let fd=new FormData(); fd.append('media',selectedStoryFile); fd.append('text',cap);
  try{
    let r=await fetch('/api/story',{method:'POST',body:fd}); let txt=await r.text(); let d;
    try{ d=JSON.parse(txt);}catch(e){ throw new Error(txt.slice(0,200)); }
    if(d.ok){document.getElementById('storyMsg').innerText='✅ Story Posted! Friends only can view';document.getElementById('storyPreview').style.display='none';document.getElementById('storySendBtn').style.display='none';document.getElementById('storyCaption').style.display='none';document.getElementById('storyCaption').value='';selectedStoryFile=null;document.getElementById('storyFile').value='';setTimeout(loadStories,800);}
    else{document.getElementById('storyMsg').innerText='Failed: '+(d.error||'');}
  }catch(e){document.getElementById('storyMsg').innerText='Error: '+e.message;}
}
async function createTextStory(){let t=prompt('Text story (24h) friends only:');if(!t)return;let r=await fetch('/api/story/text',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t})});let d=await r.json();if(d.ok)loadStories();}
async function loadStories(){
  try{
    let r=await fetch('/api/stories'); stories=await r.json();
    groupedStories={}; stories.forEach(s=>{ if(!groupedStories[s.username]) groupedStories[s.username]=[]; groupedStories[s.username].push(s); });
    let h='';
    Object.keys(groupedStories).forEach(username=>{
      let userStories=groupedStories[username];
      let first=userStories[0];
      let profPic=profiles[username];
      let inner='';
      if(profPic) inner=`<div class=s-ring><img src="${profPic}"></div>`;
      else {
        let m=first.media_url||''; let low=m.toLowerCase();
        if(first.text &&!m) inner=`<div class=s-ring>${first.text.slice(0,10)}</div>`;
        else if(low.includes('.mp4')||low.includes('.mov')||low.includes('.webm')) inner=`<div class=s-ring>▶️</div>`;
        else if(m) inner=`<div class=s-ring><img src="${m}"></div>`;
        else inner=`<div class=s-ring>?</div>`;
      }
      let countBadge=userStories.length>1?`<div class=s-count>${userStories.length}</div>`:'';
      h+=`<div class=s-item onclick="openGrouped('${username}')"><div style="position:relative">${inner}${countBadge}</div><br><small><b>${username.slice(0,8)}</b></small></div>`;
    });
    document.getElementById('storyBar').innerHTML=h||'<small style=color:#888;padding:12px>No friends stories - add friends in Search tab, only friends see stories</small>';
  }catch(e){document.getElementById('storyBar').innerHTML='<small>Error loading</small>';}
}
function openGrouped(username){ currentGroup=groupedStories[username]||[]; currentGroupIdx=0; document.getElementById('viewerModal').style.display='flex'; showGrouped(); }
function showGrouped(){
  clearTimeout(storyTimer); let s=currentGroup[currentGroupIdx]; if(!s){closeViewer();return;}
  document.getElementById('viewerUser').innerText=s.username;
  document.getElementById('viewerCounter').innerText=(currentGroupIdx+1)+'/'+currentGroup.length;
  document.getElementById('delStoryBtn').style.display=(s.username==curUser)?'inline-block':'none';
  let bar=document.getElementById('progressBar'); bar.innerHTML=currentGroup.map((_,idx)=>`<div class="${idx==currentGroupIdx?'active':idx<currentGroupIdx?'seen':''}"></div>`).join('');
  let img=document.getElementById('viewerMedia'),vid=document.getElementById('viewerVideo'),txt=document.getElementById('viewerText'),cap=document.getElementById('viewerCaption');
  img.style.display=vid.style.display=txt.style.display=cap.style.display='none';
  let m=s.media_url||''; let low=m.toLowerCase();
  if(s.text &&!m){txt.style.display='block';txt.innerText=s.text;}
  else if(low.includes('.mp4')||low.includes('.mov')||low.includes('.webm')){vid.style.display='block';vid.src=m;vid.load(); if(!lowData) vid.play().catch(()=>{}); if(s.text){cap.style.display='block';cap.innerText=s.text;}}
  else if(m){img.style.display='block';img.src=m; if(s.text){cap.style.display='block';cap.innerText=s.text;}}
  fetch('/api/story/view',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:s.id})});
  storyTimer=setTimeout(()=>{nextStory()},6000);
}
function nextStory(){ if(currentGroupIdx<currentGroup.length-1){currentGroupIdx++; showGrouped();} else {closeViewer(); loadStories();} }
function prevStory(){ if(currentGroupIdx>0){currentGroupIdx--; showGrouped();} }
function closeViewer(){clearTimeout(storyTimer);document.getElementById('viewerModal').style.display='none';let v=document.getElementById('viewerVideo');v.pause();}
async function deleteStory(){if(!confirm('Delete?'))return;let s=currentGroup[currentGroupIdx];await fetch('/api/story/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:s.id})}); closeViewer(); loadStories();}
async function replyStory(){
  let input=document.getElementById('storyReplyInput');
  let text=input.value.trim(); if(!text)return;
  let s=currentGroup[currentGroupIdx];
  if(!s)return;
  // send as chat message to story owner
  let fd=new FormData(); fd.append('receiver',s.username); fd.append('text','↩️ Replied to your story: '+text+'\\n[Story: '+(s.text||'media')+']');
  await fetch('/api/send',{method:'POST',body:fd});
  // also notification
  await fetch('/api/story/reply',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({to:s.username,text:text,story_id:s.id})});
  input.value=''; alert('Reply sent to chat with '+s.username); closeViewer(); switchTab('chat'); openChat(s.username);
}
async function loadPosts(){
  let r=await fetch('/api/posts'); let posts=await r.json(); let h=''; if(posts.length==0)h='<div class=card style=text-align:center;color:#888>No posts - public for all</div>';
  posts.forEach(p=>{
    let pic=profiles[p.username];let picHtml=pic?`<img src="${pic}">`:p.username[0];
    let m=p.media_url||''; let low=m.toLowerCase(); let isVideo=low.includes('.mp4')||low.includes('.mov')||low.includes('.webm');
    let media='';
    if(m){
      if(isVideo){
        if(lowData) media=`<div style="background:#000;color:#fff;padding:20px;text-align:center" onclick="this.innerHTML='<video src=${m} controls autoplay style=width:100%></video>'">🎥 Video (Low Data) - Tap to play</div>`;
        else media=`<video src="${m}" controls playsinline preload="metadata" style="width:100%;max-height:400px"></video>`;
      } else {
        media=`<img src="${m}" style="width:100%" loading="lazy">`;
      }
    }
    let del=(p.username==curUser)?`<span class=del onclick="deletePost(${p.id})">🗑️</span>`:'';
    h+=`<div class=card style="padding:0;overflow:hidden"><div style="padding:10px;display:flex;align-items:center;gap:8px"><div class=pic>${picHtml}</div><b>${p.username}</b><small style="margin-left:auto">${(p.created_at||'').slice(0,16)}</small>${del}</div>${p.text?`<div style="padding:0 12px 8px">${p.text}</div>`:''}${media}<div style="padding:10px;display:flex;gap:12px"><span onclick="likePost(${p.id})" style="cursor:pointer">${p.liked?'❤️':'🤍'} ${p.like_count||0}</span><span onclick="commentPost(${p.id})" style="cursor:pointer">💬</span></div></div>`;
  });
  document.getElementById('postsList').innerHTML=h;
}
async function createPost(){
  let txt=document.getElementById('postText').value;
  let f=selectedPostFile||document.getElementById('postFile').files[0];
  if(!txt&&!f){document.getElementById('postMsg').innerText='Add text or tap 📎';return;}
  document.getElementById('postMsg').innerText='Posting...';
  let fd=new FormData(); fd.append('text',txt); if(f) fd.append('media',f);
  try{
    let r=await fetch('/api/post',{method:'POST',body:fd});
    let raw=await r.text(); let d;
    try{ d=JSON.parse(raw);}catch(e){ throw new Error(raw.slice(0,400)); }
    if(d.ok){document.getElementById('postMsg').innerText='✅ Posted! Public';document.getElementById('postText').value='';document.getElementById('postFile').value='';document.getElementById('postPreview').style.display='none';document.getElementById('postFileName').innerText='Tap 📎 for pic/video';selectedPostFile=null;setTimeout(loadPosts,600);}
    else{document.getElementById('postMsg').innerText='Failed: '+(d.error||'');}
  }catch(e){document.getElementById('postMsg').innerText='Error: '+e.message.slice(0,300);}
}
async function deletePost(id){if(!confirm('Delete post?'))return;await fetch('/api/post/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:id})});loadPosts();}
async function likePost(id){await fetch('/api/like',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:id})});loadPosts();}
async function commentPost(id){let t=prompt('Comment:');if(!t)return;await fetch('/api/comment',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:id,text:t})});loadPosts();}
function renderChatUsers(users){let h='';users.forEach(u=>{if(u.username==curUser)return;let pic=u.pic_url?`<img src="${u.pic_url}">`:u.username[0];h+=`<div class=card style="display:flex;align-items:center;gap:10px;cursor:pointer" onclick="openChat('${u.username}')"><div class=pic>${pic}</div><b>${u.username}</b><small style="margin-left:auto;color:#888">friends only</small></div>`});document.getElementById('chatUsers').innerHTML=h||'<div class=card style=color:#888">No friends yet - go to Search to add friends</div>';}
function filterChat(){let q=document.getElementById('searchChat').value.toLowerCase();renderChatUsers(allUsers.filter(u=>u.username.toLowerCase().includes(q)))}
async function loadChatUsers(){
  // load friends only for chat
  try{
    let r=await fetch('/api/friends/list'); let friends=await r.json();
    let friendUsernames = friends.map(f=>f.friend);
    let filtered = allUsers.filter(u=> friendUsernames.includes(u.username));
    // include self friends? also show friends only
    renderChatUsers(filtered.length>0?filtered:allUsers); // fallback show all if no friends yet
  }catch(e){ renderChatUsers(allUsers); }
}
async function openChat(username){
  chatWith=username;
  document.getElementById('chatUsers').style.display='none';document.getElementById('searchChat').style.display='none';
  let box=document.getElementById('chatBox');box.style.display='block';
  box.innerHTML=`<div style="padding:10px"><button onclick="backChat()" style="background:var(--sec);padding:8px;border-radius:8px;border:1px solid var(--border)">← ${username}</button></div><div id=msgs style="padding:10px;padding-bottom:130px"></div><div class=chat-bar><input id=chatText class=pill placeholder="Write message..." /><input type=file id=chatFileHidden accept="image/*,video/*" style="display:none"><div class=sticker onclick="document.getElementById('chatFileHidden').click()">📎</div><button class=yellow onclick=sendMsg()>Send</button></div>`;
  document.getElementById('chatFileHidden').addEventListener('change',function(e){let f=e.target.files[0]; if(f)selectedChatFile=f;});
  loadMsgs();
}
function backChat(){chatWith='';document.getElementById('chatBox').style.display='none';document.getElementById('chatUsers').style.display='block';document.getElementById('searchChat').style.display='block';}
async function loadMsgs(){
  if(!chatWith)return;let r=await fetch('/api/messages?with='+chatWith);let msgs=await r.json();let h='';
  msgs.forEach(m=>{
    let mu=m.media_url||''; let low=mu.toLowerCase(); let isVideo=low.includes('.mp4')||low.includes('.mov')||low.includes('.webm');
    let media=''; if(mu){ if(isVideo) media=`<br><video src="${mu}" controls playsinline style="max-width:220px;border-radius:12px;margin-top:6px"></video>`; else media=`<br><img src="${mu}" style="max-width:220px;border-radius:12px;margin-top:6px">`; }
    let isMe=m.sender==curUser; let del=isMe?`<br><span class=del onclick="deleteMsg(${m.id})">🗑️</span>`:'';
    h+=`<div style="margin:12px 0;text-align:${isMe?'right':'left'}"><span style="background:${isMe?'#000':'#eee'};color:${isMe?'#fff':'#000'};padding:12px 16px;border-radius:22px;display:inline-block;max-width:76%;word-break:break-word">${m.text||''}${media}${del}</span></div>`;
  });
  let el=document.getElementById('msgs'); if(el) el.innerHTML=h;
}
async function sendMsg(){
  let tEl=document.getElementById('chatText');let t=tEl?tEl.value:'';let f=selectedChatFile;if(!t&&!f)return;
  let fd=new FormData();fd.append('receiver',chatWith);fd.append('text',t);if(f)fd.append('media',f);
  if(tEl) tEl.value='';selectedChatFile=null;let hid=document.getElementById('chatFileHidden');if(hid)hid.value='';
  try{
    let r=await fetch('/api/send',{method:'POST',body:fd}); let txt=await r.text(); let d; try{ d=JSON.parse(txt);}catch(e){ throw new Error(txt.slice(0,200)); }
    if(!d.ok) alert('Failed: '+(d.error||''));
  }catch(e){ alert('Error: '+e.message); }
  setTimeout(loadMsgs,400);
}
async function deleteMsg(id){if(!confirm('Delete?'))return;await fetch('/api/message/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:id})});loadMsgs();}
async function searchUsers(){
  let q=document.getElementById('searchUsersInput').value||'';
  let r=await fetch('/api/search?q='+encodeURIComponent(q)); let users=await r.json();
  let h='';
  users.forEach(u=>{
    if(u.username==curUser) return;
    let pic=u.pic_url?`<img src="${u.pic_url}">`:u.username[0];
    let status = u.friend_status||'none';
    let btn='';
    if(status=='none') btn=`<button class=friend-btn f-add onclick="addFriend('${u.username}')">+ Add</button>`;
    else if(status=='pending_sent') btn=`<button class=friend-btn f-pending>Pending</button>`;
    else if(status=='pending_received') btn=`<button class=friend-btn f-add onclick="acceptFriend('${u.username}')">Accept</button>`;
    else if(status=='friends') btn=`<button class=friend-btn f-friends>✓ Friends</button>`;
    h+=`<div class=card style="display:flex;align-items:center;gap:10px"><div class=pic>${pic}</div><b>${u.username}</b><div style="margin-left:auto">${btn}</div></div>`;
  });
  document.getElementById('searchResults').innerHTML=h||'<small style=color:#888>No users found</small>';
}
async function addFriend(username){await fetch('/api/friend/request',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({to:username})}); searchUsers(); loadFriendRequests();}
async function acceptFriend(username){await fetch('/api/friend/accept',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({from:username})}); searchUsers(); loadFriendRequests(); loadMyFriends(); loadStories();}
async function loadFriendRequests(){
  let r=await fetch('/api/friend/requests'); let reqs=await r.json();
  document.getElementById('reqCount').innerText=reqs.length;
  let h='';
  reqs.forEach(req=>{
    let pic=profiles[req.sender]?`<img src="${profiles[req.sender]}">`:req.sender[0];
    h+=`<div class=card style="display:flex;align-items:center;gap:10px"><div class=pic>${pic}</div><b>${req.sender}</b><div style="margin-left:auto;display:flex;gap:6px"><button class=friend-btn f-add onclick="acceptFriend('${req.sender}')">Accept</button><button class=friend-btn f-pending onclick="declineFriend('${req.sender}')">Decline</button></div></div>`;
  });
  document.getElementById('friendRequests').innerHTML=h||'<small style=color:#888>No pending requests</small>';
}
async function declineFriend(username){await fetch('/api/friend/decline',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({from:username})}); loadFriendRequests();}
async function loadMyFriends(){
  let r=await fetch('/api/friends/list'); let friends=await r.json();
  let h='';
  friends.forEach(f=>{
    let pic=profiles[f.friend]?`<img src="${profiles[f.friend]}">`:f.friend[0];
    h+=`<div class=card style="display:flex;align-items:center;gap:10px"><div class=pic>${pic}</div><b>${f.friend}</b><span style="margin-left:auto;color:#00c851;font-size:12px">✓ Friends</span></div>`;
  });
  document.getElementById('myFriendsList').innerHTML=h||'<small style=color:#888>No friends yet - search above and add</small>';
}
async function loadNotifs(){
  let r=await fetch('/api/notifications'); let notifs=await r.json();
  let h='';
  notifs.forEach(n=>{
    h+=`<div class=card><small style=color:#888">${n.created_at.slice(0,16)} - ${n.type}</small><br><b>${n.from_user}</b>: ${n.text}<br>${n.type=='friend_request'?`<button class=friend-btn f-add onclick="acceptFriend('${n.from_user}'); switchTab('search');">Accept Friend</button>`:''}</div>`;
  });
  document.getElementById('notifList').innerHTML=h||'<small style=color:#888>No notifications</small>';
}
async function loadNotifCount(){
  try{
    let r=await fetch('/api/notifications/count'); let d=await r.json();
    let el=document.getElementById('notifCount');
    if(d.count>0){el.style.display='block'; el.innerText=d.count>99?'99+':d.count;} else {el.style.display='none';}
  }catch(e){}
}
async function clearNotifs(){await fetch('/api/notifications/clear',{method:'POST'}); loadNotifs(); loadNotifCount();}
async function uploadProfilePic(){
  let f=selectedProfileFile||document.getElementById('profilePicInput').files[0];
  if(!f){alert('Pick pic - tap 📎');return}
  document.getElementById('profileMsg').innerText='Uploading...';
  let fd=new FormData();fd.append('media',f);
  try{
    let r=await fetch('/api/profile/pic',{method:'POST',body:fd}); let txt=await r.text(); let d; try{ d=JSON.parse(txt);}catch{ throw new Error(txt.slice(0,200)); }
    if(d.ok){
      document.getElementById('profileMsg').innerText='✅ Updated!';
      profiles[curUser]=d.url; renderTopPic();
      let big=document.getElementById('profilePicBig'); big.innerHTML=`<img src="${d.url}?t=${Date.now()}" style="width:100%;height:100%;object-fit:cover">`;
      selectedProfileFile=null; setTimeout(()=>{ loadProfiles(); loadStories(); }, 800);
    } else {document.getElementById('profileMsg').innerText='Failed';}
  }catch(e){document.getElementById('profileMsg').innerText='Error: '+e.message;}
}
async function logout(){await fetch('/logout');location.href='/login'}
loadMe();switchTab('stories');
</script></body></html>"""

@app.route('/')
def home():
    if 'username' not in session: return redirect('/login')
    return render_template_string(MAIN_HTML)

@app.route('/login', methods=['GET'])
def login_page(): return render_template_string(LOGIN_HTML)

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

@app.route('/login', methods=['POST'])
def login_api():
    data=request.json; u=data.get('username','').strip()[:20]; p=data.get('password','')
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT password FROM auth WHERE username=%s" if USE_POSTGRES else "SELECT password FROM auth WHERE username=?", (u,))
    row=c.fetchone(); conn.close()
    if not row or not check_password_hash(row[0],p): return jsonify({"ok":False,"error":"Wrong pass"})
    session['username']=u; return jsonify({"ok":True})

@app.route('/signup', methods=['POST'])
def signup():
    data=request.json; u=data.get('username','').strip()[:20]; p=data.get('password','')
    if len(u)<3 or len(p)<3: return jsonify({"ok":False,"error":"Min 3"})
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT 1 FROM auth WHERE username=%s" if USE_POSTGRES else "SELECT 1 FROM auth WHERE username=?", (u,))
    if c.fetchone(): conn.close(); return jsonify({"ok":False,"error":"Taken"})
    if USE_POSTGRES:
        c.execute("INSERT INTO auth VALUES (%s,%s,%s)",(u,generate_password_hash(p),datetime.now().isoformat()))
        c.execute("INSERT INTO profiles (username,pic_url,last_seen) VALUES (%s,%s,%s) ON CONFLICT (username) DO NOTHING",(u,"",datetime.now().isoformat()))
    else:
        c.execute("INSERT INTO auth VALUES (?,?,?)",(u,generate_password_hash(p),datetime.now().isoformat()))
        c.execute("INSERT OR IGNORE INTO profiles (username,pic_url,last_seen) VALUES (?,?,?)",(u,"",datetime.now().isoformat()))
    conn.commit(); conn.close(); session['username']=u; return jsonify({"ok":True})

@app.route('/api/me')
def api_me(): return jsonify({"username":session.get('username','')})

@app.route('/api/users')
def api_users():
    conn=get_conn(); c=conn.cursor(); c.execute("SELECT username,pic_url FROM profiles"); rows=c.fetchall(); conn.close()
    return jsonify([{"username":r[0],"pic_url":r[1] or ""} for r in rows])

@app.route('/api/search')
def api_search():
    me = session.get('username')
    q = (request.args.get('q','') or '').strip().lower()
    conn = get_conn()
    c = conn.cursor()
    try:
        if q:
            like = f"%{q}%"
            like2 = f"%{q.split()[0]}%" if ' ' in q else like
            if USE_POSTGRES:
                c.execute("SELECT username,pic_url FROM profiles WHERE LOWER(username) LIKE %s OR LOWER(username) LIKE %s LIMIT 30", (like, like2))
            else:
                c.execute("SELECT username,pic_url FROM profiles WHERE LOWER(username) LIKE? OR LOWER(username) LIKE? LIMIT 30", (like, like2))
        else:
            c.execute("SELECT username,pic_url FROM profiles LIMIT 30")
        users = c.fetchall()
    except Exception as e:
        print(f"SEARCH ERROR: {e}")
        users = []
    try:
        if USE_POSTGRES:
            c.execute("SELECT sender,receiver,status FROM friends WHERE sender=%s OR receiver=%s", (me,me))
        else:
            c.execute("SELECT sender,receiver,status FROM friends WHERE sender=? OR receiver=?", (me,me))
        fr = c.fetchall()
    except:
        fr = []
    status_map = {}
    for s,r,st in fr:
        if s == me:
            status_map[r] = 'friends' if st == 'accepted' else 'pending_sent'
        else:
            status_map[s] = 'friends' if st == 'accepted' else 'pending_received'
    out = []
    for u,pic in users:
        if u == me:
            continue
        out.append({"username": u, "pic_url": pic or "", "friend_status": status_map.get(u, 'none')})
    conn.close()
    return jsonify(out)

@app.route('/api/friend/request', methods=['POST'])
def api_friend_request():
    me=session.get('username'); data=request.json; to=data.get('to')
    if not to or to==me: return jsonify({"ok":False})
    conn=get_conn(); c=conn.cursor()
    # check exists
    c.execute("SELECT 1 FROM friends WHERE (sender=%s AND receiver=%s) OR (sender=%s AND receiver=%s)" if USE_POSTGRES else "SELECT 1 FROM friends WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?)", (me,to,to,me))
    if c.fetchone(): conn.close(); return jsonify({"ok":False,"error":"exists"})
    c.execute("INSERT INTO friends (sender,receiver,status,created_at) VALUES (%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO friends (sender,receiver,status,created_at) VALUES (?,?,?,?)", (me,to,'pending',datetime.now().isoformat()))
    # notification
    c.execute("INSERT INTO notifications (username,type,from_user,text,created_at) VALUES (%s,%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO notifications (username,type,from_user,text,created_at) VALUES (?,?,?,?,?)", (to,'friend_request',me,f'{me} sent you friend request',datetime.now().isoformat()))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/api/friend/accept', methods=['POST'])
def api_friend_accept():
    me=session.get('username'); data=request.json; frm=data.get('from')
    conn=get_conn(); c=conn.cursor()
    c.execute("UPDATE friends SET status='accepted' WHERE sender=%s AND receiver=%s AND status='pending'" if USE_POSTGRES else "UPDATE friends SET status='accepted' WHERE sender=? AND receiver=? AND status='pending'", (frm,me))
    c.execute("INSERT INTO notifications (username,type,from_user,text,created_at) VALUES (%s,%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO notifications (username,type,from_user,text,created_at) VALUES (?,?,?,?,?)", (frm,'friend_accept',me,f'{me} accepted your request',datetime.now().isoformat()))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/api/friend/decline', methods=['POST'])
def api_friend_decline():
    me=session.get('username'); data=request.json; frm=data.get('from')
    conn=get_conn(); c=conn.cursor()
    c.execute("DELETE FROM friends WHERE sender=%s AND receiver=%s AND status='pending'" if USE_POSTGRES else "DELETE FROM friends WHERE sender=? AND receiver=? AND status='pending'", (frm,me))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/api/friend/requests')
def api_friend_requests():
    me=session.get('username'); conn=get_conn(); c=conn.cursor()
    c.execute("SELECT sender,created_at FROM friends WHERE receiver=%s AND status='pending'" if USE_POSTGRES else "SELECT sender,created_at FROM friends WHERE receiver=? AND status='pending'", (me,))
    rows=c.fetchall(); conn.close()
    return jsonify([{"sender":r[0],"created_at":r[1]} for r in rows])

@app.route('/api/friends/list')
def api_friends_list():
    me=session.get('username'); conn=get_conn(); c=conn.cursor()
    c.execute("SELECT sender,receiver FROM friends WHERE (sender=%s OR receiver=%s) AND status='accepted'" if USE_POSTGRES else "SELECT sender,receiver FROM friends WHERE (sender=? OR receiver=?) AND status='accepted'", (me,me))
    rows=c.fetchall(); conn.close()
    out=[]
    for s,r in rows:
        friend = r if s==me else s
        out.append({"friend":friend})
    return jsonify(out)

@app.route('/api/posts')
def api_posts():
    me=session.get('username'); conn=get_conn(); c=conn.cursor()
    try:
        c.execute("SELECT id,username,text,media_url,created_at FROM posts ORDER BY id DESC LIMIT 50")
    except Exception as e:
        conn.rollback()
        # try repair and retry
        try:
            c.execute("ALTER TABLE posts ADD COLUMN IF NOT EXISTS text TEXT")
            c.execute("ALTER TABLE posts ADD COLUMN IF NOT EXISTS media_url TEXT")
            conn.commit()
            c.execute("SELECT id,username,text,media_url,created_at FROM posts ORDER BY id DESC LIMIT 50")
        except Exception as e2:
            conn.close(); return jsonify([])

    rows=c.fetchall(); out=[]
    for r in rows:
        pid=r[0]; lc=0; liked=False
        try:
            c.execute("SELECT COUNT(*) FROM post_likes WHERE post_id=%s" if USE_POSTGRES else "SELECT COUNT(*) FROM post_likes WHERE post_id=?", (pid,)); lc=c.fetchone()[0]
            c.execute("SELECT 1 FROM post_likes WHERE post_id=%s AND username=%s" if USE_POSTGRES else "SELECT 1 FROM post_likes WHERE post_id=? AND username=?", (pid,me))
            if c.fetchone(): liked=True
        except: pass
        out.append({"id":pid,"username":r[1],"text":r[2],"media_url":r[3],"created_at":r[4],"like_count":lc,"liked":liked})
    conn.close(); return jsonify(out)

@app.route('/api/post', methods=['POST'])
def api_post():
    try:
        me=session.get('username')
        if not me: return jsonify({"ok":False})
        txt=request.form.get('text','')[:500]
        f=request.files.get('media'); url=''
        if f and f.filename: url = upload_to_cloudinary(f)
        conn=get_conn(); c=conn.cursor()
        c.execute("INSERT INTO posts(username, text, media_url) VALUES (?,?,?)",(me, txt, url))
        conn.commit(); conn.close()
        return jsonify({"ok":True})
    except Exception as e:
        print(f"POST ERR {e}"); return jsonify({"ok":False, "err":str(e)}), 500

@app.route('/api/post/delete', methods=['POST'])
def api_post_delete():
    me=session.get('username'); data=request.json; pid=data.get('id')
    conn=get_conn(); c=conn.cursor()
    c.execute("DELETE FROM posts WHERE id=%s AND username=%s" if USE_POSTGRES else "DELETE FROM posts WHERE id=? AND username=?", (pid,me)); conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/api/stories', methods=['GET'])
def api_stories():
    me = session.get('username')
    if not me: return jsonify([]),401
    import time
    conn = get_conn(); c = conn.cursor()
    cutoff = time.time() - 86400

    # get friends list
    try:
        if USE_POSTGRES:
            c.execute("SELECT sender,receiver FROM friends WHERE sender=%s OR receiver=%s", (me,me))
        else:
            c.execute("SELECT sender,receiver FROM friends WHERE sender=? OR receiver=?", (me,me))
    except:
        try:
            if USE_POSTGRES:
                c.execute("SELECT from_user,to_user FROM friends WHERE from_user=%s OR to_user=%s", (me,me))
            else:
                c.execute("SELECT from_user,to_user FROM friends WHERE from_user=? OR to_user=?", (me,me))
        except:
            friends = set([me])
            fr = []
        else:
            fr = c.fetchall()
    else:
        fr = c.fetchall()

    friends = set([me])
    try:
        for s,r in fr:
            if s==me: friends.add(r)
            elif r==me: friends.add(s)
    except: pass

    # auto-delete old stories (>24h)
    try:
        if USE_POSTGRES:
            c.execute("DELETE FROM stories WHERE timestamp < %s", (cutoff,))
        else:
            c.execute("DELETE FROM stories WHERE timestamp <?", (cutoff,))
        conn.commit()
    except: pass

    # get only last 24h stories from friends
    out=[]
    try:
        c.execute("SELECT id,username,media_url,created_at FROM stories")
        rows=c.fetchall()
        for r in rows:
            try:
                if float(r[3]) < cutoff:
                    continue
            except:
                pass
            out.append({'id':r[0], 'username':r[1], 'media_url':r[2], 'created_at':r[3]})
    except Exception as e:
        print(f"STORIES ERR {e}")
    conn.close()
    return jsonify(out)

@app.route('/api/story', methods=['POST'])
def api_story():
    me=session.get('username')
    f=request.files.get('media'); url=''
    if f and f.filename: url = upload_to_cloud(f)
    conn=get_conn(); c=conn.cursor()
    c.execute("INSERT INTO stories(username,image,created) VALUES(?,?,?)",(me,url,time.time()))
    conn.commit(); conn.close()
    return jsonify({"ok":True})

@app.route('/api/story/delete', methods=['POST'])
def api_story_delete():
    me=session.get('username'); data=request.json; sid=data.get('id')
    conn=get_conn(); c=conn.cursor()
    c.execute("DELETE FROM stories WHERE id=%s AND username=%s" if USE_POSTGRES else "DELETE FROM stories WHERE id=? AND username=?", (sid,me)); conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/api/story/text', methods=['POST'])
def api_story_text():
    me=session.get('username'); data=request.json; txt=data.get('text','')[:100]
    if not txt: return jsonify({"ok":False,"error":"empty"})
    conn=get_conn(); c=conn.cursor(); now=datetime.now(); exp=now+timedelta(hours=24)
    c.execute("INSERT INTO stories (username,media_url,text,created_at,expires_at) VALUES (%s,%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO stories (username,media_url,text,created_at,expires_at) VALUES (?,?,?,?,?)", (me,"",txt,now.isoformat(),exp.isoformat()))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/api/story/view', methods=['POST'])
def api_story_view():
    me=session.get('username'); data=request.json; sid=data.get('id'); conn=get_conn(); c=conn.cursor()
    try: c.execute("INSERT INTO story_views VALUES (%s,%s) ON CONFLICT DO NOTHING" if USE_POSTGRES else "INSERT OR IGNORE INTO story_views VALUES (?,?)", (sid,me)); conn.commit()
    except: pass
    conn.close(); return jsonify({"ok":True})

@app.route('/api/story/reply', methods=['POST'])
def api_story_reply():
    me=session.get('username'); data=request.json; to=data.get('to'); txt=data.get('text','')[:200]
    if not to: return jsonify({"ok":False})
    conn=get_conn(); c=conn.cursor()
    c.execute("INSERT INTO notifications (username,type,from_user,text,created_at) VALUES (%s,%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO notifications (username,type,from_user,text,created_at) VALUES (?,?,?,?,?)", (to,'story_reply',me,f'Replied to your story: {txt}',datetime.now().isoformat()))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/api/avatar', methods=['POST'])
def api_avatar():
    me=session.get('username')
    f=request.files.get('media')
    if f and f.filename:
        url = upload_to_cloud(f)
        conn=get_conn(); c=conn.cursor()
        c.execute("UPDATE users SET avatar=? WHERE username=?",(url,me))
        conn.commit(); conn.close()
    return jsonify({"ok":True})

@app.route('/api/friend/request', methods=['POST'])
def api_friend_request():
    me = session.get('username')
    if not me: return jsonify({'error':'not logged'}),401
    to_user = request.json.get('to_user')
    if not to_user or to_user == me: return jsonify({'error':'invalid'}),400
    conn = get_conn(); c = conn.cursor()
    if USE_POSTGRES:
        c.execute("SELECT id FROM friend_requests WHERE (from_user=%s AND to_user=%s) OR (from_user=%s AND to_user=%s)", (me,to_user,to_user,me))
    else:
        c.execute("SELECT id FROM friend_requests WHERE (from_user=? AND to_user=?) OR (from_user=? AND to_user=?)", (me,to_user,to_user,me))
    if c.fetchone():
        conn.close()
        return jsonify({'status':'already exists'})
    if USE_POSTGRES:
        c.execute("INSERT INTO friend_requests (from_user,to_user,status) VALUES (%s,%s,'pending')", (me,to_user))
    else:
        c.execute("INSERT INTO friend_requests (from_user,to_user,status) VALUES (?,'pending')", (me,to_user)) # if 3 cols use this
        # If above fails, use: INSERT INTO friend_requests (from_user,to_user,status) VALUES (?,?,?)
    try:
        if USE_POSTGRES:
            pass
        else:
            c.execute("INSERT INTO friend_requests (from_user,to_user,status) VALUES (?,?,?)", (me,to_user,'pending'))
    except:
        pass
    # Final safe insert for both DBs
    try:
        if USE_POSTGRES:
            c.execute("INSERT INTO friend_requests (from_user,to_user,status) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING", (me,to_user,'pending'))
        else:
            c.execute("INSERT OR IGNORE INTO friend_requests (from_user,to_user,status) VALUES (?,?,?)", (me,to_user,'pending'))
    except:
        pass
    conn.commit(); conn.close()
    return jsonify({'status':'sent'})

@app.route('/api/friend/list_requests', methods=['GET'])
def api_friend_list_requests():
    me = session.get('username')
    if not me: return jsonify([]),401
    conn = get_conn(); c = conn.cursor()
    if USE_POSTGRES:
        c.execute("SELECT id,from_user FROM friend_requests WHERE to_user=%s AND status='pending'", (me,))
    else:
        c.execute("SELECT id,from_user FROM friend_requests WHERE to_user=? AND status='pending'", (me,))
    rows = c.fetchall()
    conn.close()
    return jsonify([{'id':r[0],'from_user':r[1]} for r in rows])

@app.route('/api/friend/approve', methods=['POST'])
def api_friend_approve():
    me = session.get('username')
    if not me: return jsonify({'error':'not logged'}),401
    req_id = request.json.get('id')
    conn = get_conn(); c = conn.cursor()
    if USE_POSTGRES:
        c.execute("UPDATE friend_requests SET status='accepted' WHERE id=%s AND to_user=%s", (req_id, me))
    else:
        c.execute("UPDATE friend_requests SET status='accepted' WHERE id=? AND to_user=?", (req_id, me))
    conn.commit(); conn.close()
    return jsonify({'status':'accepted'})

@app.route('/api/friend/decline', methods=['POST'])
def api_friend_decline():
    me = session.get('username')
    if not me: return jsonify({'error':'not logged'}),401
    req_id = request.json.get('id')
    conn = get_conn(); c = conn.cursor()
    if USE_POSTGRES:
        c.execute("DELETE FROM friend_requests WHERE id=%s AND to_user=%s", (req_id, me))
    else:
        c.execute("DELETE FROM friend_requests WHERE id=? AND to_user=?", (req_id, me))
    conn.commit(); conn.close()
    return jsonify({'status':'declined'})

@app.route('/api/friend/my_friends', methods=['GET'])
def api_my_friends():
    me = session.get('username')
    if not me: return jsonify([]),401
    conn = get_conn(); c = conn.cursor()
    if USE_POSTGRES:
        c.execute("SELECT from_user,to_user FROM friend_requests WHERE status='accepted' AND (from_user=%s OR to_user=%s)", (me,me))
    else:
        c.execute("SELECT from_user,to_user FROM friend_requests WHERE status='accepted' AND (from_user=? OR to_user=?)", (me,me))
    rows = c.fetchall()
    friends = []
    for f,t in rows:
        friends.append(t if f==me else f)
    conn.close()
    return jsonify(list(set(friends)))
import time

@app.route('/api/status/ping', methods=['POST'])
def api_status_ping():
    me = session.get('username')
    if not me: return jsonify({'ok':False}),401
    now = time.time()
    conn = get_conn(); c = conn.cursor()
    if USE_POSTGRES:
        c.execute("INSERT INTO user_status (username,online,last_seen) VALUES (%s,1,%s) ON CONFLICT (username) DO UPDATE SET online=1, last_seen=%s", (me,now,now))
    else:
        c.execute("INSERT OR REPLACE INTO user_status (username,online,last_seen) VALUES (?,?,?)", (me,1,now))
    conn.commit(); conn.close()
    return jsonify({'ok':True})

@app.route('/api/status/offline', methods=['POST'])
def api_status_offline():
    me = session.get('username')
    if not me: return jsonify({'ok':False}),401
    now = time.time()
    conn = get_conn(); c = conn.cursor()
    if USE_POSTGRES:
        c.execute("UPDATE user_status SET online=0, last_seen=%s WHERE username=%s", (now,me))
    else:
        c.execute("UPDATE user_status SET online=0, last_seen=? WHERE username=?", (now,me))
    conn.commit(); conn.close()
    return jsonify({'ok':True})

@app.route('/api/status/get', methods=['GET'])
def api_status_get():
    me = session.get('username')
    if not me: return jsonify({}),401
    other = request.args.get('user')
    conn = get_conn(); c = conn.cursor()
    now = time.time()
    # Auto set offline if last_seen > 60 seconds ago
    if USE_POSTGRES:
        c.execute("UPDATE user_status SET online=0 WHERE last_seen < %s", (now-60,))
        if other:
            c.execute("SELECT online,last_seen FROM user_status WHERE username=%s", (other,))
            r = c.fetchone()
        else:
            c.execute("SELECT username,online,last_seen FROM user_status")
            r = c.fetchall()
    else:
        c.execute("UPDATE user_status SET online=0 WHERE last_seen <?", (now-60,))
        if other:
            c.execute("SELECT online,last_seen FROM user_status WHERE username=?", (other,))
            r = c.fetchone()
        else:
            c.execute("SELECT username,online,last_seen FROM user_status")
            r = c.fetchall()
    conn.commit(); conn.close()
    if other:
        if not r: return jsonify({'online':0,'last_seen':0})
        return jsonify({'online':r[0],'last_seen':r[1]})
    else:
        return jsonify({row[0]: {'online':row[1],'last_seen':row[2]} for row in r})

@app.route('/api/messages/read', methods=['POST'])
def api_messages_read():
    me = session.get('username')
    if not me: return jsonify({'ok':False}),401
    other = request.json.get('from_user')
    if not other: return jsonify({'ok':False}),400
    conn = get_conn(); c = conn.cursor()
    if USE_POSTGRES:
        c.execute("UPDATE messages SET read=1 WHERE sender=%s AND to_user=%s AND read=0", (other, me))
    else:
        c.execute("UPDATE messages SET read=1 WHERE sender=? AND to_user=? AND read=0", (other, me))
    conn.commit(); conn.close()
    return jsonify({'ok':True})

@app.route('/api/messages/unread_count', methods=['GET'])
def api_unread_count():
    me = session.get('username')
    if not me: return jsonify({}),401
    conn = get_conn(); c = conn.cursor()
    if USE_POSTGRES:
        c.execute("SELECT sender, COUNT(*) FROM messages WHERE to_user=%s AND read=0 GROUP BY sender", (me,))
    else:
        c.execute("SELECT sender, COUNT(*) FROM messages WHERE to_user=? AND read=0 GROUP BY sender", (me,))
    rows = c.fetchall()
    conn.close()
    return jsonify({r[0]:r[1] for r in rows})

@app.route('/api/messages', methods=['GET','POST'])
def api_messages():
    me = session.get('username')
    if not me:
        return jsonify({'error':'not logged'}),401
    conn = get_conn(); c = conn.cursor()

    if request.method == 'GET':
        other = request.args.get('user')
        if not other:
            conn.close()
            return jsonify([])
        if USE_POSTGRES:
            try:
                c.execute("SELECT id,sender,to_user,message,media_url,reply_to,read, timestamp FROM messages WHERE (sender=%s AND to_user=%s) OR (sender=%s AND to_user=%s) ORDER BY id ASC", (me,other,other,me))
            except:
                c.execute("SELECT id,sender,to_user,message,media_url,reply_to,read FROM messages WHERE (sender=%s AND to_user=%s) OR (sender=%s AND to_user=%s) ORDER BY id ASC", (me,other,other,me))
        else:
            try:
                c.execute("SELECT id,sender,to_user,message,media_url,reply_to,read,timestamp FROM messages WHERE (sender=? AND to_user=?) OR (sender=? AND to_user=?) ORDER BY id ASC", (me,other,other,me))
            except:
                c.execute("SELECT id,sender,to_user,message,media_url,reply_to,read FROM messages WHERE (sender=? AND to_user=?) OR (sender=? AND to_user=?) ORDER BY id ASC", (me,other,other,me))
        rows = c.fetchall()
        conn.close()
        out = []
        for r in rows:
            # r = id, sender, to_user, message, media_url, reply_to, read, [timestamp]
            out.append({
                'id': r[0],
                'sender': r[1],
                'to_user': r[2],
                'message': r[3] if len(r)>3 else '',
                'media_url': r[4] if len(r)>4 else None,
                'reply_to': r[5] if len(r)>5 else None,
                'read': r[6] if len(r)>6 else 0,
                'timestamp': r[7] if len(r)>7 else None
            })
        return jsonify(out)

    else: # POST - send message
        data = request.get_json() or {}
        to_user = data.get('to_user')
        msg = data.get('message','')
        media_url = data.get('media_url')
        reply_to = data.get('reply_to') # <-- swipe reply id
        if not to_user:
            conn.close()
            return jsonify({'error':'no to_user'}),400

        if USE_POSTGRES:
            try:
                c.execute("INSERT INTO messages (sender,to_user,message,media_url,reply_to,read) VALUES (%s,%s,%s,%s,%s,0)", (me,to_user,msg,media_url,reply_to))
            except Exception as e:
                # fallback if columns missing
                try:
                    c.execute("INSERT INTO messages (sender,to_user,message,media_url,reply_to,read,timestamp) VALUES (%s,%s,%s,%s,%s,0,%s)", (me,to_user,msg,media_url,reply_to,time.time()))
                except:
                    c.execute("INSERT INTO messages (sender,to_user,message) VALUES (%s,%s,%s)", (me,to_user,msg))
        else:
            try:
                c.execute("INSERT INTO messages (sender,to_user,message,media_url,reply_to,read) VALUES (?,?,?,?,?,0)", (me,to_user,msg,media_url,reply_to))
            except:
                try:
                    c.execute("INSERT INTO messages (sender,to_user,message,media_url,reply_to,read,timestamp) VALUES (?,?,?,?,?,0,?)", (me,to_user,msg,media_url,reply_to,time.time()))
                except:
                    c.execute("INSERT INTO messages (sender,to_user,message) VALUES (?,?,?)", (me,to_user,msg))
        conn.commit(); conn.close()
        return jsonify({'status':'sent'})

@app.route('/api/send', methods=['POST'])
def api_send():
    me=session.get('username')
    try:
        other=request.form.get('receiver',''); txt=request.form.get('text','')[:500]; f=request.files.get('media'); url=''
        if f and f.filename and f.filename!='':
            import uuid; ext=f.filename.rsplit('.',1)[-1].lower() if '.' in f.filename else 'jpg'; name=str(uuid.uuid4())[:8]+'.'+ext; os.makedirs('static/uploads',exist_ok=True); path=os.path.join('static/uploads',name); f.save(path); url='/'+path
        if not txt and not url: return jsonify({"ok":False,"error":"empty"}),400
        conn=get_conn(); c=conn.cursor()
        c.execute("INSERT INTO messages (sender,receiver,text,media_url,created_at) VALUES (%s,%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO messages (sender,receiver,text,media_url,created_at) VALUES (?,?,?,?,?)", (me,other,txt,url,datetime.now().isoformat()))
        c.execute("INSERT INTO notifications (username,type,from_user,text,created_at) VALUES (%s,%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO notifications (username,type,from_user,text,created_at) VALUES (?,?,?,?,?)", (other,'message',me,f'Message: {txt[:30] or "photo/video"}',datetime.now().isoformat()))
        conn.commit(); conn.close(); return jsonify({"ok":True})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"ok":False,"error":str(e)}),500

@app.route('/api/message/delete', methods=['POST'])
def api_message_delete():
    me=session.get('username'); data=request.json; mid=data.get('id')
    conn=get_conn(); c=conn.cursor()
    c.execute("DELETE FROM messages WHERE id=%s AND sender=%s" if USE_POSTGRES else "DELETE FROM messages WHERE id=? AND sender=?", (mid,me)); conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/api/notifications')
def api_notifications():
    me=session.get('username'); conn=get_conn(); c=conn.cursor()
    c.execute("SELECT id,type,from_user,text,created_at FROM notifications WHERE username=%s ORDER BY id DESC LIMIT 50" if USE_POSTGRES else "SELECT id,type,from_user,text,created_at FROM notifications WHERE username=? ORDER BY id DESC LIMIT 50", (me,))
    rows=c.fetchall(); conn.close()
    return jsonify([{"id":r[0],"type":r[1],"from_user":r[2],"text":r[3],"created_at":r[4]} for r in rows])

@app.route('/api/notifications/count')
def api_notifications_count():
    me=session.get('username'); conn=get_conn(); c=conn.cursor()
    c.execute("SELECT COUNT(*) FROM notifications WHERE username=%s AND is_read=0" if USE_POSTGRES else "SELECT COUNT(*) FROM notifications WHERE username=? AND is_read=0", (me,))
    cnt=c.fetchone()[0]; conn.close(); return jsonify({"count":cnt})

@app.route('/api/notifications/clear', methods=['POST'])
def api_notifications_clear():
    me=session.get('username'); conn=get_conn(); c=conn.cursor()
    c.execute("DELETE FROM notifications WHERE username=%s" if USE_POSTGRES else "DELETE FROM notifications WHERE username=?", (me,)); conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/static/uploads/<path:filename>')
def uploads(filename): return send_from_directory('static/uploads', filename)

if __name__=='__main__':
    port=int(os.environ.get("PORT",5000)); app.run(host='0.0.0.0',port=port)
