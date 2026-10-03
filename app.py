import os
from flask import Flask, request, jsonify, session, render_template_string, redirect, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import sqlite3

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET","prove-am-final")
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

def init_db():
    conn = get_conn(); c=conn.cursor()
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
    conn.commit(); conn.close()
init_db()
typing_map={}

LOGIN_HTML="""<!DOCTYPE html><html><head><meta name=viewport content="width=device-width,initial-scale=1"><style>body{background:#000;color:#fff;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}.box{background:#111;padding:24px;border-radius:22px;width:330px;text-align:center;border:1px solid #222}input{width:100%;padding:13px;margin:8px 0;border-radius:12px;border:none;background:#222;color:#fff;box-sizing:border-box}button{width:100%;padding:13px;background:#ffcc00;border:none;border-radius:12px;font-weight:bold}img{width:90px;height:90px;border-radius:50%;border:2px solid #ffcc00}</style></head><body><div class=box><h2 style=color:#ffcc00>PROVE AM</h2><input id=u placeholder=Username><input id=p type=password placeholder=Password><button onclick=login()>Login</button><button onclick=signup() style=background:#222;color:#fff;margin-top:8px>Sign Up</button><p id=msg style=color:#ff5555></p></div><script>async function login(){let r=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u.value,password:p.value})});let d=await r.json();if(d.ok)location.href='/';else msg.innerText=d.error}async function signup(){let r=await fetch('/signup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u.value,password:p.value})});let d=await r.json();if(d.ok)location.href='/';else msg.innerText=d.error}</script></body></html>"""

