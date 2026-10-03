import os
from flask import Flask, request, jsonify, session, render_template_string, redirect, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import sqlite3
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET","prove-am-jerrick-2024")
DB_URL = os.environ.get("DATABASE_URL","")
USE_POSTGRES = DB_URL.startswith("postgres")
def get_conn():
    if USE_POSTGRES:
        try:
            import psycopg2
            return psycopg2.connect(DB_URL,connect_timeout=10)
        except:
            import psycopg
            return psycopg.connect(DB_URL)
    return sqlite3.connect("app.db")
def init_db():
    conn=get_conn(); c=conn.cursor()
    if USE_POSTGRES:
        c.execute("CREATE TABLE IF NOT EXISTS auth (username TEXT PRIMARY KEY, password TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS profiles (username TEXT PRIMARY KEY, pic_url TEXT, bio TEXT, last_seen TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS posts (id SERIAL PRIMARY KEY, username TEXT, text TEXT, media_url TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS post_likes (post_id INT, username TEXT, PRIMARY KEY(post_id,username))")
        c.execute("CREATE TABLE IF NOT EXISTS comments (id SERIAL PRIMARY KEY, post_id INT, username TEXT, text TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS comment_likes (comment_id INT, username TEXT, PRIMARY KEY(comment_id,username))")
        c.execute("CREATE TABLE IF NOT EXISTS messages (id SERIAL PRIMARY KEY, sender TEXT, receiver TEXT, text TEXT, media_url TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS msg_reacts (msg_id INT, username TEXT, emoji TEXT, PRIMARY KEY(msg_id,username))")
        c.execute("CREATE TABLE IF NOT EXISTS stories (id SERIAL PRIMARY KEY, username TEXT, media_url TEXT, text TEXT, created_at TEXT, expires_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS story_views (story_id INT, viewer TEXT, PRIMARY KEY(story_id,viewer))")
        c.execute("CREATE TABLE IF NOT EXISTS streaks (user1 TEXT, user2 TEXT, count INT, last_date TEXT, PRIMARY KEY(user1,user2))")
        c.execute("CREATE TABLE IF NOT EXISTS friends (user1 TEXT, user2 TEXT, PRIMARY KEY(user1,user2))")
    else:
        c.execute("CREATE TABLE IF NOT EXISTS auth (username TEXT PRIMARY KEY, password TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS profiles (username TEXT PRIMARY KEY, pic_url TEXT, bio TEXT, last_seen TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, text TEXT, media_url TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS post_likes (post_id INT, username TEXT, PRIMARY KEY(post_id,username))")
        c.execute("CREATE TABLE IF NOT EXISTS comments (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INT, username TEXT, text TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS comment_likes (comment_id INT, username TEXT, PRIMARY KEY(comment_id,username))")
        c.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, receiver TEXT, text TEXT, media_url TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS msg_reacts (msg_id INT, username TEXT, emoji TEXT, PRIMARY KEY(msg_id,username))")
        c.execute("CREATE TABLE IF NOT EXISTS stories (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, media_url TEXT, text TEXT, created_at TEXT, expires_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS story_views (story_id INT, viewer TEXT, PRIMARY KEY(story_id,viewer))")
        c.execute("CREATE TABLE IF NOT EXISTS streaks (user1 TEXT, user2 TEXT, count INT, last_date TEXT, PRIMARY KEY(user1,user2))")
        c.execute("CREATE TABLE IF NOT EXISTS friends (user1 TEXT, user2 TEXT, PRIMARY KEY(user1,user2))")
    conn.commit(); conn.close()
