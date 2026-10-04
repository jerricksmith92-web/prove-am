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

def get_conn():
    if USE_POSTGRES:
        try:
            import psycopg2
            return psycopg2.connect(DB_URL)
        except:
            import psycopg
            return psycopg.connect(DB_URL)
    return sqlite3.connect("app.db")

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
    try:
        nuclear_repair()
    except:
        pass
    conn=get_conn(); c=conn.cursor()
    if USE_POSTGRES:
        c.execute("CREATE TABLE IF NOT EXISTS auth (username TEXT PRIMARY KEY, password TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS profiles (username TEXT PRIMARY KEY, pic_url TEXT, bio TEXT, last_seen TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS posts (id SERIAL PRIMARY KEY, username TEXT, text TEXT, media_url TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS post_likes (post_id INT, username TEXT, PRIMARY KEY(post_id,username))")
        c.execute("CREATE TABLE IF NOT EXISTS comments (id SERIAL PRIMARY KEY, post_id INT, username TEXT, text TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS messages (id SERIAL PRIMARY KEY, sender TEXT, receiver TEXT, text TEXT, media_url TEXT, created_at TEXT, read INT DEFAULT 0, reply_to TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS stories (id SERIAL PRIMARY KEY, username TEXT, media_url TEXT, text TEXT, created_at TEXT, expires_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS story_views (story_id INT, viewer TEXT, PRIMARY KEY(story_id,viewer))")
        c.execute("CREATE TABLE IF NOT EXISTS friends (id SERIAL PRIMARY KEY, sender TEXT, receiver TEXT, status TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS notifications (id SERIAL PRIMARY KEY, username TEXT, type TEXT, from_user TEXT, text TEXT, created_at TEXT, is_read INT DEFAULT 0)")
        c.execute("CREATE TABLE IF NOT EXISTS user_status (username TEXT PRIMARY KEY, last_seen REAL)")
    else:
        c.execute("CREATE TABLE IF NOT EXISTS auth (username TEXT PRIMARY KEY, password TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS profiles (username TEXT PRIMARY KEY, pic_url TEXT, bio TEXT, last_seen TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, text TEXT, media_url TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS post_likes (post_id INT, username TEXT, PRIMARY KEY(post_id,username))")
        c.execute("CREATE TABLE IF NOT EXISTS comments (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INT, username TEXT, text TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, receiver TEXT, text TEXT, media_url TEXT, created_at TEXT, read INT DEFAULT 0, reply_to TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS stories (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, media_url TEXT, text TEXT, created_at TEXT, expires_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS story_views (story_id INT, viewer TEXT, PRIMARY KEY(story_id,viewer))")
        c.execute("CREATE TABLE IF NOT EXISTS friends (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, receiver TEXT, status TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, type TEXT, from_user TEXT, text TEXT, created_at TEXT, is_read INT DEFAULT 0)")
        c.execute("CREATE TABLE IF NOT EXISTS user_status (username TEXT PRIMARY KEY, last_seen REAL)")
    conn.commit(); conn.close()
    print("DB READY V36 FINAL FIX")

init_db()

LOGIN_HTML="""<!DOCTYPE html><html><head><meta name=viewport content="width=device-width,initial-scale=1"><style>body{background:#000;color:#fff;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}.box{background:#111;padding:24px;border-radius:22px;width:330px;text-align:center;border:1px solid #222}input{width:100%;padding:13px;margin:8px 0;border-radius:12px;border:none;background:#222;color:#fff;font-size:16px}button{width:100%;padding:13px;background:#ffcc00;border:none;border-radius:12px;font-weight:bold}</style></head><body><div class=box><h2 style=color:#ffcc00>PROVE AM</h2><input id=u placeholder=Username><input id=p type=password placeholder=Password><button onclick=login()>Login</button><button onclick=signup() style=background:#222;color:#fff;margin-top:8px>Sign Up</button><p id=msg style=color:#ff5555></p></div><script>async function login(){let r=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u.value,password:p.value})});let d=await r.json();if(d.ok)location.href='/';else msg.innerText=d.error}async function signup(){let r=await fetch('/signup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u.value,password:p.value})});let d=await r.json();if(d.ok)location.href='/';else msg.innerText=d.error}</script></body></html>"""