MAIN_HTML="""<!DOCTYPE html><html><head><meta name=viewport content="width=device-width,initial-scale=1"><style>
body{background:#fff;color:#000;font-family:-apple-system,sans-serif;margin:0}
.top{position:fixed;top:0;left:0;right:0;background:#fff;padding:10px 12px;display:flex;align-items:center;justify-content:space-between;z-index:100;border-bottom:1px solid #eee;height:44px}
.logo{color:#c9a227;font-weight:bold;display:flex;align-items:center;gap:6px}
.tabs{position:fixed;top:64px;left:0;right:0;background:#fff;display:flex;z-index:99;border-bottom:1px solid #eee}
.tab{flex:1;padding:14px;text-align:center;font-weight:bold;color:#888;cursor:pointer;border-bottom:3px solid transparent}
.tab.active{color:#000;border-color:#000}
.content{margin-top:112px;padding:12px;padding-bottom:90px;min-height:100vh;background:#f8f8f8}
.story-bar{display:flex;gap:14px;overflow-x:auto;padding:10px 0}
.story-item{text-align:center;min-width:70px;cursor:pointer}
.story-item.ring{width:68px;height:68px;border-radius:50%;background:#000;display:flex;align-items:center;justify-content:center;color:#fff;font-size:12px;text-align:center;padding:5px;box-sizing:border-box;border:3px solid #000}
.story-item img.ring{object-fit:cover;border:3px solid #000}
.story-card{border:1.5px dashed #ccc;border-radius:16px;padding:16px;background:#fff;margin-top:16px}
.btn-row{display:flex;gap:12px;margin-top:12px}
.btn-light{flex:1;padding:12px;border-radius:20px;border:1.5px solid #000;background:#fff;font-weight:bold}
.btn-dark{flex:1;padding:12px;border-radius:20px;border:1.5px solid #000;background:#000;color:#fff;font-weight:bold}
.post-card{background:#fff;margin:12px 0;border-radius:0;border-bottom:8px solid #f0f0f0}
.post-card img.post-img,.post-card video{width:100%;max-height:80vh;object-fit:cover}
.post-actions{display:flex;gap:16px;padding:10px 12px;font-size:20px;align-items:center}
.card{background:#fff;margin:10px 0;padding:12px;border-radius:16px;border:1px solid #eee}
input,textarea{width:100%;background:#f0f0f0;color:#000;border:none;border-radius:12px;padding:12px;margin:6px 0;box-sizing:border-box}
button{background:#ffcc00;color:#000;border:none;padding:10px 16px;border-radius:12px;font-weight:bold}
.stickers{display:flex;gap:6px;overflow-x:auto;padding:8px 0}
.stickers span{font-size:22px;background:#f0f0f0;padding:6px 8px;border-radius:12px;cursor:pointer}
.viewer{position:fixed;top:0;left:0;right:0;bottom:0;background:#000;z-index:999;display:none;flex-direction:column}
.online-dot{width:8px;height:8px;background:#0f0;border-radius:50%;display:inline-block}
</style></head><body>
<div class=top><div class=logo><span style=border:2px solid #c9a227;border-radius:50%;padding:4px 6px;font-size:10px>PROVE</span> PROVE AM</div><div>⚙️ 👤</div></div>
<div class=tabs><div class=tab active id=tStories onclick="showTab('stories')">Stories</div><div class=tab id=tPost onclick="showTab('post')">Post</div><div class=tab id=tChat onclick="showTab('chat')">Chat 💬</div></div>
<div class=content>
<div id=storiesDiv><div style=display:flex;justify-content:space-between;align-items:center><b>Friends ></b><b style=color:#a855f7;cursor:pointer onclick="document.getElementById('storyFile').click()">+ Add Story</b><input type=file id=storyFile accept="image/*,video/*" style=display:none onchange=createStory()></div><div class=story-bar id=storyBar></div><div class=story-card><b>Post a Story ✨</b><br><small>video, picture, or text — disappears in 24h</small><div class=btn-row><button class=btn-light onclick="document.getElementById('storyFile').click()">📷 Photo/Video</button><button class=btn-dark onclick="createTextStory()">A Text Story</button></div></div><div id=stickerStory class=stickers></div></div>
<div id=postDiv style=display:none><div class=card><textarea id=postText placeholder="What's up? Prove Am..."></textarea><div id=stickerPost class=stickers></div><input type=file id=postFile accept="image/*,video/*" multiple><button onclick=createPost()>Post</button></div><div id=postsList></div></div>
<div id=chatDiv style=display:none><input id=searchChat placeholder="Search users..." oninput=filterChat()><div id=chatUsers></div><div id=chatBox style=display:none></div></div>
</div>
<div class=viewer id=viewerModal><div style="padding:12px;display:flex;justify-content:space-between;background:#111;color:#fff"><b id=viewerUser></b><div><span id=viewerCount></span> <button onclick=closeViewer() style=background:#fff>X</button></div></div><div style="flex:1;display:flex;align-items:center;justify-content:center;background:#000"><img id=viewerMedia style="max-width:100%;max-height:80vh;display:none"><video id=viewerVideo controls playsinline style="max-width:100%;max-height:80vh;display:none"></video><div id=viewerText style="color:#fff;font-size:28px;font-weight:bold;padding:20px;display:none"></div></div><div style="padding:12px;background:#111"><div id=stickerStory2 class=stickers></div><div style="display:flex;gap:8px"><input id=replyStoryInput placeholder="Reply to story..." style="flex:1;background:#222;color:#fff"><button onclick=replyStory()>Send</button><button onclick=nextStory() style="background:#fff">Next</button></div></div></div>
<script>
let curUser='',chatWith='',stories=[],storyIdx=0,allUsers=[];
const STICKERS=['😂','❤️','🔥','😭','🙏','🇬🇭','💯','👏','😍','🥺','✨','🎉','😅','🤣'];
function stickerBar(id){return STICKERS.map(s=>`<span onclick="addSticker('${id}','${s}')">${s}</span>`).join('')}
function addSticker(id,em){let el=document.getElementById(id);if(el){el.value+=em;el.focus()}}
async function loadMe(){let r=await fetch('/api/me');let d=await r.json();curUser=d.username;setInterval(()=>fetch('/api/online',{method:'POST'}),15000);fetch('/api/online',{method:'POST'})}
function showTab(t){document.querySelectorAll('.tab').forEach(e=>e.classList.remove('active'));document.getElementById('t'+t.charAt(0).toUpperCase()+t.slice(1)).classList.add('active');['stories','post','chat'].forEach(x=>document.getElementById(x+'Div').style.display=x==t?'block':'none');if(t=='stories')loadStories();if(t=='post'){loadPosts();document.getElementById('stickerPost').innerHTML=stickerBar('postText')}if(t=='chat')loadChatUsers()}
async function loadStories(){let r=await fetch('/api/stories');stories=await r.json();let h='';stories.forEach((s,i)=>{let inner=s.text?`<div class=ring style=background:#000>${s.text.slice(0,20)}</div>`:`<img class=ring src="${s.media_url}">`;h+=`<div class=story-item onclick="openViewer(${i})">${inner}<br><small><b>${s.username.slice(0,10)}</b></small><br><small>👁️${s.views||0}</small></div>`});document.getElementById('storyBar').innerHTML=h||'<small style=color:#888>No stories yet</small>';document.getElementById('stickerStory').innerHTML=stickerBar('replyStoryInput');document.getElementById('stickerStory2').innerHTML=stickerBar('replyStoryInput')}
function openViewer(i){storyIdx=i;let s=stories[i];viewerModal.style.display='flex';viewerUser.innerText=s.username;viewerCount.innerText='👁️ '+(s.views||0);let img=document.getElementById('viewerMedia'),vid=document.getElementById('viewerVideo'),txt=document.getElementById('viewerText');img.style.display=vid.style.display=txt.style.display='none';if(s.text){txt.style.display='block';txt.innerText=s.text}else if(s.media_url.match(/\\.(mp4|webm|mov)$/i)){vid.style.display='block';vid.src=s.media_url;vid.load()}else{img.style.display='block';img.src=s.media_url}fetch('/api/story/view',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:s.id})})}
function closeViewer(){viewerModal.style.display='none';document.getElementById('viewerVideo').pause()}
function nextStory(){if(storyIdx<stories.length-1)openViewer(storyIdx+1);else closeViewer()}
async function replyStory(){let s=stories[storyIdx];let t=document.getElementById('replyStoryInput').value||'🔥';await fetch('/api/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({receiver:s.username,text:t})});document.getElementById('replyStoryInput').value='';closeViewer()}
async function createStory(){let f=storyFile.files[0];if(!f)return;let fd=new FormData();fd.append('media',f);let r=await fetch('/api/story',{method:'POST',body:fd});let d=await r.json();if(d.ok){setTimeout(loadStories,700);alert('Story posted!')} }
async function createTextStory(){let t=prompt('Enter text story (disappears 24h):');if(!t)return;let r=await fetch('/api/story/text',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t})});let d=await r.json();if(d.ok){loadStories();}}
async function loadPosts(){let r=await fetch('/api/posts');let posts=await r.json();let h='';if(posts.length==0)h='<div class=card style=text-align:center;color:#888>No posts yet - be first!</div>';posts.forEach(p=>{let media='';if(p.media_url){if(p.media_url.match(/\\.(mp4|webm|mov)$/i))media=`<video src="${p.media_url}" controls playsinline preload=none class=post-img></video>`;else media=`<img src="${p.media_url}" class=post-img>`}h+=`<div class=post-card><div style="padding:8px 12px;display:flex;align-items:center;gap:8px"><img src="${p.pic||''}" style="width:32px;height:32px;border-radius:50%;background:#eee" onerror="this.style.display='none'"><b>${p.username}</b><small style="margin-left:auto">${p.created_at.slice(0,16)}</small></div>${p.text?`<div style="padding:0 12px 8px">${p.text}</div>`:''}${media}<div class=post-actions><span onclick="likePost(${p.id})" style=cursor:pointer>${p.liked?'❤️':'🤍'} ${p.like_count||0}</span><span onclick="toggleComments(${p.id})">💬 ${p.comment_count||0}</span><span onclick="sharePost(${p.id})">✈️</span><span style=margin-left:auto;cursor:pointer onclick="deletePost(${p.id})">🗑️</span></div><div id=comments-${p.id} style=display:none;padding:0 12px><div id=commentList-${p.id}></div><div style="display:flex;gap:6px;padding:8px 0"><input id=commentInput-${p.id} placeholder="Comment..."><button onclick="addComment(${p.id})">Send</button></div></div></div>`});document.getElementById('postsList').innerHTML=h}
async function likePost(id){await fetch('/api/like',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:id})});loadPosts()}
async function deletePost(id){if(!confirm('Delete?'))return;await fetch('/api/post/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});loadPosts()}
async function sharePost(id){let t=prompt('Share to user:');if(!t)return;await fetch('/api/send',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({receiver:t,text:'Check this post: '+id})});alert('Shared')}
async function toggleComments(id){let el=document.getElementById('comments-'+id);el.style.display=el.style.display=='none'?'block':'none';if(el.style.display=='block'){let r=await fetch('/api/comments?post_id='+id);let cs=await r.json();let h='';cs.forEach(c=>{h+=`<div style="padding:8px;background:#f5f5f5;margin:4px 0;border-radius:10px"><b>${c.username}</b>: ${c.text} <span onclick="likeComment(${c.id})" style=float:right>❤️ ${c.like_count||0}</span></div>`});document.getElementById('commentList-'+id).innerHTML=h||'No comments'}}
async function addComment(pid){let el=document.getElementById('commentInput-'+pid);let txt=el.value;if(!txt)return;await fetch('/api/comment',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:pid,text:txt})});el.value='';loadPosts()}
async function likeComment(id){await fetch('/api/comment/like',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({comment_id:id})})}
async function createPost(){let files=document.getElementById('postFile').files;let text=document.getElementById('postText').value;if(!text&&files.length==0){alert('Write something');return}if(files.length==0){let fd=new FormData();fd.append('text',text);await fetch('/api/post',{method:'POST',body:fd})}else{for(let f of files){let fd=new FormData();fd.append('text',text);fd.append('media',f);await fetch('/api/post',{method:'POST',body:fd});text=''}}document.getElementById('postText').value='';document.getElementById('postFile').value='';setTimeout(loadPosts,800)}
async function loadChatUsers(){let r=await fetch('/api/users');allUsers=await r.json();renderChatUsers(allUsers)}
function renderChatUsers(users){let h='';users.forEach(u=>{if(u.username==curUser)return;h+=`<div class=card style="display:flex;align-items:center;justify-content:space-between;cursor:pointer" onclick="openChat('${u.username}')"><div style="display:flex;align-items:center;gap:10px"><div style="width:40px;height:40px;border-radius:50%;background:#000;color:#fff;display:flex;align-items:center;justify-content:center">${u.username[0]}</div><div><b>${u.username}</b><br><small>${u.online?'🟢 Online':'⚪ Offline'} ${u.streak?'🔥'+u.streak:''}</small></div></div><div>→</div></div>`});document.getElementById('chatUsers').innerHTML=h||'No users'}
function filterChat(){let q=document.getElementById('searchChat').value.toLowerCase();renderChatUsers(allUsers.filter(u=>u.username.toLowerCase().includes(q)))}
async function openChat(username){chatWith=username;document.getElementById('chatUsers').style.display='none';document.getElementById('searchChat').style.display='none';let box=document.getElementById('chatBox');box.style.display='block';box.innerHTML=`<button onclick="backChat()" style="background:#eee;margin-bottom:10px">← ${username} <span id=typingStatus style=color:#0a0></span></button><div id=msgs style="margin-bottom:140px"></div><div id=stickerChat class=stickers></div><div style="position:fixed;bottom:0;left:0;right:0;background:#fff;padding:10px;display:flex;gap:6px;border-top:1px solid #eee"><input id=chatText placeholder="Message" style="flex:1;background:#f0f0f0" oninput=sendTyping()><input type=file id=chatFile accept="image/*,video/*,audio/*" style="width:70px"><button onclick="startAudio()" style="background:#000;color:#fff">🎤</button><button onclick=sendMsg() style="background:#000;color:#fff">Send</button></div>`;document.getElementById('stickerChat').innerHTML=stickerBar('chatText');loadMsgs();window.chatInterval=setInterval(loadMsgs,3000)}
function backChat(){chatWith='';clearInterval(window.chatInterval);document.getElementById('chatBox').style.display='none';document.getElementById('chatUsers').style.display='block';document.getElementById('searchChat').style.display='block'}
async function loadMsgs(){if(!chatWith)return;let r=await fetch('/api/messages?with='+chatWith);let msgs=await r.json();let h='';msgs.forEach(m=>{let media='';if(m.media_url){if(m.media_url.match(/\\.(mp3|m4a|ogg|wav|webm|mp4)$/i)){media=`<br><audio controls preload=none style="width:200px"><source src="${m.media_url}"></audio>`}else if(m.media_url.match(/\\.(mp4|webm|mov)$/i))media=`<br><video src="${m.media_url}" controls playsinline style="max-width:200px;border-radius:12px"></video>`;else media=`<br><img src="${m.media_url}" style="max-width:200px;border-radius:12px">`}let isMe=m.sender==curUser;let reactHtml=m.reacts?`<div style="margin-top:5px;text-align:${isMe?'right':'left'}"><span style="background:#eee;padding:3px 9px;border-radius:12px;font-size:13px;border:1px solid #ddd">${m.reacts}</span></div>`:'';h+=`<div style="margin:12px 0;text-align:${isMe?'right':'left'}"><span style="background:${isMe?'#000':'#f0f0f0'};color:${isMe?'#fff':'#000'};padding:10px 14px;border-radius:18px;display:inline-block;max-width:72%;cursor:pointer" onclick="reactMsg(${m.id})">${m.text||''}${media}</span>${reactHtml}</div>`});let el=document.getElementById('msgs');if(el)el.innerHTML=h;let tr=await fetch('/api/typing?with='+chatWith);let td=await tr.json();let ts=document.getElementById('typingStatus');if(ts)ts.innerText=td.typing?'typing...':''}
async function sendMsg(){let t=document.getElementById('chatText').value;let f=document.getElementById('chatFile').files[0];if(!t&&!f)return;let fd=new FormData();fd.append('receiver',chatWith);fd.append('text',t);if(f)fd.append('media',f);await fetch('/api/send',{method:'POST',body:fd});document.getElementById('chatText').value='';document.getElementById('chatFile').value='';loadMsgs()}
async function sendTyping(){fetch('/api/typing',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({receiver:chatWith})})}
async function reactMsg(id){let e=prompt('React: ❤️ 😂 🔥 😭 🙏 🇬🇭');if(!e)return;await fetch('/api/react',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({msg_id:id,emoji:e})});loadMsgs()}
let rec,chunks=[];async function startAudio(){if(rec&&rec.state=='recording'){rec.stop();return}try{let s=await navigator.mediaDevices.getUserMedia({audio:true});let mime='';if(MediaRecorder.isTypeSupported('audio/mp4'))mime='audio/mp4';else if(MediaRecorder.isTypeSupported('audio/webm'))mime='audio/webm';rec=new MediaRecorder(s,{mimeType:mime});chunks=[];rec.ondataavailable=e=>chunks.push(e.data);rec.onstop=async()=>{let ext=mime.includes('mp4')?'mp4':'webm';let blob=new Blob(chunks,{type:mime});let fd=new FormData();fd.append('receiver',chatWith);fd.append('media',blob,'voice.'+ext);fd.append('text','🎤 Audio');await fetch('/api/send',{method:'POST',body:fd});loadMsgs()};rec.start();alert('Recording... tap 🎤 again to stop')}catch(e){alert('Mic needed')}}
loadMe();showTab('stories');
</script></body></html>"""

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
def api_me():
    u=session.get('username')
    if not u: return jsonify({"username":""})
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT pic_url FROM profiles WHERE username=%s" if USE_POSTGRES else "SELECT pic_url FROM profiles WHERE username=?", (u,))
    row=c.fetchone(); conn.close()
    return jsonify({"username":u,"pic":row[0] if row and row[0] else ""})