init_db()
typing_map = {}
LOGIN_HTML = """<!DOCTYPE html><html><head><meta name=viewport content="width=device-width,initial-scale=1">
<style>body{background:#0a0a0a;color:#fff;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}
.box{background:#1a1a1a;padding:30px;border-radius:20px;width:310px;text-align:center}
input{width:100%;padding:12px;margin:8px 0;border-radius:10px;border:none;background:#2a2a2a;color:#fff;box-sizing:border-box}
button{width:100%;padding:12px;background:#ffcc00;color:#000;border:none;border-radius:10px;font-weight:bold;margin-top:10px;cursor:pointer}
.logo{width:80px;height:80px;border-radius:50%;object-fit:cover;margin-bottom:10px}
h2{color:#ffcc00;margin:6px 0}
.brand{font-size:11px;color:#888;margin-top:12px}</style></head><body>
<div class=box>
<img src=/logo.jpg onerror="this.src='/logo-full.jpg'" class=logo>
<h2>PROVE AM - No Cap</h2>
<input id=u placeholder=Username>
<input id=p type=password placeholder=Password>
<button onclick=login()>Login</button>
<button onclick=signup()>Sign Up</button>
<p id=msg style=color:#ff4444></p>
<div class=brand>Built by Jerrick 🇬🇭<br>Low Data Mode ON</div>
</div>
<script>
async function login(){
 let u=document.getElementById('u').value.trim();
 let p=document.getElementById('p').value;
 let r=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})});
 let d=await r.json(); if(d.ok) location.href='/'; else document.getElementById('msg').innerText=d.error;
}
async function signup(){
 let u=document.getElementById('u').value.trim();
 let p=document.getElementById('p').value;
 let r=await fetch('/signup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})});
 let d=await r.json(); if(d.ok) location.href='/'; else document.getElementById('msg').innerText=d.error;
}
</script></body></html>"""
MAIN_HTML = """<!DOCTYPE html><html><head><meta name=viewport content="width=device-width,initial-scale=1">
<style>
:root{--bg:#000;--card:#1a1a1a;--card2:#2a2a2a;--txt:#fff;--accent:#ffcc00}
.light{--bg:#f5f5f5;--card:#fff;--card2:#eee;--txt:#000}
body{background:var(--bg);color:var(--txt);font-family:sans-serif;margin:0;transition:.3s}
.top{position:fixed;top:0;left:0;right:0;background:var(--card);padding:10px 12px;display:flex;justify-content:space-between;align-items:center;z-index:100;border-bottom:1px solid #222}
.top img.logo{width:36px;height:36px;border-radius:50%}
.tabs{position:fixed;top:56px;left:0;right:0;background:var(--card);display:flex;z-index:99}
.tab{flex:1;padding:12px;text-align:center;cursor:pointer;border-bottom:2px solid transparent;font-size:14px}
.tab.active{border-color:var(--accent);color:var(--accent);font-weight:bold}
.content{margin-top:110px;padding:10px;padding-bottom:90px}
.card{background:var(--card);margin:10px 0;padding:12px;border-radius:16px}
.card img,.card video{max-width:100%;border-radius:12px;margin-top:8px}
.post-actions{display:flex;gap:14px;margin-top:8px;align-items:center}
.like{cursor:pointer;font-size:20px}.like.liked{color:red}
input,textarea{width:100%;background:var(--card2);color:var(--txt);border:none;border-radius:10px;padding:10px;margin:6px 0;box-sizing:border-box}
button{background:var(--accent);color:#000;border:none;padding:9px 14px;border-radius:10px;font-weight:bold;cursor:pointer}
.user-row{background:var(--card);padding:10px;border-radius:12px;margin:6px 0;display:flex;align-items:center;justify-content:space-between;cursor:pointer}
.online{width:8px;height:8px;background:#0f0;border-radius:50%;display:inline-block}
.offline{background:#666}
.story-bar{display:flex;gap:10px;overflow-x:auto;padding:8px 0}
.story-item{text-align:center;cursor:pointer;min-width:64px}
.story-item img{width:58px;height:58px;border-radius:50%;border:3px solid var(--accent);object-fit:cover}
.viewer-modal{position:fixed;top:0;left:0;right:0;bottom:0;background:#000;z-index:200;display:none;flex-direction:column}
.viewer-top{padding:10px;display:flex;justify-content:space-between;align-items:center;background:#111}
.brand{font-size:10px;color:#888;text-align:center;padding:8px}
.low-badge{background:#ffcc00;color:#000;font-size:10px;padding:2px 6px;border-radius:6px}
</style></head><body>
<div class=top>
<div style="display:flex;align-items:center;gap:8px"><img src="/logo.jpg" onerror="this.src='/logo-full.jpg'" class=logo><b style=color:var(--accent)>PROVE AM</b><span class=low-badge>LOW DATA</span></div>
<div style="display:flex;align-items:center;gap:8px"><img id=myPic style="width:28px;height:28px;border-radius:50%;display:none"><span id=me></span>
<button onclick="toggleTheme()" style="padding:4px 8px">☀️/🌙</button>
<button onclick=logout() style="padding:4px 8px">Out</button></div>
</div>
<div class=tabs>
<div class=tab active id=tStories onclick="showTab('stories')">Stories</div>
<div class=tab id=tPost onclick="showTab('post')">Feed</div>
<div class=tab id=tChat onclick="showTab('chat')">Chat</div>
<div class=tab id=tProfile onclick="showTab('profile')">Me</div>
</div>
<div class=content>
<div id=storiesDiv>
<div class=story-bar id=storyBar></div>
<div id=storiesList></div>
</div>
<div id=postDiv style=display:none>
<div class=card>
<textarea id=postText placeholder="What's up? Prove Am..."></textarea>
<input type=file id=postFile accept="image/*,video/*" multiple>
<button onclick=createPost()>Post (2+ allowed)</button>
<div style="margin-top:8px">
<button onclick=document.getElementById('storyFile').click() style="background:#222;color:#fff">+ Story (24h)</button>
<input type=file id=storyFile accept="image/*,video/*" style=display:none onchange=createStory()>
</div>
</div>
<div id=postsList></div>
</div>
<div id=chatDiv style=display:none>
<input id=searchChat placeholder="Search users..." oninput=filterChat() style="margin-bottom:8px">
<div id=chatUsers></div>
<div id=chatBox style=display:none></div>
</div>
<div id=profileDiv style=display:none>
<div class=card style=text-align:center>
<img id=profilePicLarge src="/logo.jpg" style="width:90px;height:90px;border-radius:50%">
<h3 id=profileName></h3>
<input type=file id=picFile accept="image/*" onchange=uploadPic()>
<p>Online status auto</p>
<div class=brand>Built by Jerrick 🇬🇭 - Prove Am No Cap<br>Low Data Mode: Forced ON (no autoplay)<br>Your logo: logo.jpg / logo-full.jpg used</div>
</div>
</div>
</div>
<div class=viewer-modal id=viewerModal>
<div class=viewer-top><span id=viewerUser></span><span><span id=viewerCount></span> <button onclick=closeViewer()>✕</button></span></div>
<div style="flex:1;display:flex;align-items:center;justify-content:center"><img id=viewerMedia style="max-width:100%;max-height:80vh;display:none"><video id=viewerVideo controls style="max-width:100%;max-height:80vh;display:none"></video></div>
<div style="padding:10px;display:flex;gap:8px"><input id=replyStoryInput placeholder="Reply to story..."><button onclick=replyStory()>Send to Chat</button><button onclick=nextStory()>Next →</button></div>
</div>
<script>
let curUser=''; let chatWith=''; let stories=[]; let storyIdx=0;
let lowData=true;
function toggleTheme(){ document.body.classList.toggle('light'); localStorage.setItem('theme', document.body.classList.contains('light')?'light':'dark'); }
if(localStorage.getItem('theme')=='light') document.body.classList.add('light');
async function loadMe(){
 let r=await fetch('/api/me'); let d=await r.json(); curUser=d.username; document.getElementById('me').innerText=curUser; document.getElementById('profileName').innerText=curUser;
 if(d.pic){ document.getElementById('myPic').src=d.pic; document.getElementById('myPic').style.display='block'; document.getElementById('profilePicLarge').src=d.pic; }
 setInterval(updateOnline,15000); updateOnline();
}
function updateOnline(){ fetch('/api/online',{method:'POST'}); }
function showTab(t){
 document.querySelectorAll('.tab').forEach(e=>e.classList.remove('active'));
 document.getElementById('t'+t.charAt(0).toUpperCase()+t.slice(1)).classList.add('active');
 ['stories','post','chat','profile'].forEach(x=>document.getElementById(x+'Div').style.display=x==t?'block':'none');
 if(t=='stories') loadStories(); if(t=='post') loadPosts(); if(t=='chat') loadChatUsers();
}
async function loadStories(){
 let r=await fetch('/api/stories'); stories=await r.json();
 let bar=document.getElementById('storyBar'); let h='';
 stories.forEach((s,i)=>{
   h+=`<div class=story-item onclick="openViewer(${i})"><img src="${s.media_url}" loading=lazy><br><small>${s.username}</small><br><small>👁️${s.views||0}</small></div>`;
 });
 bar.innerHTML=h||'No stories - post one!';
}
function openViewer(i){
 storyIdx=i; let s=stories[i];
 document.getElementById('viewerModal').style.display='flex';
 document.getElementById('viewerUser').innerText=s.username;
 document.getElementById('viewerCount').innerText='👁️ '+(s.views||0)+' viewers';
 let img=document.getElementById('viewerMedia'); let vid=document.getElementById('viewerVideo');
 if(s.media_url.match(/\\.(mp4|webm|mov)$/i)){ img.style.display='none'; vid.style.display='block'; vid.src=s.media_url; if(lowData) vid.autoplay=false; }
 else{ vid.style.display='none'; img.style.display='block'; img.src=s.media_url; }
 fetch('/api/story/view',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:s.id})});
}
function closeViewer(){ document.getElementById('viewerModal').style.display='none'; document.getElementById('viewerVideo').pause(); }
function nextStory(){ if(storyIdx<stories.length-1) openViewer(storyIdx+1); else closeViewer(); }
async function replyStory(){
 let s=stories[storyIdx]; let txt=document.getElementById('replyStoryInput').value||'Replied to your story 🔥';
 await fetch('/api/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({receiver:s.username,text:txt+" [story:"+s.id+"]"})});
 document.getElementById('replyStoryInput').value=''; closeViewer(); alert('Replied in chat with '+s.username);
}
async function createStory(){
 let f=document.getElementById('storyFile').files[0]; if(!f) return;
 let fd=new FormData(); fd.append('media',f);
 let r=await fetch('/api/story',{method:'POST',body:fd}); let d=await r.json(); if(d.ok){ loadStories(); alert('Story posted 24h'); }
}
async function loadPosts(){
 let r=await fetch('/api/posts'); let posts=await r.json();
 let h='';
 posts.forEach(p=>{
   let media=''; if(p.media_url){ if(p.media_url.match(/\\.(mp4|webm|mov)$/i)) media=`<video src="${p.media_url}" controls preload=none style="max-width:100%"></video>`; else media=`<img src="${p.media_url}" loading=lazy>`; }
   let liked = p.liked? 'liked' : '';
   h+=`<div class=card><div style="display:flex;align-items:center;gap:8px"><img src="${p.pic||'/logo.jpg'}" style="width:32px;height:32px;border-radius:50%"><b>${p.username}</b> ${p.online?'<span class=online></span>':'<span class="online offline"></span>'}</div><p>${p.text||''}</p>${media}
   <div class=post-actions><span class="like ${liked}" onclick="likePost(${p.id})">${p.liked?'❤️':'🤍'} ${p.like_count||0}</span><span onclick="toggleComments(${p.id})">💬 ${p.comment_count||0}</span><span onclick="shareReply('${p.username}')">↗️ Reply</span></div>
   <div id=comments-${p.id} style=display:none><div id=commentList-${p.id}></div><input id=commentInput-${p.id} placeholder="Comment..."><button onclick="addComment(${p.id})">Send</button></div>
   <small>${p.created_at.slice(0,16)}</small></div>`;
 });
 document.getElementById('postsList').innerHTML=h;
}
async function likePost(id){ await fetch('/api/like',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:id})}); loadPosts(); }
async function toggleComments(id){
 let el=document.getElementById('comments-'+id); el.style.display=el.style.display=='none'?'block':'none';
 let r=await fetch('/api/comments?post_id='+id); let cs=await r.json();
 let h=''; cs.forEach(c=>{ h+=`<div style="padding:6px;background:var(--card2);margin:4px 0;border-radius:8px"><b>${c.username}</b>: ${c.text} <span onclick="likeComment(${c.id})" style="cursor:pointer">❤️ ${c.like_count||0}</span></div>`; });
 document.getElementById('commentList-'+id).innerHTML=h;
}
async function addComment(post_id){
 let txt=document.getElementById('commentInput-'+post_id).value; if(!txt) return;
 await fetch('/api/comment',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id,text:txt})});
 document.getElementById('commentInput-'+post_id).value=''; toggleComments(post_id); loadPosts();
}
async function likeComment(id){ await fetch('/api/comment/like',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({comment_id:id})}); }
function shareReply(user){ let idx=stories.findIndex(s=>s.username==user); if(idx>=0) openViewer(idx); }
async function createPost(){
 let files=document.getElementById('postFile').files; let text=document.getElementById('postText').value;
 if(files.length==0){ let fd=new FormData(); fd.append('text',text); await fetch('/api/post',{method:'POST',body:fd}); }
 else{ for(let f of files){ let fd=new FormData(); fd.append('text',text); fd.append('media',f); await fetch('/api/post',{method:'POST',body:fd}); text=''; } }
 document.getElementById('postText').value=''; document.getElementById('postFile').value=''; loadPosts(); alert('Posted!');
}
let allUsers=[];
async function loadChatUsers(){
 let r=await fetch('/api/users'); allUsers=await r.json(); renderChatUsers(allUsers);
}
function renderChatUsers(users){
 let h=''; users.forEach(u=>{
   if(u.username==curUser) return;
   let on = u.online?'<span class=online></span> Online':'<span class="online offline"></span> Offline';
   h+=`<div class=user-row onclick="openChat('${u.username}')"><div style="display:flex;align-items:center;gap:8px"><img src="${u.pic||'/logo.jpg'}" style="width:32px;height:32px;border-radius:50%"><div><b>${u.username}</b><br><small>${on} ${u.streak?'🔥'+u.streak:''}</small></div></div><div>Chat</div></div>`;
 });
 document.getElementById('chatUsers').innerHTML=h;
}
function filterChat(){
 let q=document.getElementById('searchChat').value.toLowerCase();
 let f=allUsers.filter(u=>u.username.toLowerCase().includes(q));
 renderChatUsers(f);
}
async function openChat(username){
 chatWith=username;
 document.getElementById('chatUsers').style.display='none';
 document.getElementById('searchChat').style.display='none';
 let box=document.getElementById('chatBox'); box.style.display='block';
 box.innerHTML=`<button onclick="backChat()">← Back ${username} <span id=typingStatus></span></button><div id=msgs style="margin-top:10px;margin-bottom:70px"></div>
 <div style="position:fixed;bottom:0;left:0;right:0;background:var(--card);padding:10px;display:flex;gap:6px;align-items:center">
 <input id=chatText placeholder="Message" style="flex:1" oninput=sendTyping()>
 <input type=file id=chatFile accept="image/*,video/*,audio/*" style="width:70px">
 <button onclick="startAudio()" style="background:#222;color:#fff">🎤</button>
 <button onclick=sendMsg()>Send</button></div>`;
 loadMsgs();
}
function backChat(){ chatWith=''; document.getElementById('chatBox').style.display='none'; document.getElementById('chatUsers').style.display='block'; document.getElementById('searchChat').style.display='block'; }
async function loadMsgs(){
 if(!chatWith) return;
 let r=await fetch('/api/messages?with='+chatWith); let msgs=await r.json();
 let h='';
 msgs.forEach(m=>{
   let media=''; if(m.media_url){ if(m.media_url.match(/\\.(mp4|webm|mov|mp3|m4a|ogg|wav)$/i)){ if(m.media_url.match(/\\.(mp3|m4a|ogg|wav)$/i)) media=`<br><audio src="${m.media_url}" controls style="max-width:200px"></audio>`; else media=`<br><video src="${m.media_url}" controls preload=none style="max-width:200px;border-radius:12px"></video>`; } else media=`<br><img src="${m.media_url}" loading=lazy style="max-width:200px;border-radius:12px">`; }
   let react=''; if(m.reacts) react=`<br><small>${m.reacts}</small>`;
   let isMe=m.sender==curUser;
   h+=`<div style="margin:8px 0;text-align:${isMe?'right':'left'}"><span style="background:${isMe?'#ffcc00':'var(--card2)'};color:${isMe?'#000':'var(--txt)'};padding:8px 12px;border-radius:14px;display:inline-block;max-width:70%;cursor:pointer" onclick="reactMsg(${m.id})">${m.text||''}${media}${react}</span></div>`;
 });
 document.getElementById('msgs').innerHTML=h;
 let tr=await fetch('/api/typing?with='+chatWith); let td=await tr.json(); if(td.typing) document.getElementById('typingStatus').innerText='typing...';
}
async function sendMsg(){
 let text=document.getElementById('chatText').value;
 let file=document.getElementById('chatFile').files[0];
 let fd=new FormData(); fd.append('receiver',chatWith); fd.append('text',text); if(file) fd.append('media',file);
 let r=await fetch('/api/send',{method:'POST',body:fd}); let d=await r.json(); if(d.ok){ document.getElementById('chatText').value=''; document.getElementById('chatFile').value=''; loadMsgs(); }
}
async function sendTyping(){ fetch('/api/typing',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({receiver:chatWith})}); }
async function reactMsg(id){ let e=prompt('React: ❤️ 😂 🔥 😭 🙏'); if(!e) return; await fetch('/api/react',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({msg_id:id,emoji:e})}); loadMsgs(); }
let rec; let chunks=[];
async function startAudio(){
 if(rec && rec.state=='recording'){ rec.stop(); return; }
 let stream=await navigator.mediaDevices.getUserMedia({audio:true}); rec=new MediaRecorder(stream); chunks=[];
 rec.ondataavailable=e=>chunks.push(e.data);
 rec.onstop=async()=>{
   let blob=new Blob(chunks,{type:'audio/webm'}); let fd=new FormData(); fd.append('receiver',chatWith); fd.append('media',blob,'voice.webm'); fd.append('text','🎤 Audio');
   await fetch('/api/send',{method:'POST',body:fd}); loadMsgs();
 };
 rec.start(); alert('Recording... click 🎤 again to stop');
}
async function uploadPic(){
 let f=document.getElementById('picFile').files[0]; if(!f) return;
 let fd=new FormData(); fd.append('media',f);
 let r=await fetch('/api/profile/pic',{method:'POST',body:fd}); let d=await r.json(); if(d.ok){ alert('Profile pic updated'); loadMe(); }
}
async function logout(){ await fetch('/logout'); location.href='/login'; }
loadMe(); showTab('stories');
setInterval(()=>{ if(chatWith) loadMsgs(); },2500);
</script>
</body></html>"""
@app.route('/')
def home():
    if 'username' not in session: return redirect('/login')
    return render_template_string(MAIN_HTML)
