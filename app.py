import os, uuid, json
from flask import Flask, request, jsonify, session, render_template_string, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY','prove-am-secret-2026-v37')

# --- FIX 1: UPLOAD FOLDER ABSOLUTE ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
ALLOWED_EXT = {'png','jpg','jpeg','gif','webp','mp4','mov','avi'}

DB_URL = os.environ.get('DATABASE_URL','')
USE_POSTGRES = DB_URL.startswith('postgres')

def get_conn():
    if USE_POSTGRES:
        return psycopg2.connect(DB_URL, sslmode='require')
    import sqlite3
    conn = sqlite3.connect(os.path.join(BASE_DIR,'prove.db'))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn(); c = conn.cursor()
    if USE_POSTGRES:
        c.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS profiles (username TEXT PRIMARY KEY, pic_url TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS posts (id SERIAL PRIMARY KEY, username TEXT, caption TEXT, image TEXT, likes INT DEFAULT 0, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS friends (id SERIAL PRIMARY KEY, sender TEXT, receiver TEXT, status TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS messages (id SERIAL PRIMARY KEY, sender TEXT, receiver TEXT, text TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS likes (id SERIAL PRIMARY KEY, post_id INT, username TEXT)")
    else:
        c.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS profiles (username TEXT PRIMARY KEY, pic_url TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, caption TEXT, image TEXT, likes INT DEFAULT 0, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS friends (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, receiver TEXT, status TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, receiver TEXT, text TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS likes (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INT, username TEXT)")
    conn.commit(); conn.close()
init_db()

def ensure_profile(username):
    try:
        conn=get_conn(); c=conn.cursor()
        if USE_POSTGRES:
            c.execute("INSERT INTO profiles (username,pic_url) VALUES (%s,%s) ON CONFLICT (username) DO NOTHING", (username,""))
        else:
            c.execute("INSERT OR IGNORE INTO profiles (username,pic_url) VALUES (?,?)", (username,""))
        conn.commit(); conn.close()
    except Exception as e:
        print(f"ensure_profile {e}")

HTML = r"""
<!DOCTYPE html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{background:#000;color:#fff;font-family:Arial;margin:0}
.header{display:flex;justify-content:space-between;padding:10px;background:#111;position:sticky;top:0}
.post{background:#111;margin:10px;border-radius:10px;padding:10px}
.post-img{width:100%;max-height:500px;object-fit:contain;border-radius:10px;background:#222}
.btn{background:#fff;color:#000;padding:6px 12px;border-radius:20px;border:0;margin:2px}
.low{position:fixed;top:60px;right:10px;z-index:99;background:orange;color:#000;padding:5px 10px;border-radius:10px}
</style></head><body>
<div class="header"><b>PROVE AM</b><span><a href="/logout" style="color:#fff">Logout</a> - {{me}}</span></div>
<button class="low" id="lowBtn" onclick="toggleLow()">Low: OFF</button>
<div style="padding:10px">
<input id="caption" placeholder="What's on your mind?" style="width:70%;padding:10px;border-radius:20px">
<input type="file" id="file" accept="image/*,video/*" style="display:none" onchange="previewFile()">
<button class="btn" onclick="document.getElementById('file').click()">📎 Tap for pic/video</button>
<button class="btn" onclick="sendPost()">SEND POST (Public)</button>
<div id="preview"></div>
<div style="margin-top:15px"><input id="searchQ" placeholder="Search users e.g Jerrick Smith" style="width:60%;padding:8px;border-radius:20px" oninput="doSearch()"><div id="searchRes"></div></div>
</div>
<div id="posts"></div>
<script>
let lowMode=false;
function toggleLow(){lowMode=!lowMode;document.getElementById('lowBtn').innerText=lowMode?'Low: ON':'Low: OFF';document.getElementById('lowBtn').style.background=lowMode?'yellow':'orange'}
let selectedFile=null;
function previewFile(){
 const f=document.getElementById('file').files[0]; if(!f)return; selectedFile=f;
 const r=document.getElementById('preview'); r.innerHTML='Selected: '+f.name;
}
async function sendPost(){
 const cap=document.getElementById('caption').value;
 if(!cap &&!selectedFile){alert('Type something or pick pic');return}
 const fd=new FormData(); fd.append('caption',cap);
 if(selectedFile &&!lowMode) fd.append('image',selectedFile);
 const res=await fetch('/api/post',{method:'POST',body:fd}); const j=await res.json();
 if(j.ok){document.getElementById('caption').value='';selectedFile=null;document.getElementById('preview').innerHTML='';document.getElementById('file').value='';loadPosts()}else alert('Post failed '+JSON.stringify(j))
}
async function loadPosts(){
 const res=await fetch('/api/posts'); const data=await res.json();
 const div=document.getElementById('posts'); div.innerHTML='';
 data.forEach(p=>{
   let imgHtml='';
   if(p.image){
     if(p.image.startsWith('http')) imgHtml=`<img src="${p.image}" class="post-img" onerror="this.style.display='none'">`;
     else imgHtml=`<img src="/${p.image}" class="post-img" onerror="this.style.display='none'">`;
   }
   div.innerHTML+=`<div class="post"><b>${p.username}</b> <small>${p.date}</small><p>${p.caption||''}</p>${imgHtml}<div><button class="btn" onclick="likePost(${p.id})">❤️ ${p.likes||0}</button></div></div>`;
 });
}
async function doSearch(){
 const q=document.getElementById('searchQ').value; if(q.length<2){document.getElementById('searchRes').innerHTML='';return}
 const res=await fetch('/api/search?q='+encodeURIComponent(q)); const users=await res.json();
 const div=document.getElementById('searchRes'); if(users.length==0){div.innerHTML='<p style="color:#888">No users found</p>';return}
 div.innerHTML=users.map(u=>`<div style="display:flex;justify-content:space-between;background:#222;margin:5px;padding:8px;border-radius:10px"><span>${u.username} (${u.friend_status})</span><button class="btn" onclick="addFriend('${u.username}')">+ Add</button></div>`).join('');
}
async function addFriend(u){await fetch('/api/add_friend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u})});alert('Request sent to '+u);doSearch()}
async function likePost(id){await fetch('/api/like/'+id,{method:'POST'});loadPosts()}
loadPosts();
</script></body></html>
"""

@app.route('/')
def home():
    if 'username' not in session: return redirect('/login')
    ensure_profile(session['username'])
    return render_template_string(HTML, me=session['username'])

@app.route('/login')
def login_page():
    if 'username' in session: return redirect('/')
    return render_template_string("""
    <body style="background:#000;color:#fff;font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh">
    <form method=post action=/auth style="background:#111;padding:20px;border-radius:15px;width:80%;max-width:350px">
    <h2>PROVE AM Login</h2><input name=username placeholder="Username e.g Jerrick Smith" style="width:100%;padding:12px;margin:5px 0;border-radius:20px;border:0"><br>
    <input name=password type=password placeholder="Password" style="width:100%;padding:12px;margin:5px 0;border-radius:20px;border:0"><br>
    <button style="width:100%;padding:12px;border-radius:20px;border:0;background:#fff;color:#000;font-weight:bold;margin-top:10px">Login / Signup</button>
    </form></body>
    """)

@app.route('/auth', methods=['POST'])
def auth():
    u=request.form.get('username','').strip(); p=request.form.get('password','').strip()
    if not u or not p: return "missing",400
    conn=get_conn(); c=conn.cursor()
    try:
        if USE_POSTGRES:
            c.execute("SELECT password FROM users WHERE username=%s",(u,)); row=c.fetchone()
            if not row: c.execute("INSERT INTO users (username,password) VALUES (%s,%s)",(u,p))
            elif row[0]!=p: conn.close(); return "wrong password",401
        else:
            c.execute("SELECT password FROM users WHERE username=?",(u,)); row=c.fetchone()
            if not row: c.execute("INSERT INTO users (username,password) VALUES (?,?)",(u,p))
            elif row[0]!=p: conn.close(); return "wrong password",401
        conn.commit()
    except Exception as e:
        print(e)
    conn.close()
    session['username']=u
    ensure_profile(u)
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear(); return redirect('/login')

@app.route('/api/post', methods=['POST'])
def api_post():
    me=session.get('username')
    if not me: return jsonify({"error":"login"}),401
    caption=request.form.get('caption','')
    file=request.files.get('image')
    image_path=""
    if file and file.filename!='':
        ext=file.filename.rsplit('.',1)[-1].lower()
        if ext in ALLOWED_EXT:
            if os.environ.get('CLOUDINARY_CLOUD_NAME'):
                try:
                    import cloudinary, cloudinary.uploader
                    cloudinary.config(cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'), api_key=os.environ.get('CLOUDINARY_API_KEY'), api_secret=os.environ.get('CLOUDINARY_API_SECRET'))
                    res=cloudinary.uploader.upload(file, resource_type="auto")
                    image_path=res.get('secure_url','')
                except Exception as e:
                    print(f"CLOUDINARY FAIL {e}")
                    fname=f"{uuid.uuid4().hex}.{ext}"; local_path=os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(fname)); file.seek(0); file.save(local_path); image_path=f"static/uploads/{fname}"
            else:
                fname=f"{uuid.uuid4().hex}.{ext}"; local_path=os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(fname)); file.save(local_path); image_path=f"static/uploads/{fname}"
                print(f"SAVED {local_path} exists={os.path.exists(local_path)}")
    conn=get_conn(); c=conn.cursor(); now=datetime.now().strftime("%a, %d %b %Y %I:%M %p")
    if USE_POSTGRES: c.execute("INSERT INTO posts (username,caption,image,created_at) VALUES (%s,%s,%s,%s)",(me,caption,image_path,now))
    else: c.execute("INSERT INTO posts (username,caption,image,created_at) VALUES (?,?,?,?)",(me,caption,image_path,now))
    conn.commit(); conn.close(); ensure_profile(me)
    return jsonify({"ok":True})

@app.route('/api/posts')
def api_posts():
    conn=get_conn(); c=conn.cursor()
    try:
        c.execute("SELECT username,caption,image,created_at,id,likes FROM posts ORDER BY id DESC LIMIT 100")
        rows=c.fetchall()
    except:
        c.execute("SELECT username,caption,image,created_at,id FROM posts ORDER BY id DESC LIMIT 100"); rows=c.fetchall()
    conn.close()
    out=[]
    for r in rows:
        if isinstance(r, dict) or hasattr(r, 'keys'):
            username=r['username']; caption=r['caption']; image=r['image']; date=r['created_at']; pid=r['id']; likes=r.get('likes',0) if isinstance(r, dict) else 0
        else:
            username=r[0]; caption=r[1]; image=r[2]; date=r[3]; pid=r[4]; likes=r[5] if len(r)>5 else 0
        out.append({"username":username,"caption":caption,"image":image or "","date":date,"id":pid,"likes":likes})
    return jsonify(out)

@app.route('/api/search')
def api_search():
    me=session.get('username')
    q=(request.args.get('q','') or '').strip().lower()
    conn=get_conn()
    c=conn.cursor()
    try:
        if q:
            like=f"%{q}%"
            like2=f"%{q.split()[0]}%" if ' ' in q else like
            if USE_POSTGRES:
                c.execute("SELECT username,pic_url FROM profiles WHERE LOWER(username) LIKE %s OR LOWER(username) LIKE %s LIMIT 30",(like,like2))
            else:
                c.execute("SELECT username,pic_url FROM profiles WHERE LOWER(username) LIKE? OR LOWER(username) LIKE? LIMIT 30",(like,like2))
        else:
            c.execute("SELECT username,pic_url FROM profiles LIMIT 30")
        users=c.fetchall()
    except Exception as e:
        print(f"SEARCH ERROR: {e}")
        users=[]
    try:
        if USE_POSTGRES:
            c.execute("SELECT sender,receiver,status FROM friends WHERE sender=%s OR receiver=%s",(me,me))
        else:
            c.execute("SELECT sender,receiver,status FROM friends WHERE sender=? OR receiver=?",(me,me))
        fr=c.fetchall()
    except:
        fr=[]
    status_map={}
    for row in fr:
        if hasattr(row,'keys'):
            s=row['sender']; r=row['receiver']; st=row['status']
        else:
            s=row[0]; r=row[1]; st=row[2]
        if s==me:
            status_map[r]='friends' if st=='accepted' else 'pending_sent'
        else:
            status_map[s]='friends' if st=='accepted' else 'pending_received'
    out=[]
    for row in users:
        if hasattr(row,'keys'):
            u=row['username']; pic=row['pic_url']
        else:
            u=row[0]; pic=row[1]
        if u==me:
            continue
        out.append({"username":u,"pic_url":pic or "","friend_status":status_map.get(u,'none')})
    conn.close()
    return jsonify(out)

@app.route('/api/add_friend', methods=['POST'])
def add_friend():
    me=session.get('username'); data=request.get_json(); target=data.get('username')
    if not me or not target: return jsonify({"error":"missing"}),400
    conn=get_conn(); c=conn.cursor()
    if USE_POSTGRES:
        c.execute("SELECT * FROM friends WHERE (sender=%s AND receiver=%s) OR (sender=%s AND receiver=%s)",(me,target,target,me))
    else:
        c.execute("SELECT * FROM friends WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?)",(me,target,target,me))
    if c.fetchone(): conn.close(); return jsonify({"ok":False,"msg":"already"})
    if USE_POSTGRES:
        c.execute("INSERT INTO friends (sender,receiver,status) VALUES (%s,%s,%s)",(me,target,'pending'))
    else:
        c.execute("INSERT INTO friends (sender,receiver,status) VALUES (?,?,?)",(me,target,'pending'))
    conn.commit(); conn.close()
    return jsonify({"ok":True})

@app.route('/api/like/<int:pid>', methods=['POST'])
def like_post(pid):
    me=session.get('username')
    conn=get_conn(); c=conn.cursor()
    try:
        if USE_POSTGRES:
            c.execute("SELECT id FROM likes WHERE post_id=%s AND username=%s",(pid,me))
        else:
            c.execute("SELECT id FROM likes WHERE post_id=? AND username=?",(pid,me))
        if not c.fetchone():
            if USE_POSTGRES:
                c.execute("INSERT INTO likes (post_id,username) VALUES (%s,%s)",(pid,me))
                c.execute("UPDATE posts SET likes = COALESCE(likes,0)+1 WHERE id=%s",(pid,))
            else:
                c.execute("INSERT INTO likes (post_id,username) VALUES (?,?)",(pid,me))
                c.execute("UPDATE posts SET likes = COALESCE(likes,0)+1 WHERE id=?",(pid,))
            conn.commit()
    except Exception as e:
        print(e)
    conn.close()
    return jsonify({"ok":True})

@app.route('/api/fix_profiles')
def fix_profiles():
    conn=get_conn(); c=conn.cursor()
    if USE_POSTGRES:
        c.execute("SELECT username FROM users")
    else:
        c.execute("SELECT username FROM users")
    users=c.fetchall()
    count=0
    for row in users:
        uname=row[0] if not hasattr(row,'keys') else row['username']
        ensure_profile(uname); count+=1
    conn.close()
    return f"Fixed {count} profiles - Now search will work! Go home and search Jerrick"

@app.route('/static/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',10000)), debug=True)