@app.route('/api/online', methods=['POST'])
def api_online():
    u=session.get('username')
    if not u: return jsonify({"ok":False})
    conn=get_conn(); c=conn.cursor(); now=datetime.now().isoformat()
    c.execute("UPDATE profiles SET last_seen=%s WHERE username=%s" if USE_POSTGRES else "UPDATE profiles SET last_seen=? WHERE username=?", (now,u))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/api/users')
def api_users():
    me=session.get('username'); conn=get_conn(); c=conn.cursor()
    c.execute("SELECT username,pic_url,last_seen FROM profiles"); rows=c.fetchall(); users=[]; now=datetime.now()
    for r in rows:
        un=r[0]; pic=r[1] or ""; last=r[2]; online=False
        try:
            if last:
                dt=datetime.fromisoformat(last)
                if (now-dt).total_seconds()<120: online=True
        except: pass
        cnt=0
        try:
            c.execute("SELECT count FROM streaks WHERE (user1=%s AND user2=%s) OR (user1=%s AND user2=%s)" if USE_POSTGRES else "SELECT count FROM streaks WHERE (user1=? AND user2=?) OR (user1=? AND user2=?)",(me,un,un,me))
            s=c.fetchone();
            if s: cnt=s[0]
        except: pass
        users.append({"username":un,"pic":pic,"online":online,"streak":cnt})
    conn.close(); return jsonify(users)