@app.route('/login', methods=['GET'])
def login_page(): return render_template_string(LOGIN_HTML)
@app.route('/login', methods=['POST'])
def login_api():
    data=request.json; u=data.get('username','').strip()[:20]; p=data.get('password','')
    conn=get_conn(); c=conn.cursor()
    if USE_POSTGRES: c.execute("SELECT password FROM auth WHERE username=%s",(u,))
    else: c.execute("SELECT password FROM auth WHERE username=?",(u,))
    row=c.fetchone(); conn.close()
    if not row or not check_password_hash(row[0],p): return jsonify({"ok":False,"error":"Wrong pass"})
    session['username']=u; return jsonify({"ok":True})
@app.route('/signup', methods=['POST'])
def signup():
    data=request.json; u=data.get('username','').strip()[:20]; p=data.get('password','')
    if len(u)<3 or len(p)<3: return jsonify({"ok":False,"error":"Min 3"})
    conn=get_conn(); c=conn.cursor()
    if USE_POSTGRES: c.execute("SELECT 1 FROM auth WHERE username=%s",(u,))
    else: c.execute("SELECT 1 FROM auth WHERE username=?",(u,))
    if c.fetchone(): conn.close(); return jsonify({"ok":False,"error":"Taken"})
    if USE_POSTGRES:
        c.execute("INSERT INTO auth VALUES (%s,%s,%s)",(u,generate_password_hash(p),datetime.now().isoformat()))
        c.execute("INSERT INTO profiles (username,pic_url,last_seen) VALUES (%s,%s,%s) ON CONFLICT (username) DO NOTHING",(u,"",datetime.now().isoformat()))
    else:
        c.execute("INSERT INTO auth VALUES (?,?,?)",(u,generate_password_hash(p),datetime.now().isoformat()))
        c.execute("INSERT OR IGNORE INTO profiles (username,pic_url,last_seen) VALUES (?,?,?)",(u,"",datetime.now().isoformat()))
    conn.commit(); conn.close(); session['username']=u; return jsonify({"ok":True})
