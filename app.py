import os
from flask import Flask, request, jsonify, render_template_string, session, redirect, send_file
from datetime import datetime, timedelta
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import cloudinary, cloudinary.uploader
app = Flask(__name__)
app.secret_key = "proveam-v205-final-fixed"
DB_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = bool(DB_URL)
CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME")
API_KEY = os.environ.get("CLOUDINARY_API_KEY")
API_SECRET = os.environ.get("CLOUDINARY_API_SECRET")
USE_CLOUD = bool(CLOUD_NAME and API_KEY and API_SECRET)
if USE_CLOUD:
    cloudinary.config(cloud_name=CLOUD_NAME, api_key=API_KEY, api_secret=API_SECRET, secure=True)

def save_media(data_url, mtype="image"):
    if not data_url: return data_url
    if data_url.startswith("http"): return data_url
    if not USE_CLOUD: return data_url
    try:
        res = cloudinary.uploader.upload(data_url, resource_type="auto", folder="proveam", quality="auto:low")
        return res.get("secure_url")
    except: return data_url

def get_conn():
    if USE_POSTGRES:
        try:
            import psycopg
            return psycopg.connect(DB_URL)
        except: import psycopg2; return psycopg2.connect(DB_URL)
    conn = sqlite3.connect("proveam.db", check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn(); c = conn.cursor()
    def safe(sql):
        try: c.execute(sql); conn.commit()
        except:
            try: conn.rollback()
            except: pass
    def q(pg, lite): return pg if USE_POSTGRES else lite
    safe(q("CREATE TABLE IF NOT EXISTS auth (username TEXT PRIMARY KEY, password TEXT, created_at TEXT, avatar TEXT, last_active TEXT)", "CREATE TABLE IF NOT EXISTS auth (username TEXT PRIMARY KEY, password TEXT, created_at TEXT, avatar TEXT, last_active TEXT)"))
    safe(q("CREATE TABLE IF NOT EXISTS posts (id SERIAL PRIMARY KEY, username TEXT, media TEXT, media_type TEXT, likes INT DEFAULT 0, created_at TEXT, expires_at TEXT)", "CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, media TEXT, media_type TEXT, likes INTEGER DEFAULT 0, created_at TEXT, expires_at TEXT)"))
    safe(q("CREATE TABLE IF NOT EXISTS likes (id SERIAL PRIMARY KEY, post_id INT, username TEXT)", "CREATE TABLE IF NOT EXISTS likes (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, username TEXT)"))
    safe(q("CREATE TABLE IF NOT EXISTS replies (id SERIAL PRIMARY KEY, post_id INT, username TEXT, text TEXT, created_at TEXT)", "CREATE TABLE IF NOT EXISTS replies (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER, username TEXT, text TEXT, created_at TEXT)"))
    safe(q("CREATE TABLE IF NOT EXISTS saved (id SERIAL PRIMARY KEY, username TEXT, post_id INT)", "CREATE TABLE IF NOT EXISTS saved (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, post_id INTEGER)"))
    try: conn.close()
    except: pass
init_db()
LOGIN_HTML = '''<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"><style>*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:#000;color:#fff;display:flex;justify-content:center;align-items:center;height:100vh}input{font-size:16px!important}.box{background:#111;border:1px solid #222;padding:28px;border-radius:20px;width:90%;max-width:360px;text-align:center}input{width:100%;padding:14px;background:#000;border:1px solid #333;color:#fff;border-radius:12px;margin:7px 0}.btn{width:100%;padding:14px;border:none;border-radius:12px;font-weight:800;margin-top:12px;background:linear-gradient(135deg,#D4AF37,#FFD700);color:#000}</style></head><body><div class="box"><h1 style="color:#D4AF37">PROVE AM</h1><p style="font-size:10px;letter-spacing:3px;color:#D4AF37">BY JERRICK SMITH</p><h3 id="title" style="margin-top:12px">Login</h3><input id="u" placeholder="Username"><input id="p" type="password" placeholder="Password"><button class="btn" onclick="doAuth()">Continue</button><p style="margin-top:14px"><a href="#" onclick="toggleMode()" id="tog" style="color:#D4AF37">No account? Sign Up</a></p><p id="msg" style="color:#f66"></p></div><script>let mode='login';function toggleMode(){mode=mode=='login'?'signup':'login';document.getElementById('title').innerText=mode=='login'?'Login':'Sign Up';document.getElementById('tog').innerText=mode=='login'?'No account? Sign Up':'Have account? Login'}async function doAuth(){let u=document.getElementById('u').value,p=document.getElementById('p').value;let r=await fetch('/'+mode,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})});let d=await r.json();if(d.ok)location.href='/';else document.getElementById('msg').innerText=d.error;}</script></body></html>'''

MAIN_HTML = '''<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css"><style>:root{--bg:#000;--card:#111;--text:#fff;--border:#222;--sub:#888}*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}html{-webkit-text-size-adjust:100%;touch-action:manipulation}body{background:var(--bg);color:var(--text)}input,textarea{font-size:16px!important}.header{position:sticky;top:0;z-index:10;background:var(--bg);border-bottom:1px solid var(--border);padding:12px;display:flex;justify-content:space-between;align-items:center}.top-tabs{display:flex;justify-content:space-around;border-bottom:1px solid var(--border)}.top-tabs a{color:var(--sub);text-decoration:none;font-weight:800;font-size:14px;padding:12px 0;width:33%;text-align:center}.top-tabs a.active{color:var(--text);border-bottom:2px solid var(--text)}.post{border-bottom:8px solid var(--card)}.post-top{padding:12px;display:flex;gap:10px;align-items:center}.post-top img{width:32px;height:32px;border-radius:50%}.post-media{width:100%;background:#111;display:flex;justify-content:center}.post-media img,.post-media video{width:100%;max-height:70vh;object-fit:contain}.post-actions{padding:12px;display:flex;gap:18px;font-size:20px}.fab{position:fixed;bottom:20px;right:20px;background:linear-gradient(135deg,#D4AF37,#FFD700);color:#000;width:56px;height:56px;border-radius:50%;border:none;font-size:28px;z-index:20}#sheetWrap{display:none;position:fixed;inset:0;z-index:100;background:#0009}#sheet{position:absolute;bottom:0;left:0;right:0;background:var(--card);border-radius:22px 22px 0 0;max-height:85vh;display:flex;flex-direction:column}</style></head><body><div class="header"><b style="color:#D4AF37">PROVE AM</b><div style="display:flex;gap:12px"><a href="/stories-page" style="color:var(--text);text-decoration:none">Stories</a><a href="/chats" style="color:var(--text);text-decoration:none">Chats</a><a href="/profile" style="color:var(--text);text-decoration:none">Profile</a></div></div><div class="top-tabs"><a href="/stories-page">Stories</a><a href="/" class="active">Posts</a><a href="/chats">Chats</a></div><div id="feed" style="min-height:60vh;padding-top:10px">Loading...</div><input type="file" id="fileIn" accept="image/*,video/*" multiple style="display:none"><button class="fab" onclick="fileIn.click()">+</button><div id="sheetWrap" onclick="if(event.target==this)closeSheet()"><div id="sheet"><div style="width:36px;height:4px;background:#666;border-radius:4px;margin:10px auto"></div><div id="commentList" style="overflow-y:auto;padding:12px;flex:1"></div><div style="display:flex;gap:10px;padding:10px;border-top:1px solid var(--border)"><input id="commentInput" placeholder="Add comment..." style="flex:1;background:var(--bg);border:1px solid var(--border);border-radius:20px;padding:10px 14px;color:var(--text)"></div></div></div><script>let allPosts=[];let curUser="";let avatars={};let activePost=null;async function compress(file){return new Promise(res=>{let img=new Image();let url=URL.createObjectURL(file);img.onload=()=>{let max=800,w=img.width,h=img.height;if(w>max||h>max){if(w>h){h=h*max/w;w=max;}else{w=w*max/h;h=max;}}let c=document.createElement('canvas');c.width=w;c.height=h;c.getContext('2d').drawImage(img,0,0,w,h);res(c.toDataURL('image/jpeg',0.45));URL.revokeObjectURL(url);};img.src=url;});}fileIn.addEventListener('change',async e=>{for(let f of e.target.files){let dataUrl=f.type.startsWith('image')?await compress(f):await new Promise(r=>{let fr=new FileReader();fr.onload=ev=>r(ev.target.result);fr.readAsDataURL(f);});let type=f.type.startsWith('video')?'video':'image';await fetch('/upload',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media:dataUrl,media_type:type})});}loadFeed();});function render(){if(!allPosts.length){feed.innerHTML='<div style="padding:60px;text-align:center;color:var(--sub)">No posts yet<br>Tap +</div>';return;}let html='';for(let p of allPosts){let av=avatars[p.username]||'https://i.pravatar.cc/100?u='+p.username;let mediaTag=p.media_type=='video'?'<video src="'+p.media+'" controls playsinline></video>':'<img src="'+p.media+'">';let del=p.username===curUser?'<button style="margin-left:auto;background:#f22;color:#fff;border:none;border-radius:8px;padding:4px 10px" onclick="deletePost('+p.id+')"><i class="fa fa-trash"></i></button>':'';let heart=p.liked?'<i class="fa-solid fa-heart" style="color:red"></i>':'<i class="fa-regular fa-heart"></i>';let save=p.saved?'<i class="fa-solid fa-bookmark" style="color:#D4AF37"></i>':'<i class="fa-regular fa-bookmark"></i>';html+='<div class="post"><div class="post-top"><img src="'+av+'"><b>'+p.username+'</b>'+del+'</div><div class="post-media">'+mediaTag+'</div><div class="post-actions"><span onclick="likePost('+p.id+')">'+heart+' '+p.likes+'</span><span onclick="openComments('+p.id+')"><i class="fa-regular fa-comment"></i></span><span style="margin-left:auto" onclick="savePost('+p.id+')">'+save+'</span></div></div>';}feed.innerHTML=html;}async function loadFeed(){let me=await (await fetch('/me')).json();curUser=me.username;avatars=await (await fetch('/avatars')).json();let data=await (await fetch('/feed')).json();allPosts=Array.isArray(data)?data:(data.posts||[]);render();}async function likePost(id){let p=allPosts.find(x=>x.id==id);if(p){p.liked=!p.liked;p.likes+=p.liked?1:-1;render();}await fetch('/like/'+id,{method:'POST'});}async function savePost(id){let p=allPosts.find(x=>x.id==id);if(p){p.saved=!p.saved;render();}await fetch('/save/'+id,{method:'POST'});}async function deletePost(id){if(!confirm('Delete?'))return;allPosts=allPosts.filter(p=>p.id!=id);render();await fetch('/delete/'+id,{method:'POST'});}function openComments(id){activePost=id;sheetWrap.style.display='block';loadComments(id);}function closeSheet(){sheetWrap.style.display='none';}async function loadComments(id){let r=await fetch('/replies/'+id);let reps=await r.json();let h='';for(let c of reps){h+='<div style="padding:8px 0"><b>'+c.username+'</b> '+c.text+'</div>';}commentList.innerHTML=h||'<div style="color:var(--sub)">No comments</div>';}commentInput.addEventListener('keydown',async e=>{if(e.key==='Enter'){let txt=e.target.value;e.target.value='';commentList.innerHTML+='<div><b>'+curUser+'</b> '+txt+'</div>';await fetch('/reply/'+activePost,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:txt})});loadComments(activePost);}});loadFeed();</script></body></html>'''

STORIES_HTML = '''<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"><style>*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:#000;color:#fff}input{font-size:16px!important}.header{padding:12px;border-bottom:1px solid #222;display:flex;justify-content:space-between}.story{padding:12px;border-bottom:1px solid #222;display:flex;gap:10px;align-items:center}.story img{width:40px;height:40px;border-radius:50%;border:2px solid #D4AF37}</style></head><body><div class="header"><a href="/" style="color:#D4AF37;text-decoration:none">← Back</a><b>Stories</b><input type="file" id="storyIn" accept="image/*,video/*" style="display:none"><button onclick="storyIn.click()" style="background:#D4AF37;border:none;padding:6px 12px;border-radius:8px">+ Story</button></div><div id="storyList">Loading...</div><script>async function loadStories(){let r=await fetch('/stories');let data=await r.json();let h='';for(let s of data){h+='<div class="story"><img src="https://i.pravatar.cc/100?u='+s.username+'"><b>'+s.username+'</b><span style="margin-left:auto;color:#888;font-size:12px">24h</span></div>';}document.getElementById('storyList').innerHTML=h||'No stories';}storyIn.addEventListener('change',async e=>{let f=e.target.files[0];if(!f)return;let dataUrl=await new Promise(r=>{let fr=new FileReader();fr.onload=ev=>r(ev.target.result);fr.readAsDataURL(f);});await fetch('/upload-story',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({media:dataUrl,media_type:f.type.startsWith('video')?'video':'image'})});loadStories();});loadStories();</script></body></html>'''

CHATS_HTML = '''<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"><style>*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:#000;color:#fff}input{font-size:16px!important}.header{padding:12px;border-bottom:1px solid #222;display:flex;justify-content:space-between}.chat-item{padding:14px;border-bottom:1px solid #111;display:flex;gap:12px;align-items:center}.chat-item img{width:36px;height:36px;border-radius:50%}</style></head><body><div class="header"><a href="/" style="color:#D4AF37;text-decoration:none">← Back</a><b>Chats</b></div><div id="userList">Loading users...</div><script>async function loadUsers(){let r=await fetch('/users');let users=await r.json();let h='';for(let u of users){h+='<div class="chat-item" onclick="location.href=`/chat/${u}`"><img src="https://i.pravatar.cc/100?u='+u+'"><b>'+u+'</b><span style="margin-left:auto;color:#D4AF37">→</span></div>';}document.getElementById('userList').innerHTML=h;}loadUsers();</script></body></html>'''
@app.route("/logo.jpg")
def logo_route():
    try: return send_file("logo.jpg")
    except: return "",404

@app.route("/login", methods=["POST"])
def login_route():
    d=request.get_json();u=d.get("username","").strip();p=d.get("password","")
    conn=get_conn();c=conn.cursor()
    c.execute("SELECT password FROM auth WHERE username=%s" if USE_POSTGRES else "SELECT password FROM auth WHERE username=?",(u,))
    row=c.fetchone()
    if not row: return jsonify({"error":"No user"}),404
    pw=row[0]
    if not check_password_hash(pw,p): return jsonify({"error":"Wrong pass"}),401
    session["username"]=u;conn.close();return jsonify({"ok":True})

@app.route("/signup", methods=["POST"])
def signup_route():
    d=request.get_json();u=d.get("username","").strip();p=d.get("password","")
    conn=get_conn();c=conn.cursor()
    c.execute("SELECT username FROM auth WHERE username=%s" if USE_POSTGRES else "SELECT username FROM auth WHERE username=?",(u,))
    if c.fetchone(): return jsonify({"error":"Exists"}),400
    c.execute("INSERT INTO auth (username,password,created_at) VALUES (%s,%s,%s)" if USE_POSTGRES else "INSERT INTO auth (username,password,created_at) VALUES (?,?,?)",(u,generate_password_hash(p),datetime.now().isoformat()))
    conn.commit();session["username"]=u;conn.close();return jsonify({"ok":True})

@app.route("/login-page")
def login_page(): return render_template_string(LOGIN_HTML)

@app.route("/")
def index():
    if "username" not in session: return redirect("/login-page")
    return render_template_string(MAIN_HTML)

@app.route("/stories-page")
def stories_page():
    if "username" not in session: return redirect("/login-page")
    return render_template_string(STORIES_HTML)

@app.route("/chats")
def chats_page():
    if "username" not in session: return redirect("/login-page")
    return render_template_string(CHATS_HTML)

@app.route("/me")
def me_route():
    if "username" not in session: return jsonify({}),401
    return jsonify({"username":session["username"]})

@app.route("/avatars")
def avatars_route():
    conn=get_conn();c=conn.cursor();c.execute("SELECT username,avatar FROM auth");rows=c.fetchall();conn.close()
    out={}
    for r in rows:
        try: out[r[0]]=r[1] or f"https://i.pravatar.cc/100?u={r[0]}"
        except: out[r["username"]]=r["avatar"]
    return jsonify(out)

@app.route("/users")
def users_route():
    conn=get_conn();c=conn.cursor();c.execute("SELECT username FROM auth");rows=c.fetchall();conn.close()
    out=[]
    for r in rows:
        try: out.append(r[0])
        except: out.append(r["username"])
    return jsonify(out)

@app.route("/feed")
def feed_route():
    if "username" not in session: return jsonify([]),401
    me=session["username"];conn=get_conn();c=conn.cursor()
    try: c.execute("DELETE FROM posts WHERE expires_at < %s" if USE_POSTGRES else "DELETE FROM posts WHERE expires_at <?",(datetime.now().isoformat(),))
    except: pass
    c.execute("SELECT id,username,media,media_type,likes FROM posts ORDER BY id DESC LIMIT 100");rows=c.fetchall();res=[]
    for r in rows:
        try: pid,un,med,mt,lk=r
        except: pid=r["id"];un=r["username"];med=r["media"];mt=r["media_type"];lk=r["likes"]
        c.execute("SELECT 1 FROM likes WHERE post_id=%s AND username=%s" if USE_POSTGRES else "SELECT 1 FROM likes WHERE post_id=? AND username=?",(pid,me))
        liked=bool(c.fetchone())
        c.execute("SELECT 1 FROM saved WHERE post_id=%s AND username=%s" if USE_POSTGRES else "SELECT 1 FROM saved WHERE post_id=? AND username=?",(pid,me))
        saved=bool(c.fetchone())
        res.append({"id":pid,"username":un,"media":med,"media_type":mt,"likes":lk or 0,"liked":liked,"saved":saved})
    conn.close();return jsonify(res)

@app.route("/upload", methods=["POST"])
def upload_route():
    if "username" not in session: return jsonify({}),401
    d=request.get_json();med=d.get("media");mt=d.get("media_type","image")
    url=save_media(med,mt);now=datetime.now();exp=(now+timedelta(days=7)).isoformat()
    conn=get_conn();c=conn.cursor()
    if USE_POSTGRES: c.execute("INSERT INTO posts (username,media,media_type,likes,created_at,expires_at) VALUES (%s,%s,%s,0,%s,%s)",(session["username"],url,mt,now.isoformat(),exp))
    else: c.execute("INSERT INTO posts (username,media,media_type,likes,created_at,expires_at) VALUES (?,?,?,?,?,?)",(session["username"],url,mt,0,now.isoformat(),exp))
    conn.commit();conn.close();return jsonify({"ok":True})

@app.route("/like/<int:pid>", methods=["POST"])
def like_route(pid):
    if "username" not in session: return jsonify({}),401
    me=session["username"];conn=get_conn();c=conn.cursor()
    c.execute("SELECT 1 FROM likes WHERE post_id=%s AND username=%s" if USE_POSTGRES else "SELECT 1 FROM likes WHERE post_id=? AND username=?",(pid,me))
    if c.fetchone():
        c.execute("DELETE FROM likes WHERE post_id=%s AND username=%s" if USE_POSTGRES else "DELETE FROM likes WHERE post_id=? AND username=?",(pid,me))
        c.execute("UPDATE posts SET likes=likes-1 WHERE id=%s" if USE_POSTGRES else "UPDATE posts SET likes=likes-1 WHERE id=?",(pid,))
    else:
        c.execute("INSERT INTO likes (post_id,username) VALUES (%s,%s)" if USE_POSTGRES else "INSERT INTO likes (post_id,username) VALUES (?,?)",(pid,me))
        c.execute("UPDATE posts SET likes=likes+1 WHERE id=%s" if USE_POSTGRES else "UPDATE posts SET likes=likes+1 WHERE id=?",(pid,))
    conn.commit();conn.close();return jsonify({"ok":True})

@app.route("/save/<int:pid>", methods=["POST"])
def save_route(pid):
    if "username" not in session: return jsonify({}),401
    me=session["username"];conn=get_conn();c=conn.cursor()
    c.execute("SELECT 1 FROM saved WHERE post_id=%s AND username=%s" if USE_POSTGRES else "SELECT 1 FROM saved WHERE post_id=? AND username=?",(pid,me))
    if c.fetchone(): c.execute("DELETE FROM saved WHERE post_id=%s AND username=%s" if USE_POSTGRES else "DELETE FROM saved WHERE post_id=? AND username=?",(pid,me))
    else: c.execute("INSERT INTO saved (username,post_id) VALUES (%s,%s)" if USE_POSTGRES else "INSERT INTO saved (username,post_id) VALUES (?,?)",(me,pid))
    conn.commit();conn.close();return jsonify({"ok":True})

@app.route("/delete/<int:pid>", methods=["POST"])
def delete_route(pid):
    if "username" not in session: return jsonify({}),401
    conn=get_conn();c=conn.cursor();c.execute("DELETE FROM posts WHERE id=%s AND username=%s" if USE_POSTGRES else "DELETE FROM posts WHERE id=? AND username=?",(pid,session["username"]))
    conn.commit();conn.close();return jsonify({"ok":True})

@app.route("/replies/<int:pid>")
def replies_route(pid):
    conn=get_conn();c=conn.cursor();c.execute("SELECT username,text,created_at FROM replies WHERE post_id=%s ORDER BY id ASC" if USE_POSTGRES else "SELECT username,text,created_at FROM replies WHERE post_id=? ORDER BY id ASC",(pid,));rows=c.fetchall();conn.close()
    out=[]
    for r in rows:
        try: out.append({"username":r[0],"text":r[1],"created_at":r[2]})
        except: out.append({"username":r["username"],"text":r["text"],"created_at":r["created_at"]})
    return jsonify(out)

@app.route("/reply/<int:pid>", methods=["POST"])
def reply_route(pid):
    if "username" not in session: return jsonify({}),401
    d=request.get_json();txt=d.get("text","").strip()
    conn=get_conn();c=conn.cursor()
    if USE_POSTGRES: c.execute("INSERT INTO replies (post_id,username,text,created_at) VALUES (%s,%s,%s,%s)",(pid,session["username"],txt,datetime.now().isoformat()))
    else: c.execute("INSERT INTO replies (post_id,username,text,created_at) VALUES (?,?,?,?)",(pid,session["username"],txt,datetime.now().isoformat()))
    conn.commit();conn.close();return jsonify({"ok":True})

@app.route("/stories")
def stories_route():
    conn=get_conn();c=conn.cursor()
    try: c.execute("DELETE FROM stories WHERE expires_at < %s" if USE_POSTGRES else "DELETE FROM stories WHERE expires_at <?",(datetime.now().isoformat(),))
    except: pass
    c.execute("SELECT id,username,media,media_type,created_at FROM stories ORDER BY id DESC LIMIT 50");rows=c.fetchall();conn.close()
    out=[]
    for r in rows:
        try: out.append({"id":r[0],"username":r[1],"media":r[2],"media_type":r[3],"created_at":r[4]})
        except: out.append({"id":r["id"],"username":r["username"],"media":r["media"],"media_type":r["media_type"],"created_at":r["created_at"]})
    return jsonify(out)

@app.route("/upload-story", methods=["POST"])
def upload_story_route():
    if "username" not in session: return jsonify({}),401
    d=request.get_json();med=d.get("media");mt=d.get("media_type","image")
    url=save_media(med,mt);now=datetime.now();exp=(now+timedelta(hours=24)).isoformat()
    conn=get_conn();c=conn.cursor()
    if USE_POSTGRES: c.execute("INSERT INTO stories (username,media,media_type,created_at,expires_at) VALUES (%s,%s,%s,%s,%s)",(session["username"],url,mt,now.isoformat(),exp))
    else: c.execute("INSERT INTO stories (username,media,media_type,created_at,expires_at) VALUES (?,?,?,?,?)",(session["username"],url,mt,now.isoformat(),exp))
    conn.commit();conn.close();return jsonify({"ok":True})

@app.route("/profile")
def profile_route():
    if "username" not in session: return redirect("/login-page")
    return f'<html><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"><style>body{{background:#000;color:#fff;font-family:system-ui;padding:20px}}a{{color:#D4AF37}}</style></head><body><a href="/">← Back</a><h2>{session["username"]}</h2><p>PROVE AM BY JERRICK SMITH 2026</p><a href="/logout" style="color:#f66">Logout</a></body></html>'

@app.route("/logout")
def logout_route(): session.clear(); return redirect("/login-page")

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))