@app.route('/api/posts')
def api_posts():
    me=session.get('username'); conn=get_conn(); c=conn.cursor()
    c.execute("SELECT id,username,text,media_url,created_at FROM posts ORDER BY id DESC LIMIT 50"); rows=c.fetchall(); out=[]
    for r in rows:
        pid=r[0]; uname=r[1]; txt=r[2]; media=r[3]; created=r[4]; like_count=0; liked=False; comment_count=0; pic=""
        try:
            c.execute("SELECT COUNT(*) FROM post_likes WHERE post_id=%s" if USE_POSTGRES else "SELECT COUNT(*) FROM post_likes WHERE post_id=?", (pid,)); like_count=c.fetchone()[0]
            c.execute("SELECT 1 FROM post_likes WHERE post_id=%s AND username=%s" if USE_POSTGRES else "SELECT 1 FROM post_likes WHERE post_id=? AND username=?", (pid,me))
            if c.fetchone(): liked=True
            c.execute("SELECT COUNT(*) FROM comments WHERE post_id=%s" if USE_POSTGRES else "SELECT COUNT(*) FROM comments WHERE post_id=?", (pid,)); comment_count=c.fetchone()[0]
            c.execute("SELECT pic_url FROM profiles WHERE username=%s" if USE_POSTGRES else "SELECT pic_url FROM profiles WHERE username=?", (uname,)); prow=c.fetchone()
            if prow: pic=prow[0] or ""
        except: pass
        out.append({"id":pid,"username":uname,"text":txt,"media_url":media,"created_at":created,"like_count":like_count,"liked":liked,"comment_count":comment_count,"pic":pic})
    conn.close(); return jsonify(out)