@app.route('/api/me')
def api_me():
    u=session.get('username')
    if not u: return jsonify({"username":""})
    conn=get_conn(); c=conn.cursor()
    if USE_POSTGRES: c.execute("SELECT pic_url FROM profiles WHERE username=%s",(u,))
    else: c.execute("SELECT pic_url FROM profiles WHERE username=?",(u,))
    row=c.fetchone(); conn.close()
    pic=row[0] if row and row[0] else ""
    return jsonify({"username":u,"pic":pic})
@app.route('/api/online', methods=['POST'])
def api_online():
    u=session.get('username')
    if not u: return jsonify({"ok":False})
    conn=get_conn(); c=conn.cursor(); now=datetime.now().isoformat()
    if USE_POSTGRES: c.execute("UPDATE profiles SET last_seen=%s WHERE username=%s",(now,u))
    else: c.execute("UPDATE profiles SET last_seen=? WHERE username=?",(now,u))
    conn.commit(); conn.close(); return jsonify({"ok":True})
@app.route('/api/users')
def api_users():
    me=session.get('username')
    if not me: return jsonify([])
    conn=get_conn(); c=conn.cursor()
    if USE_POSTGRES: c.execute("SELECT username,pic_url,last_seen FROM profiles")
    else: c.execute("SELECT username,pic_url,last_seen FROM profiles")
    rows=c.fetchall(); users=[]; now=datetime.now()
    for r in rows:
        un,pic,last=r[0],r[1] or "",r[2]; online=False
        try:
            if last:
                dt=datetime.fromisoformat(last)
                if (now-dt).total_seconds()<120: online=True
        except: pass
        cnt=0
        try:
            if USE_POSTGRES: c.execute("SELECT count FROM streaks WHERE (user1=%s AND user2=%s) OR (user1=%s AND user2=%s)",(me,un,un,me))
            else: c.execute("SELECT count FROM streaks WHERE (user1=? AND user2=?) OR (user1=? AND user2=?)",(me,un,un,me))
            s=c.fetchone()
            if s: cnt=s[0]
        except: pass
        users.append({"username":un,"pic":pic,"online":online,"streak":cnt})
    conn.close(); return jsonify(users)