MAIN_HTML="""<!DOCTYPE html><html><head><meta name=viewport content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"><style>
:root{--bg:#f6f6f6;--card:#fff;--text:#000;--sec:#efefef;--border:#e5e5e5}
body.dark{--bg:#000;--card:#111;--text:#fff;--sec:#222;--border:#222}
body{background:var(--bg);color:var(--text);font-family:-apple-system,sans-serif;margin:0}
.top{position:fixed;top:0;left:0;right:0;background:var(--card);padding:8px 10px;display:flex;align-items:center;justify-content:space-between;z-index:100;border-bottom:1px solid var(--border);height:50px}
.tabs{position:fixed;top:50px;left:0;right:0;background:var(--card);display:flex;z-index:99;border-bottom:1px solid var(--border);height:50px}
.tab{flex:1;display:flex;align-items:center;justify-content:center;font-weight:bold;color:#888;cursor:pointer;border-bottom:3px solid transparent}
.tab.active{color:var(--text);border-color:var(--text)}
.content{margin-top:100px;padding-bottom:160px}
.story-bar{display:flex;gap:12px;overflow-x:auto;padding:12px;background:var(--card)}
.s-item{text-align:center;min-width:68px;cursor:pointer}
.s-ring{width:62px;height:62px;border-radius:50%;background:#000;display:flex;align-items:center;justify-content:center;color:#fff;border:3px solid #ffcc00;overflow:hidden}
.s-ring img{width:100%;height:100%;object-fit:cover}
.card{background:var(--card);margin:8px;padding:12px;border-radius:16px;border:1px solid var(--border)}
.pic{width:32px;height:32px;border-radius:50%;background:#000;color:#fff;display:flex;align-items:center;justify-content:center;overflow:hidden}
.pic img{width:100%;height:100%;object-fit:cover}
.onlineDot{width:10px;height:10px;background:#00c853;border-radius:50%;display:inline-block}
.offlineDot{width:10px;height:10px;background:#999;border-radius:50%;display:inline-block}
.badge{background:red;color:#fff;border-radius:10px;padding:2px 6px;font-size:11px;margin-left:6px}
.replyBox{border-left:3px solid #ffcc00;background:#fff8e1;padding:6px;border-radius:8px;font-size:12px;margin-bottom:4px;color:#000}
.chat-bar{position:fixed;bottom:0;left:0;right:0;background:var(--card);padding:10px;display:flex;gap:8px;border-top:1px solid var(--border);z-index:50}
.pill{flex:1;background:#e9e9e9;border:none;border-radius:25px;padding:12px 16px}
.yellow{background:#ffcc00;border:none;border-radius:25px;padding:0 18px;height:44px;font-weight:800}
.friend-btn{padding:6px 12px;border-radius:20px;border:none;font-weight:700;font-size:12px}
.f-add{background:#ffcc00}.f-pending{background:#ddd}.f-friends{background:#00c851;color:#fff}
</style></head><body>
<div class=top><div style="font-weight:900;color:#c9a227">PROVE AM</div><div class=pic id=topPic onclick="openProfile()">J</div></div>
<div class=tabs><div class=tab active id=tStories onclick="switchTab('stories')">Stories</div><div class=tab id=tPost onclick="switchTab('post')">Post</div><div class=tab id=tChat onclick="switchTab('chat')">Chat</div><div class=tab id=tSearch onclick="switchTab('search')">Search</div></div>
<div class=content>
<div id=storiesDiv><div class=story-bar id=storyBar></div><div class=card><input type=file id=storyFile accept="image/*,video/*" style="display:none"><button onclick="document.getElementById('storyFile').click()" style="width:100%;padding:10px;background:#222;color:#fff;border-radius:10px;border:none">📷 Add Story - Friends can view (once chatting)</button><textarea id=storyCaption placeholder="Caption"></textarea><button onclick="uploadStory()" style="width:100%;background:#ffcc00;padding:12px;border:none;border-radius:10px;margin-top:8px">SEND STORY</button><p id=storyMsg></p></div></div>
<div id=postDiv style=display:none><div class=card><textarea id=postText placeholder="What's up?"></textarea><input type=file id=postFile accept="image/*,video/*" style="display:none"><button onclick="document.getElementById('postFile').click()">📎 Pic</button><button onclick="createPost()" style="background:#ffcc00;padding:10px;width:100%;border:none;border-radius:10px;margin-top:8px">SEND POST</button><p id=postMsg></p></div><div id=postsList></div></div>
<div id=chatDiv style=display:none><div id=chatUsers></div><div id=chatBox style=display:none></div></div>
<div id=searchDiv style=display:none class=card><input id=searchUsersInput placeholder="Search" oninput="searchUsers()"><div id=searchResults></div><h4>Requests <span id=reqCount></span></h4><div id=friendRequests></div><h4>Friends</h4><div id=myFriendsList></div></div>
<div id=profileDiv style=display:none class=card><div class=pic style="width:90px;height:90px;margin:auto" id=profilePicBig>J</div><p id=profileName style="text-align:center"></p><input type=file id=profilePicInput accept="image/*" style="display:none"><button onclick="document.getElementById('profilePicInput').click()">Pick Pic</button><button onclick="uploadProfilePic()" style="background:#ffcc00;padding:10px;width:100%;border:none;border-radius:10px">Update Pic - stays after redeploy</button><p id=profileMsg></p></div>
</div>
<script>
let curUser='',chatWith='',allUsers=[],profiles={},selectedStoryFile=null,selectedPostFile=null,selectedChatFile=null,selectedProfileFile=null,replyToText='';
async function loadMe(){let r=await fetch('/api/me');let d=await r.json();curUser=d.username;document.getElementById('profileName').innerText=curUser;loadProfiles();ping();setInterval(ping,15000);}
function ping(){fetch('/api/status/ping',{method:'POST'});}
function switchTab(t){document.querySelectorAll('.tab').forEach(e=>e.classList.remove('active'));document.getElementById('t'+t.charAt(0).toUpperCase()+t.slice(1)).classList.add('active');document.getElementById('storiesDiv').style.display=t=='stories'?'block':'none';document.getElementById('postDiv').style.display=t=='post'?'block':'none';document.getElementById('chatDiv').style.display=t=='chat'?'block':'none';document.getElementById('searchDiv').style.display=t=='search'?'block':'none';document.getElementById('profileDiv').style.display='none';if(t=='stories')loadStories();if(t=='post')loadPosts();if(t=='chat')loadChatUsers();if(t=='search'){searchUsers();loadFriendRequests();loadMyFriends();}}
async function loadProfiles(){let r=await fetch('/api/users');let u=await r.json();allUsers=u;u.forEach(x=>profiles[x.username]=x.pic_url);let url=profiles[curUser];if(url){document.getElementById('topPic').innerHTML=`<img src="${url}">`;document.getElementById('profilePicBig').innerHTML=`<img src="${url}" style="width:100%;height:100%;object-fit:cover">`;}}
document.getElementById('storyFile').addEventListener('change',e=>{selectedStoryFile=e.target.files[0];});
document.getElementById('postFile').addEventListener('change',e=>{selectedPostFile=e.target.files[0];});
document.getElementById('profilePicInput').addEventListener('change',e=>{selectedProfileFile=e.target.files[0];});
async function uploadStory(){if(!selectedStoryFile){alert('pick');return}let fd=new FormData();fd.append('media',selectedStoryFile);fd.append('text',document.getElementById('storyCaption').value);document.getElementById('storyMsg').innerText='Uploading permanent...';let r=await fetch('/api/story',{method:'POST',body:fd});let d=await r.json();document.getElementById('storyMsg').innerText=d.ok?'✅ Story posted - friends can view, stays after redeploy':'Failed '+d.error;if(d.ok)loadStories();}
async function loadStories(){let r=await fetch('/api/stories');let s=await r.json();let h='';s.forEach(st=>{h+=`<div class=card><b>${st.username}</b> ${st.text||''}${st.media_url?`<br><img src="${st.media_url}" style="width:100%">`:''}</div>`;});document.getElementById('storyBar').innerHTML=h||'No stories - add friends first';}
async function createPost(){let fd=new FormData();fd.append('text',document.getElementById('postText').value);if(selectedPostFile)fd.append('media',selectedPostFile);document.getElementById('postMsg').innerText='Posting permanent...';let r=await fetch('/api/post',{method:'POST',body:fd});let d=await r.json();document.getElementById('postMsg').innerText=d.ok?'✅ Posted stays':'Failed '+d.error;if(d.ok)loadPosts();}
async function loadPosts(){let r=await fetch('/api/posts');let p=await r.json();let h='';p.forEach(x=>{h+=`<div class=card><b>${x.username}</b> ${x.text||''}${x.media_url?`<br><img src="${x.media_url}" style="width:100%">`:''}</div>`;});document.getElementById('postsList').innerHTML=h;}
async function loadChatUsers(){let r=await fetch('/api/friends/list');let friends=await r.json();let h='';for(let f of friends){let uname=f.friend;let sRes=await fetch('/api/status/get?user='+uname);let st=await sRes.json();let online=st.online?'<span class=onlineDot></span> online':'<span class=offlineDot></span> offline';let uRes=await fetch('/api/messages/unread_count?with='+uname);let uc=await uRes.json();let badge=uc.count>0?`<span class=badge>${uc.count} unread</span>`:'';h+=`<div class=card onclick="openChat('${uname}')"><b>${uname}</b> ${online} ${badge}</div>`;}document.getElementById('chatUsers').innerHTML=h||'No friends - add in Search (needs approval)';}
async function openChat(u){chatWith=u;document.getElementById('chatUsers').style.display='none';let box=document.getElementById('chatBox');box.style.display='block';fetch('/api/messages/mark_read',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({with:u})});let sRes=await fetch('/api/status/get?user='+u);let s=await sRes.json();let online=s.online?'<span class=onlineDot></span> online':'<span class=offlineDot></span> offline';box.innerHTML=`<button onclick="backChat()">← ${u} ${online}</button><div id=msgs></div><div id=replyPreview style="display:none;background:#fff8e1;padding:6px"></div><div class=chat-bar><input id=chatText placeholder="Type..."><input type=file id=chatFileHidden style="display:none"><button onclick="document.getElementById('chatFileHidden').click()">📎</button><button onclick="sendMsg()" class=yellow>Send</button></div>`;document.getElementById('chatFileHidden').addEventListener('change',e=>{selectedChatFile=e.target.files[0];});loadMsgs();}
function backChat(){chatWith='';document.getElementById('chatBox').style.display='none';document.getElementById('chatUsers').style.display='block';loadChatUsers();}
async function loadMsgs(){if(!chatWith)return;let r=await fetch('/api/messages?with='+chatWith);let m=await r.json();let h='';m.forEach(x=>{let isMe=x.sender==curUser;let tick=isMe?(x.read?'✓✓ read':'✓ sent'):'';let reply=x.reply_to?`<div class=replyBox>${x.reply_to}</div>`:'';h+=`<div style="margin:8px;text-align:${isMe?'right':'left'}"><span style="background:${isMe?'#000':'#eee'};color:${isMe?'#fff':'#000'};padding:10px;border-radius:16px;display:inline-block;cursor:pointer" onclick="setReply('${(x.text||'').replace(/'/g,'').slice(0,30)}')">${reply}${x.text||''}${x.media_url?`<br><img src="${x.media_url}" style="max-width:150px">`:''}<br><small>${tick}</small></span></div>`;});document.getElementById('msgs').innerHTML=h;}
function setReply(t){replyToText=t;let p=document.getElementById('replyPreview');p.style.display='block';p.innerHTML=`Reply to: ${t} <button onclick="cancelReply()">x</button>`;}
function cancelReply(){replyToText='';document.getElementById('replyPreview').style.display='none';}
async function sendMsg(){let t=document.getElementById('chatText').value;let fd=new FormData();fd.append('receiver',chatWith);fd.append('text',t);fd.append('reply_to',replyToText);if(selectedChatFile)fd.append('media',selectedChatFile);document.getElementById('chatText').value='';cancelReply();selectedChatFile=null;await fetch('/api/send',{method:'POST',body:fd});loadMsgs();}
async function searchUsers(){let q=document.getElementById('searchUsersInput').value;let r=await fetch('/api/search?q='+q);let users=await r.json();let h='';users.forEach(u=>{if(u.username==curUser)return;let btn=u.friend_status=='none'?`<button class=friend-btn f-add onclick="addFriend('${u.username}')">+Add (needs approval)</button>`:u.friend_status=='friends'?'<span class=friend-btn f-friends>✓ Friends (can view story)</span>':`<span class=friend-btn f-pending>${u.friend_status}</span>`;h+=`<div class=card><b>${u.username}</b> ${btn}</div>`;});document.getElementById('searchResults').innerHTML=h;}
async function addFriend(u){await fetch('/api/friend/request',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({to:u})});searchUsers();}
async function loadFriendRequests(){let r=await fetch('/api/friend/requests');let reqs=await r.json();document.getElementById('reqCount').innerText=reqs.length;let h='';reqs.forEach(x=>{h+=`<div class=card><b>${x.sender}</b> <button onclick="acceptFriend('${x.sender}')">Accept</button> <button onclick="declineFriend('${x.sender}')">Decline</button></div>`;});document.getElementById('friendRequests').innerHTML=h;}
async function acceptFriend(u){await fetch('/api/friend/accept',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({from:u})});loadFriendRequests();loadMyFriends();loadChatUsers();}
async function declineFriend(u){await fetch('/api/friend/decline',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({from:u})});loadFriendRequests();}
async function loadMyFriends(){let r=await fetch('/api/friends/list');let f=await r.json();let h='';f.forEach(x=>{h+=`<div class=card><b>${x.friend}</b> ✓ Friends</div>`;});document.getElementById('myFriendsList').innerHTML=h;}
function openProfile(){document.getElementById('profileDiv').style.display='block';}
async function uploadProfilePic(){if(!selectedProfileFile){alert('pick pic');return}let fd=new FormData();fd.append('media',selectedProfileFile);document.getElementById('profileMsg').innerText='Uploading permanent...';let r=await fetch('/api/profile/pic',{method:'POST',body:fd});let d=await r.json();document.getElementById('profileMsg').innerText=d.ok?'✅ Pic stays after redeploy':'Failed';if(d.ok)loadProfiles();}
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
    me=session.get('username'); q=(request.args.get('q','') or '').strip().lower()
    conn=get_conn(); c=conn.cursor()
    if q:
        like=f"%{q}%"
        c.execute("SELECT username,pic_url FROM profiles WHERE LOWER(username) LIKE %s LIMIT 30" if USE_POSTGRES else "SELECT username,pic_url FROM profiles WHERE LOWER(username) LIKE? LIMIT 30",(like,))
    else:
        c.execute("SELECT username,pic_url FROM profiles LIMIT 30")
    users=c.fetchall()
    c.execute("SELECT sender,receiver,status FROM friends WHERE sender=%s OR receiver=%s" if USE_POSTGRES else "SELECT sender,receiver,status FROM friends WHERE sender=? OR receiver=?",(me,me))
    fr=c.fetchall(); status_map={}
    for s,r,st in fr:
        status_map[r if s==me else s]= 'friends' if st=='accepted' else 'pending_sent' if s==me else 'pending_received'
    out=[{"username":u,"pic_url":p or "","friend_status":status_map.get(u,'none')} for u,p in users if u!=me]
    conn.close(); return jsonify(out)

@app.route('/api/friend/request', methods=['POST'])
def api_friend_request():
    me=session.get('username'); to=request.json.get('to')
    if not to or to==me: return jsonify({"ok":False})
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT 1 FROM friends WHERE (sender=%s AND receiver=%s) OR (sender=%s AND receiver=%s)" if USE_POSTGRES else "SELECT 1 FROM friends WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?)",(me,to,to,me))
    if c.fetchone(): conn.close(); return jsonify({"ok":False,"error":"exists"})
    c.execute("INSERT INTO friends (sender,receiver,status,created_at) VALUES (%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO friends (sender,receiver,status,created_at) VALUES (?,?,?,?)",(me,to,'pending',datetime.now().isoformat()))
    c.execute("INSERT INTO notifications (username,type,from_user,text,created_at) VALUES (%s,%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO notifications (username,type,from_user,text,created_at) VALUES (?,?,?,?,?)",(to,'friend_request',me,f'{me} sent request - needs approval',datetime.now().isoformat()))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/api/friend/accept', methods=['POST'])
def api_friend_accept():
    me=session.get('username'); frm=request.json.get('from')
    conn=get_conn(); c=conn.cursor()
    c.execute("UPDATE friends SET status='accepted' WHERE sender=%s AND receiver=%s" if USE_POSTGRES else "UPDATE friends SET status='accepted' WHERE sender=? AND receiver=?",(frm,me))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/api/friend/decline', methods=['POST'])
def api_friend_decline():
    me=session.get('username'); frm=request.json.get('from')
    conn=get_conn(); c=conn.cursor()
    c.execute("DELETE FROM friends WHERE sender=%s AND receiver=%s" if USE_POSTGRES else "DELETE FROM friends WHERE sender=? AND receiver=?",(frm,me))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/api/friend/requests')
def api_friend_requests():
    me=session.get('username'); conn=get_conn(); c=conn.cursor()
    c.execute("SELECT sender FROM friends WHERE receiver=%s AND status='pending'" if USE_POSTGRES else "SELECT sender FROM friends WHERE receiver=? AND status='pending'",(me,))
    rows=c.fetchall(); conn.close(); return jsonify([{"sender":r[0]} for r in rows])

@app.route('/api/friends/list')
def api_friends_list():
    me=session.get('username'); conn=get_conn(); c=conn.cursor()
    c.execute("SELECT sender,receiver FROM friends WHERE (sender=%s OR receiver=%s) AND status='accepted'" if USE_POSTGRES else "SELECT sender,receiver FROM friends WHERE (sender=? OR receiver=?) AND status='accepted'",(me,me))
    rows=c.fetchall(); conn.close(); return jsonify([{"friend":r if s==me else s} for s,r in rows])

@app.route('/api/status/ping', methods=['POST'])
def api_status_ping():
    import time; me=session.get('username'); now=time.time()
    conn=get_conn(); c=conn.cursor()
    if USE_POSTGRES: c.execute("INSERT INTO user_status (username,last_seen) VALUES (%s,%s) ON CONFLICT (username) DO UPDATE SET last_seen=%s",(me,now,now))
    else: c.execute("INSERT OR REPLACE INTO user_status (username,last_seen) VALUES (?,?)",(me,now))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/api/status/get')
def api_status_get():
    import time; u=request.args.get('user'); conn=get_conn(); c=conn.cursor()
    c.execute("SELECT last_seen FROM user_status WHERE username=%s" if USE_POSTGRES else "SELECT last_seen FROM user_status WHERE username=?",(u,))
    row=c.fetchone(); conn.close()
    if not row: return jsonify({"online":False})
    return jsonify({"online": (time.time()-float(row[0]))<40})

@app.route('/api/posts')
def api_posts():
    conn=get_conn(); c=conn.cursor(); c.execute("SELECT id,username,text,media_url FROM posts ORDER BY id DESC LIMIT 50"); rows=c.fetchall(); conn.close()
    return jsonify([{"id":r[0],"username":r[1],"text":r[2],"media_url":r[3]} for r in rows])

@app.route('/api/post', methods=['POST'])
def api_post():
    me=session.get('username'); txt=request.form.get('text','')[:500]; f=request.files.get('media'); url=upload_to_cloud(f) if f and f.filename else ''
    if not txt and not url: return jsonify({"ok":False,"error":"empty"}),400
    conn=get_conn(); c=conn.cursor()
    c.execute("INSERT INTO posts (username,text,media_url,created_at) VALUES (%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO posts (username,text,media_url,created_at) VALUES (?,?,?,?)",(me,txt,url,datetime.now().isoformat()))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/api/stories')
def api_stories():
    me=session.get('username'); conn=get_conn(); c=conn.cursor(); now=datetime.now().isoformat()
    c.execute("SELECT sender,receiver FROM friends WHERE (sender=%s OR receiver=%s) AND status='accepted'" if USE_POSTGRES else "SELECT sender,receiver FROM friends WHERE (sender=? OR receiver=?) AND status='accepted'",(me,me))
    fr=c.fetchall(); friends=set([me]+[r if s==me else s for s,r in fr])
    c.execute("SELECT id,username,media_url,text FROM stories WHERE expires_at>%s ORDER BY id DESC" if USE_POSTGRES else "SELECT id,username,media_url,text FROM stories WHERE expires_at>? ORDER BY id DESC",(now,))
    rows=c.fetchall(); out=[{"id":r[0],"username":r[1],"media_url":r[2],"text":r[3]} for r in rows if r[1] in friends]
    conn.close(); return jsonify(out)

@app.route('/api/story', methods=['POST'])
def api_story():
    me=session.get('username'); f=request.files.get('media'); txt=request.form.get('text','')[:200]
    if not f or not f.filename: return jsonify({"ok":False,"error":"no file"}),400
    url=upload_to_cloud(f)
    if not url: return jsonify({"ok":False,"error":"Cloudinary keys missing - add in Render Environment"}),500
    conn=get_conn(); c=conn.cursor(); now=datetime.now(); exp=now+timedelta(hours=24)
    c.execute("INSERT INTO stories (username,media_url,text,created_at,expires_at) VALUES (%s,%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO stories (username,media_url,text,created_at,expires_at) VALUES (?,?,?,?,?)",(me,url,txt,now.isoformat(),exp.isoformat()))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/api/profile/pic', methods=['POST'])
def api_profile_pic():
    me=session.get('username'); f=request.files.get('media'); url=upload_to_cloud(f)
    if not url: return jsonify({"ok":False,"error":"no file"}),400
    conn=get_conn(); c=conn.cursor()
    c.execute("UPDATE profiles SET pic_url=%s WHERE username=%s" if USE_POSTGRES else "UPDATE profiles SET pic_url=? WHERE username=?",(url,me)); conn.commit(); conn.close()
    return jsonify({"ok":True,"url":url})

@app.route('/api/messages')
def api_messages():
    me=session.get('username'); other=request.args.get('with',''); conn=get_conn(); c=conn.cursor()
    c.execute("SELECT id,sender,text,media_url,reply_to,read FROM messages WHERE (sender=%s AND receiver=%s) OR (sender=%s AND receiver=%s) ORDER BY id ASC" if USE_POSTGRES else "SELECT id,sender,text,media_url,reply_to,read FROM messages WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) ORDER BY id ASC",(me,other,other,me))
    rows=c.fetchall(); conn.close()
    return jsonify([{"id":r[0],"sender":r[1],"text":r[2],"media_url":r[3],"reply_to":r[4],"read":r[5]} for r in rows])

@app.route('/api/messages/unread_count')
def api_unread_count():
    me=session.get('username'); other=request.args.get('with',''); conn=get_conn(); c=conn.cursor()
    c.execute("SELECT COUNT(*) FROM messages WHERE receiver=%s AND sender=%s AND read=0" if USE_POSTGRES else "SELECT COUNT(*) FROM messages WHERE receiver=? AND sender=? AND read=0",(me,other))
    cnt=c.fetchone()[0]; conn.close(); return jsonify({"count":cnt})

@app.route('/api/messages/mark_read', methods=['POST'])
def api_mark_read():
    me=session.get('username'); other=request.json.get('with'); conn=get_conn(); c=conn.cursor()
    c.execute("UPDATE messages SET read=1 WHERE receiver=%s AND sender=%s" if USE_POSTGRES else "UPDATE messages SET read=1 WHERE receiver=? AND sender=?",(me,other))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/api/send', methods=['POST'])
def api_send():
    me=session.get('username'); other=request.form.get('receiver',''); txt=request.form.get('text','')[:500]; reply_to=request.form.get('reply_to','')[:100]; f=request.files.get('media'); url=upload_to_cloud(f) if f and f.filename else ''
    if not txt and not url: return jsonify({"ok":False,"error":"empty"}),400
    conn=get_conn(); c=conn.cursor()
    c.execute("INSERT INTO messages (sender,receiver,text,media_url,reply_to,read,created_at) VALUES (%s,%s,%s,%s,%s,0,%s)" if USE_POSTGRES else "INSERT INTO messages (sender,receiver,text,media_url,reply_to,read,created_at) VALUES (?,?,?,?,?,0,?)",(me,other,txt,url,reply_to,datetime.now().isoformat()))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/api/notifications/count')
def api_notifications_count():
    me=session.get('username'); conn=get_conn(); c=conn.cursor()
    c.execute("SELECT COUNT(*) FROM notifications WHERE username=%s AND is_read=0" if USE_POSTGRES else "SELECT COUNT(*) FROM notifications WHERE username=? AND is_read=0",(me,))
    cnt=c.fetchone()[0]; conn.close(); return jsonify({"count":cnt})

@app.route('/static/uploads/<path:filename>')
def uploads(filename): return send_from_directory('static/uploads', filename)

if __name__=='__main__':
    port=int(os.environ.get("PORT",5000)); app.run(host='0.0.0.0',port=port)