@app.route('/api/post', methods=['POST'])
def api_post():
    me=session.get('username')
    if not me: return jsonify({"ok":False})
    txt=request.form.get('text','')[:500]; file=request.files.get('media'); url=''
    if file and file.filename:
        import uuid; ext=file.filename.rsplit('.',1)[-1].lower(); name=str(uuid.uuid4())[:8]+'.'+ext; os.makedirs('static/uploads',exist_ok=True); path=os.path.join('static/uploads',name); file.save(path); url='/'+path
    if not txt and not url: return jsonify({"ok":False})
    conn=get_conn(); c=conn.cursor(); now=datetime.now().isoformat()
    c.execute("INSERT INTO posts (username,text,media_url,created_at) VALUES (%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO posts (username,text,media_url,created_at) VALUES (?,?,?,?)",(me,txt,url,now))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/api/post/delete', methods=['POST'])
def api_post_del():
    me=session.get('username'); data=request.json; pid=data.get('id')
    conn=get_conn(); c=conn.cursor()
    c.execute("DELETE FROM posts WHERE id=%s AND username=%s" if USE_POSTGRES else "DELETE FROM posts WHERE id=? AND username=?", (pid,me))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/api/like', methods=['POST'])
def api_like():
    me=session.get('username'); data=request.json; pid=data.get('post_id'); conn=get_conn(); c=conn.cursor()
    try:
        c.execute("SELECT 1 FROM post_likes WHERE post_id=%s AND username=%s" if USE_POSTGRES else "SELECT 1 FROM post_likes WHERE post_id=? AND username=?", (pid,me))
        if c.fetchone(): c.execute("DELETE FROM post_likes WHERE post_id=%s AND username=%s" if USE_POSTGRES else "DELETE FROM post_likes WHERE post_id=? AND username=?", (pid,me))
        else: c.execute("INSERT INTO post_likes VALUES (%s,%s)" if USE_POSTGRES else "INSERT INTO post_likes VALUES (?,?)", (pid,me))
        conn.commit()
    except: pass
    conn.close(); return jsonify({"ok":True})