@app.route('/api/posts')
def api_posts():
    me=session.get('username'); conn=get_conn(); c=conn.cursor()
    if USE_POSTGRES: c.execute("SELECT id,username,text,media_url,created_at FROM posts ORDER BY id DESC LIMIT 50")
    else: c.execute("SELECT id,username,text,media_url,created_at FROM posts ORDER BY id DESC LIMIT 50")
    rows=c.fetchall(); out=[]
    for r in rows:
        pid,uname,txt,media,created=r[0],r[1],r[2],r[3],r[4]
        like_count=0; liked=False; comment_count=0; pic=""; online=False
        try:
            if USE_POSTGRES: c.execute("SELECT COUNT(*) FROM post_likes WHERE post_id=%s",(pid,))
            else: c.execute("SELECT COUNT(*) FROM post_likes WHERE post_id=?",(pid,))
            like_count=c.fetchone()[0]
            if USE_POSTGRES: c.execute("SELECT 1 FROM post_likes WHERE post_id=%s AND username=%s",(pid,me))
            else: c.execute("SELECT 1 FROM post_likes WHERE post_id=? AND username=?",(pid,me))
            if c.fetchone(): liked=True
            if USE_POSTGRES: c.execute("SELECT COUNT(*) FROM comments WHERE post_id=%s",(pid,))
            else: c.execute("SELECT COUNT(*) FROM comments WHERE post_id=?",(pid,))
            comment_count=c.fetchone()[0]
            if USE_POSTGRES: c.execute("SELECT pic_url,last_seen FROM profiles WHERE username=%s",(uname,))
            else: c.execute("SELECT pic_url,last_seen FROM profiles WHERE username=?",(uname,))
            prow=c.fetchone()
            if prow:
                pic=prow[0] or ""
                try:
                    dt=datetime.fromisoformat(prow[1])
                    if (datetime.now()-dt).total_seconds()<120: online=True
                except: pass
        except: pass
        out.append({"id":pid,"username":uname,"text":txt,"media_url":media,"created_at":created,"like_count":like_count,"liked":liked,"comment_count":comment_count,"pic":pic,"online":online})
    conn.close(); return jsonify(out)
    @app.route('/api/post', methods=['POST'])