@app.route('/api/comments')
def api_comments():
    pid=request.args.get('post_id'); conn=get_conn(); c=conn.cursor()
    c.execute("SELECT id,username,text,created_at FROM comments WHERE post_id=%s ORDER BY id ASC" if USE_POSTGRES else "SELECT id,username,text,created_at FROM comments WHERE post_id=? ORDER BY id ASC", (pid,))
    rows=c.fetchall(); out=[]
    for r in rows:
        cid=r[0]; like_count=0
        try: c.execute("SELECT COUNT(*) FROM comment_likes WHERE comment_id=%s" if USE_POSTGRES else "SELECT COUNT(*) FROM comment_likes WHERE comment_id=?", (cid,)); like_count=c.fetchone()[0]
        except: pass
        out.append({"id":cid,"username":r[1],"text":r[2],"created_at":r[3],"like_count":like_count})
    conn.close(); return jsonify(out)

@app.route('/api/comment', methods=['POST'])
def api_comment():
    me=session.get('username'); data=request.json; pid=data.get('post_id'); txt=data.get('text','')[:300]
    if not txt: return jsonify({"ok":False})
    conn=get_conn(); c=conn.cursor(); now=datetime.now().isoformat()
    c.execute("INSERT INTO comments (post_id,username,text,created_at) VALUES (%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO comments (post_id,username,text,created_at) VALUES (?,?,?,?)", (pid,me,txt,now))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/api/comment/like', methods=['POST'])
def api_comment_like():
    me=session.get('username'); data=request.json; cid=data.get('comment_id'); conn=get_conn(); c=conn.cursor()
    try:
        c.execute("SELECT 1 FROM comment_likes WHERE comment_id=%s AND username=%s" if USE_POSTGRES else "SELECT 1 FROM comment_likes WHERE comment_id=? AND username=?", (cid,me))
        if c.fetchone(): c.execute("DELETE FROM comment_likes WHERE comment_id=%s AND username=%s" if USE_POSTGRES else "DELETE FROM comment_likes WHERE comment_id=? AND username=?", (cid,me))
        else: c.execute("INSERT INTO comment_likes VALUES (%s,%s)" if USE_POSTGRES else "INSERT INTO comment_likes VALUES (?,?)", (cid,me))
        conn.commit()
    except: pass
    conn.close(); return jsonify({"ok":True})

@app.route('/api/stories')
def api_stories():
    conn=get_conn(); c=conn.cursor(); now=datetime.now().isoformat()
    c.execute("SELECT id,username,media_url,text,created_at FROM stories WHERE expires_at>%s ORDER BY id DESC" if USE_POSTGRES else "SELECT id,username,media_url,text,created_at FROM stories WHERE expires_at>? ORDER BY id DESC", (now,))
    rows=c.fetchall(); out=[]
    for r in rows:
        sid=r[0]; views=0
        try: c.execute("SELECT COUNT(*) FROM story_views WHERE story_id=%s" if USE_POSTGRES else "SELECT COUNT(*) FROM story_views WHERE story_id=?", (sid,)); views=c.fetchone()[0]
        except: pass
        out.append({"id":sid,"username":r[1],"media_url":r[2],"text":r[3],"created_at":r[4],"views":views})
    conn.close(); return jsonify(out)

@app.route('/api/story', methods=['POST'])
def api_story():
    me=session.get('username'); file=request.files.get('media')
    if not file or not file.filename: return jsonify({"ok":False})
    import uuid; ext=file.filename.rsplit('.',1)[-1].lower(); name=str(uuid.uuid4())[:8]+'.'+ext; os.makedirs('static/uploads',exist_ok=True); path=os.path.join('static/uploads',name); file.save(path); url='/'+path
    conn=get_conn(); c=conn.cursor(); now=datetime.now(); exp=now+timedelta(hours=24)
    c.execute("INSERT INTO stories (username,media_url,text,created_at,expires_at) VALUES (%s,%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO stories (username,media_url,text,created_at,expires_at) VALUES (?,?,?,?,?)", (me,url,"",now.isoformat(),exp.isoformat()))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/api/story/text', methods=['POST'])
def api_story_text():
    me=session.get('username'); data=request.json; txt=data.get('text','')[:100]
    if not txt: return jsonify({"ok":False})
    conn=get_conn(); c=conn.cursor(); now=datetime.now(); exp=now+timedelta(hours=24)
    c.execute("INSERT INTO stories (username,media_url,text,created_at,expires_at) VALUES (%s,%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO stories (username,media_url,text,created_at,expires_at) VALUES (?,?,?,?,?)", (me,"",txt,now.isoformat(),exp.isoformat()))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/api/story/view', methods=['POST'])