def api_post():
    me=session.get('username')
    if not me: return jsonify({"ok":False})
    txt=request.form.get('text','')[:500]
    file=request.files.get('media'); url=''
    if file and file.filename:
        import uuid; ext=file.filename.rsplit('.',1)[-1].lower()
        name=str(uuid.uuid4())[:8]+'.'+ext
        os.makedirs('static/uploads', exist_ok=True)
        path=os.path.join('static/uploads',name)
        file.save(path); url='/'+path
    if not txt and not url: return jsonify({"ok":False})
    conn=get_conn(); c=conn.cursor(); now=datetime.now().isoformat()
    if USE_POSTGRES: c.execute("INSERT INTO posts (username,text,media_url,created_at) VALUES (%s,%s,%s,%s)",(me,txt,url,now))
    else: c.execute("INSERT INTO posts (username,text,media_url,created_at) VALUES (?,?,?,?)",(me,txt,url,now))
    conn.commit(); conn.close(); return jsonify({"ok":True})
@app.route('/api/like', methods=['POST'])
def api_like():
    me=session.get('username'); data=request.json; pid=data.get('post_id')
    conn=get_conn(); c=conn.cursor()
    try:
        if USE_POSTGRES: c.execute("SELECT 1 FROM post_likes WHERE post_id=%s AND username=%s",(pid,me))
        else: c.execute("SELECT 1 FROM post_likes WHERE post_id=? AND username=?",(pid,me))
        if c.fetchone():
            if USE_POSTGRES: c.execute("DELETE FROM post_likes WHERE post_id=%s AND username=%s",(pid,me))
            else: c.execute("DELETE FROM post_likes WHERE post_id=? AND username=?",(pid,me))
        else:
            if USE_POSTGRES: c.execute("INSERT INTO post_likes VALUES (%s,%s)",(pid,me))
            else: c.execute("INSERT INTO post_likes VALUES (?,?)",(pid,me))
        conn.commit()
    except: pass
    conn.close(); return jsonify({"ok":True})
@app.route('/api/comments')
def api_comments():
    pid=request.args.get('post_id'); conn=get_conn(); c=conn.cursor()
    if USE_POSTGRES: c.execute("SELECT id,username,text,created_at FROM comments WHERE post_id=%s ORDER BY id ASC",(pid,))
    else: c.execute("SELECT id,username,text,created_at FROM comments WHERE post_id=? ORDER BY id ASC",(pid,))
    rows=c.fetchall(); out=[]
    for r in rows:
        cid,uname,txt,created=r[0],r[1],r[2],r[3]; like_count=0
        try:
            if USE_POSTGRES: c.execute("SELECT COUNT(*) FROM comment_likes WHERE comment_id=%s",(cid,))
            else: c.execute("SELECT COUNT(*) FROM comment_likes WHERE comment_id=?",(cid,))
            like_count=c.fetchone()[0]
        except: pass
        out.append({"id":cid,"username":uname,"text":txt,"created_at":created,"like_count":like_count})
    conn.close(); return jsonify(out)
@app.route('/api/comment', methods=['POST'])
def api_comment():
    me=session.get('username'); data=request.json; pid=data.get('post_id'); txt=data.get('text','')[:300]
    if not txt: return jsonify({"ok":False})
    conn=get_conn(); c=conn.cursor(); now=datetime.now().isoformat()
    if USE_POSTGRES: c.execute("INSERT INTO comments (post_id,username,text,created_at) VALUES (%s,%s,%s,%s)",(pid,me,txt,now))
    else: c.execute("INSERT INTO comments (post_id,username,text,created_at) VALUES (?,?,?,?)",(pid,me,txt,now))
    conn.commit(); conn.close(); return jsonify({"ok":True})
@app.route('/api/comment/like', methods=['POST'])
def api_comment_like():
    me=session.get('username'); data=request.json; cid=data.get('comment_id')
    conn=get_conn(); c=conn.cursor()
    try:
        if USE_POSTGRES: c.execute("SELECT 1 FROM comment_likes WHERE comment_id=%s AND username=%s",(cid,me))
        else: c.execute("SELECT 1 FROM comment_likes WHERE comment_id=? AND username=?",(cid,me))
        if c.fetchone():
            if USE_POSTGRES: c.execute("DELETE FROM comment_likes WHERE comment_id=%s AND username=%s",(cid,me))
            else: c.execute("DELETE FROM comment_likes WHERE comment_id=? AND username=?",(cid,me))
        else:
            if USE_POSTGRES: c.execute("INSERT INTO comment_likes VALUES (%s,%s)",(cid,me))
            else: c.execute("INSERT INTO comment_likes VALUES (?,?)",(cid,me))
        conn.commit()
    except: pass
    conn.close(); return jsonify({"ok":True})
@app.route('/api/stories')
def api_stories():
    conn=get_conn(); c=conn.cursor(); now=datetime.now().isoformat()
    if USE_POSTGRES: c.execute("SELECT id,username,media_url,text,created_at FROM stories WHERE expires_at>%s ORDER BY id DESC",(now,))
    else: c.execute("SELECT id,username,media_url,text,created_at FROM stories WHERE expires_at>? ORDER BY id DESC",(now,))
    rows=c.fetchall(); out=[]
    for r in rows:
        sid,uname,media,txt,created=r[0],r[1],r[2],r[3],r[4]; views=0
        try:
            if USE_POSTGRES: c.execute("SELECT COUNT(*) FROM story_views WHERE story_id=%s",(sid,))
            else: c.execute("SELECT COUNT(*) FROM story_views WHERE story_id=?",(sid,))
            views=c.fetchone()[0]
        except: pass
        out.append({"id":sid,"username":uname,"media_url":media,"text":txt,"created_at":created,"views":views})
    conn.close(); return jsonify(out)
@app.route('/api/story', methods=['POST'])
def api_story():
    me=session.get('username'); file=request.files.get('media')
    if not file or not file.filename: return jsonify({"ok":False})
    import uuid; ext=file.filename.rsplit('.',1)[-1].lower(); name=str(uuid.uuid4())[:8]+'.'+ext
    os.makedirs('static/uploads', exist_ok=True); path=os.path.join('static/uploads',name); file.save(path); url='/'+path
    conn=get_conn(); c=conn.cursor(); now=datetime.now(); exp=now+timedelta(hours=24)
    if USE_POSTGRES: c.execute("INSERT INTO stories (username,media_url,text,created_at,expires_at) VALUES (%s,%s,%s,%s,%s)",(me,url,"",now.isoformat(),exp.isoformat()))
    else: c.execute("INSERT INTO stories (username,media_url,text,created_at,expires_at) VALUES (?,?,?,?,?)",(me,url,"",now.isoformat(),exp.isoformat()))
    conn.commit(); conn.close(); return jsonify({"ok":True})
@app.route('/api/story/view', methods=['POST'])
def api_story_view():
    me=session.get('username'); data=request.json; sid=data.get('id')
    conn=get_conn(); c=conn.cursor()
    try:
        if USE_POSTGRES: c.execute("INSERT INTO story_views VALUES (%s,%s) ON CONFLICT DO NOTHING",(sid,me))
        else: c.execute("INSERT OR IGNORE INTO story_views VALUES (?,?)",(sid,me))
        conn.commit()
    except: pass
    conn.close(); return jsonify({"ok":True})
@app.route('/api/messages')
def api_messages():
    me=session.get('username'); other=request.args.get('with','')
    if not me or not other: return jsonify([])
    conn=get_conn(); c=conn.cursor()
    if USE_POSTGRES: c.execute("SELECT id,sender,text,media_url FROM messages WHERE (sender=%s AND receiver=%s) OR (sender=%s AND receiver=%s) ORDER BY id ASC",(me,other,other,me))
    else: c.execute("SELECT id,sender,text,media_url FROM messages WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) ORDER BY id ASC",(me,other,other,me))
    rows=c.fetchall(); out=[]
    for r in rows:
        mid,sender,txt,media=r[0],r[1],r[2],r[3]; reacts=""
        try:
            if USE_POSTGRES: c.execute("SELECT emoji FROM msg_reacts WHERE msg_id=%s",(mid,))
            else: c.execute("SELECT emoji FROM msg_reacts WHERE msg_id=?",(mid,))
            er=c.fetchall(); reacts=" ".join([x[0] for x in er])
        except: pass
        out.append({"id":mid,"sender":sender,"text":txt,"media_url":media,"reacts":reacts})
    conn.close(); return jsonify(out)