def api_story_view():
    me=session.get('username'); data=request.json; sid=data.get('id'); conn=get_conn(); c=conn.cursor()
    try:
        c.execute("INSERT INTO story_views VALUES (%s,%s) ON CONFLICT DO NOTHING" if USE_POSTGRES else "INSERT OR IGNORE INTO story_views VALUES (?,?)", (sid,me)); conn.commit()
    except: pass
    conn.close(); return jsonify({"ok":True})

@app.route('/api/messages')
def api_messages():
    me=session.get('username'); other=request.args.get('with',''); conn=get_conn(); c=conn.cursor()
    c.execute("SELECT id,sender,text,media_url FROM messages WHERE (sender=%s AND receiver=%s) OR (sender=%s AND receiver=%s) ORDER BY id ASC" if USE_POSTGRES else "SELECT id,sender,text,media_url FROM messages WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) ORDER BY id ASC", (me,other,other,me))
    rows=c.fetchall(); out=[]
    for r in rows:
        mid=r[0]; reacts=""
        try: c.execute("SELECT emoji FROM msg_reacts WHERE msg_id=%s" if USE_POSTGRES else "SELECT emoji FROM msg_reacts WHERE msg_id=?", (mid,)); er=c.fetchall(); reacts=" ".join([x[0] for x in er])
        except: pass
        out.append({"id":mid,"sender":r[1],"text":r[2],"media_url":r[3],"reacts":reacts})
    conn.close(); return jsonify(out)

@app.route('/api/send', methods=['POST'])
def api_send():
    me=session.get('username')
    if not me: return jsonify({"ok":False})
    if request.is_json: data=request.json; other=data.get('receiver',''); txt=data.get('text','')[:500]; url=''
    else: other=request.form.get('receiver',''); txt=request.form.get('text','')[:500]; file=request.files.get('media'); url='';
        if file and file.filename:
            import uuid; ext=file.filename.rsplit('.',1)[-1].lower(); name=str(uuid.uuid4())[:8]+'.'+ext; os.makedirs('static/uploads',exist_ok=True); path=os.path.join('static/uploads',name); file.save(path); url='/'+path
    if not txt and not url: return jsonify({"ok":False})
    conn=get_conn(); c=conn.cursor(); now=datetime.now().isoformat()
    c.execute("INSERT INTO messages (sender,receiver,text,media_url,created_at) VALUES (%s,%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO messages (sender,receiver,text,media_url,created_at) VALUES (?,?,?,?,?)", (me,other,txt,url,now))
    conn.commit(); conn.close(); typing_map.pop((other,me),None); return jsonify({"ok":True})

@app.route('/api/typing', methods=['POST','GET'])
def api_typing():
    me=session.get('username')
    if request.method=='POST': data=request.json; other=data.get('receiver'); typing_map[(me,other)]=datetime.now(); return jsonify({"ok":True})
    else: other=request.args.get('with'); t=typing_map.get((other,me)); typing=False;
        if t and (datetime.now()-t).total_seconds()<3: typing=True
        return jsonify({"typing":typing})

@app.route('/api/react', methods=['POST'])
def api_react():
    me=session.get('username'); data=request.json; mid=data.get('msg_id'); emoji=data.get('emoji','❤️')[:2]; conn=get_conn(); c=conn.cursor()
    try:
        c.execute("INSERT INTO msg_reacts VALUES (%s,%s,%s) ON CONFLICT (msg_id,username) DO UPDATE SET emoji=%s" if USE_POSTGRES else "INSERT OR REPLACE INTO msg_reacts VALUES (?,?,?)", (mid,me,emoji,emoji) if USE_POSTGRES else (mid,me,emoji)); conn.commit()
    except: pass
    conn.close(); return jsonify({"ok":True})

@app.route('/static/uploads/<path:filename>')
def uploads(filename): return send_from_directory('static/uploads', filename)

@app.route('/logo.jpg')
def logo_jpg():
    if os.path.exists('logo.jpg'): return send_from_directory('.', 'logo.jpg')
    return "",404

@app.route('/logo-full.jpg')
def logo_full():
    if os.path.exists('logo-full.jpg'): return send_from_directory('.', 'logo-full.jpg')
    return "",404

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__=='__main__':
    port=int(os.environ.get("PORT",5000)); app.run(host='0.0.0.0',port=port)