@app.route('/api/send', methods=['POST'])
def api_send():
    me=session.get('username')
    if not me: return jsonify({"ok":False})
    if request.is_json:
        data=request.json; other=data.get('receiver',''); txt=data.get('text','')[:500]; url=''
    else:
        other=request.form.get('receiver',''); txt=request.form.get('text','')[:500]; file=request.files.get('media'); url=''
        if file and file.filename:
            import uuid; ext=file.filename.rsplit('.',1)[-1].lower(); name=str(uuid.uuid4())[:8]+'.'+ext
            os.makedirs('static/uploads', exist_ok=True); path=os.path.join('static/uploads',name); file.save(path); url='/'+path
    if not txt and not url: return jsonify({"ok":False})
    conn=get_conn(); c=conn.cursor(); now=datetime.now().isoformat()
    if USE_POSTGRES: c.execute("INSERT INTO messages (sender,receiver,text,media_url,created_at) VALUES (%s,%s,%s,%s,%s)",(me,other,txt,url,now))
    else: c.execute("INSERT INTO messages (sender,receiver,text,media_url,created_at) VALUES (?,?,?,?,?)",(me,other,txt,url,now))
    try:
        today=datetime.now().date().isoformat()
        if USE_POSTGRES: c.execute("SELECT count,last_date FROM streaks WHERE user1=%s AND user2=%s",(me,other))
        else: c.execute("SELECT count,last_date FROM streaks WHERE user1=? AND user2=?",(me,other))
        row=c.fetchone()
        if not row:
            if USE_POSTGRES:
                c.execute("INSERT INTO streaks VALUES (%s,%s,%s,%s)",(me,other,1,today))
                c.execute("INSERT INTO streaks VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",(other,me,1,today))
            else:
                c.execute("INSERT INTO streaks VALUES (?,?,?,?)",(me,other,1,today))
                c.execute("INSERT OR IGNORE INTO streaks VALUES (?,?,?,?)",(other,me,1,today))
        else:
            if row[1]!=today:
                cnt=row[0]+1
                if USE_POSTGRES:
                    c.execute("UPDATE streaks SET count=%s,last_date=%s WHERE user1=%s AND user2=%s",(cnt,today,me,other))
                    c.execute("UPDATE streaks SET count=%s,last_date=%s WHERE user1=%s AND user2=%s",(cnt,today,other,me))
                else:
                    c.execute("UPDATE streaks SET count=?,last_date=? WHERE user1=? AND user2=?",(cnt,today,me,other))
                    c.execute("UPDATE streaks SET count=?,last_date=? WHERE user1=? AND user2=?",(cnt,today,other,me))
    except: pass
    conn.commit(); conn.close()
    typing_map.pop((other,me),None)
    return jsonify({"ok":True})
@app.route('/api/typing', methods=['POST','GET'])
def api_typing():
    me=session.get('username')
    if request.method=='POST':
        data=request.json; other=data.get('receiver'); typing_map[(me,other)]=datetime.now(); return jsonify({"ok":True})
    else:
        other=request.args.get('with'); t=typing_map.get((other,me)); typing=False
        if t and (datetime.now()-t).total_seconds()<3: typing=True
        return jsonify({"typing":typing})
@app.route('/api/react', methods=['POST'])
def api_react():
    me=session.get('username'); data=request.json; mid=data.get('msg_id'); emoji=data.get('emoji','❤️')[:2]
    conn=get_conn(); c=conn.cursor()
    try:
        if USE_POSTGRES: c.execute("INSERT INTO msg_reacts VALUES (%s,%s,%s) ON CONFLICT (msg_id,username) DO UPDATE SET emoji=%s",(mid,me,emoji,emoji))
        else: c.execute("INSERT OR REPLACE INTO msg_reacts VALUES (?,?,?)",(mid,me,emoji))
        conn.commit()
    except: pass
    conn.close(); return jsonify({"ok":True})
@app.route('/api/profile/pic', methods=['POST'])
def api_pic():
    me=session.get('username'); file=request.files.get('media')
    if not file or not file.filename: return jsonify({"ok":False})
    import uuid; ext=file.filename.rsplit('.',1)[-1].lower(); name='pic_'+me+'_'+str(uuid.uuid4())[:4]+'.'+ext
    os.makedirs('static/uploads', exist_ok=True); path=os.path.join('static/uploads',name); file.save(path); url='/'+path
    conn=get_conn(); c=conn.cursor()
    if USE_POSTGRES: c.execute("UPDATE profiles SET pic_url=%s WHERE username=%s",(url,me))
    else: c.execute("UPDATE profiles SET pic_url=? WHERE username=?",(url,me))
    conn.commit(); conn.close(); return jsonify({"ok":True,"url":url})
@app.route('/static/uploads/<path:filename>')
def uploads(filename): return send_from_directory('static/uploads',filename)
@app.route('/logo.jpg')
def logo_jpg():
    if os.path.exists('logo.jpg'): return send_from_directory('.', 'logo.jpg')
    if os.path.exists('logo-full.jpg'): return send_from_directory('.', 'logo-full.jpg')
    return "",404
@app.route('/logo-full.jpg')
def logo_full():
    if os.path.exists('logo-full.jpg'): return send_from_directory('.', 'logo-full.jpg')
    return "",404
@app.route('/logout')
def logout(): session.clear(); return redirect('/login')
if __name__=='__main__':
    port=int(os.environ.get("PORT",5000))
    app.run(host='0.0.0.0',port=port)
