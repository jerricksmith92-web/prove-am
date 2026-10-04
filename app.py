import os, uuid, json, random, traceback
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "prove-am-2026-final")
DB_URL = os.environ.get("DATABASE_URL", "")
USE_POSTGRES = DB_URL.startswith("postgres")
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

try:
    import cloudinary, cloudinary.uploader
    cloudinary.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key=os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_API_SECRET"),
        secure=True
    )
    HAS_CLOUD = bool(os.getenv("CLOUDINARY_CLOUD_NAME"))
except:
    HAS_CLOUD = False

def upload_to_cloud(file_storage):
    if HAS_CLOUD:
        try:
            res = cloudinary.uploader.upload(file_storage, resource_type="auto", folder="proveam")
            return res.get("secure_url")
        except Exception as e:
            print(f"Cloud fail {e}")
    try:
        ext = file_storage.filename.rsplit('.',1)[-1] if '.' in file_storage.filename else 'jpg'
        fname = f"{uuid.uuid4().hex}.{ext}"
        path = os.path.join(UPLOAD_FOLDER, fname)
        file_storage.save(path)
        return f"/static/uploads/{fname}"
    except Exception as e:
        print(f"Local fail {e}")
        return None

def get_conn():
    if USE_POSTGRES:
        try:
            import psycopg2
            return psycopg2.connect(DB_URL)
        except:
            import psycopg
            return psycopg.connect(DB_URL)
    import sqlite3
    conn = sqlite3.connect('app.db')
    return conn

def init_db():
    conn=get_conn(); c=conn.cursor()
    stmts = []
    if USE_POSTGRES:
        stmts = [
            "CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username TEXT UNIQUE, email TEXT, password TEXT, bio TEXT, profile_pic TEXT, is_verified BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT NOW())",
            "CREATE TABLE IF NOT EXISTS posts (id SERIAL PRIMARY KEY, user_id INTEGER, content TEXT, image TEXT, video TEXT, likes_count INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT NOW())",
            "CREATE TABLE IF NOT EXISTS likes (id SERIAL PRIMARY KEY, user_id INTEGER, post_id INTEGER, created_at TIMESTAMP DEFAULT NOW(), UNIQUE(user_id, post_id))",
            "CREATE TABLE IF NOT EXISTS comments (id SERIAL PRIMARY KEY, user_id INTEGER, post_id INTEGER, content TEXT, created_at TIMESTAMP DEFAULT NOW())",
            "CREATE TABLE IF NOT EXISTS messages (id SERIAL PRIMARY KEY, sender_id INTEGER, receiver_id INTEGER, content TEXT, reply_to INTEGER, is_deleted BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT NOW())",
            "CREATE TABLE IF NOT EXISTS stories (id SERIAL PRIMARY KEY, user_id INTEGER, image TEXT, video TEXT, created_at TIMESTAMP DEFAULT NOW(), expires_at TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS user_status (id INTEGER PRIMARY KEY, last_seen TIMESTAMP DEFAULT NOW(), online BOOLEAN DEFAULT FALSE)",
            "CREATE TABLE IF NOT EXISTS notifications (id SERIAL PRIMARY KEY, user_id INTEGER, from_user_id INTEGER, type TEXT, post_id INTEGER, is_read BOOLEAN DEFAULT FALSE, created_at TIMESTAMP DEFAULT NOW())",
            "CREATE TABLE IF NOT EXISTS follows (id SERIAL PRIMARY KEY, follower_id INTEGER, following_id INTEGER, created_at TIMESTAMP DEFAULT NOW(), UNIQUE(follower_id, following_id))"
        ]
    else:
        stmts = [
            "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, email TEXT, password TEXT, bio TEXT, profile_pic TEXT, is_verified BOOLEAN DEFAULT 0, created_at TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, content TEXT, image TEXT, video TEXT, likes_count INTEGER DEFAULT 0, created_at TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS likes (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, post_id INTEGER, created_at TIMESTAMP, UNIQUE(user_id, post_id))",
            "CREATE TABLE IF NOT EXISTS comments (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, post_id INTEGER, content TEXT, created_at TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id INTEGER, receiver_id INTEGER, content TEXT, reply_to INTEGER, is_deleted BOOLEAN DEFAULT 0, created_at TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS stories (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, image TEXT, video TEXT, created_at TIMESTAMP, expires_at TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS user_status (id INTEGER PRIMARY KEY, last_seen TIMESTAMP, online BOOLEAN)",
            "CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, from_user_id INTEGER, type TEXT, post_id INTEGER, is_read BOOLEAN DEFAULT 0, created_at TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS follows (id INTEGER PRIMARY KEY AUTOINCREMENT, follower_id INTEGER, following_id INTEGER, created_at TIMESTAMP, UNIQUE(follower_id, following_id))"
        ]
    for s in stmts:
        try: c.execute(s)
        except Exception as e: print(e)
    conn.commit(); conn.close()
init_db()

def login_required(f):
    @wraps(f)
    def wrapper(*a,**kw):
        if not session.get('user_id'): return jsonify({"error":"login"}),401
        return f(*a,**kw)
    return wrapper

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.form if request.form else request.get_json() or {}
    username = data.get('username'); email=data.get('email'); password=data.get('password')
    if not username or not password: return jsonify({"error":"Missing"}),400
    conn=get_conn(); c=conn.cursor()
    try:
        hashed=generate_password_hash(password)
        pic=None
        if 'profile_pic' in request.files and request.files['profile_pic'].filename:
            pic=upload_to_cloud(request.files['profile_pic'])
        if USE_POSTGRES:
            c.execute("INSERT INTO users (username,email,password,profile_pic) VALUES (%s,%s,%s,%s) RETURNING id", (username,email,hashed,pic))
            uid=c.fetchone()[0]
        else:
            c.execute("INSERT INTO users (username,email,password,profile_pic,created_at) VALUES (?,?,?,?,?)", (username,email,hashed,pic,datetime.now()))
            uid=c.lastrowid
        conn.commit()
        session['user_id']=uid
        return jsonify({"id":uid,"username":username,"profile_pic":pic})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error":str(e)}),400
    finally:
        conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    data=request.get_json() or {}
    u=data.get('username'); p=data.get('password')
    conn=get_conn(); c=conn.cursor()
    q="SELECT id,username,password,profile_pic,bio FROM users WHERE username=%s" if USE_POSTGRES else "SELECT id,username,password,profile_pic,bio FROM users WHERE username=?"
    c.execute(q,(u,)); row=c.fetchone(); conn.close()
    if not row: return jsonify({"error":"User not found"}),404
    uid,uname,pw,pic,bio=row[0],row[1],row[2],row[3],row[4] if len(row)>4 else ""
    if not (check_password_hash(pw,p) or pw==p): return jsonify({"error":"Wrong password"}),401
    session['user_id']=uid
    return jsonify({"id":uid,"username":uname,"profile_pic":pic,"bio":bio})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear(); return jsonify({"success":True})

@app.route('/api/me')
def me():
    uid=session.get('user_id')
    if not uid: return jsonify({"error":"not logged"}),401
    conn=get_conn(); c=conn.cursor()
    q="SELECT id,username,profile_pic,bio FROM users WHERE id=%s" if USE_POSTGRES else "SELECT id,username,profile_pic,bio FROM users WHERE id=?"
    c.execute(q,(uid,)); r=c.fetchone(); conn.close()
    if not r: return jsonify({"error":"no"}),404
    return jsonify({"id":r[0],"username":r[1],"profile_pic":r[2],"bio":r[3]})

@app.route('/api/users')
def users_list():
    conn=get_conn(); c=conn.cursor()
    c.execute("SELECT id,username,profile_pic,bio FROM users ORDER BY id DESC")
    rows=c.fetchall(); conn.close()
    return jsonify([{"id":r[0],"username":r[1],"profile_pic":r[2],"bio":r[3]} for r in rows])

@app.route('/api/posts', methods=['GET','POST'])
def posts():
    uid=session.get('user_id')
    if request.method=='GET':
        conn=get_conn(); c=conn.cursor()
        c.execute("SELECT p.id,p.content,p.image,p.video,p.likes_count,p.created_at,u.username,u.profile_pic,u.id, (SELECT COUNT(*) FROM comments WHERE post_id=p.id) as ccount FROM posts p JOIN users u ON p.user_id=u.id ORDER BY p.id DESC LIMIT 100")
        rows=c.fetchall()
        out=[]
        for r in rows:
            out.append({"id":r[0],"content":r[1],"image":r[2],"video":r[3],"likes_count":r[4],"created_at":str(r[5]),"username":r[6],"profile_pic":r[7],"user_id":r[8],"comments_count":r[9]})
        conn.close()
        return jsonify(out)
    else:
        if not uid: return jsonify({"error":"login"}),401
        content=request.form.get('content','') if request.form else (request.get_json() or {}).get('content','')
        img=None; vid=None
        if 'image' in request.files and request.files['image'].filename:
            f=request.files['image']
            url=upload_to_cloud(f)
            if f.filename.lower().endswith(('.mp4','.mov','.avi','.webm')):
                vid=url
            else:
                img=url
        conn=get_conn(); c=conn.cursor()
        if USE_POSTGRES:
            c.execute("INSERT INTO posts (user_id,content,image,video) VALUES (%s,%s,%s,%s) RETURNING id", (uid,content,img,vid))
            pid=c.fetchone()[0]
        else:
            c.execute("INSERT INTO posts (user_id,content,image,video,created_at) VALUES (?,?,?,?,?)", (uid,content,img,vid,datetime.now()))
            pid=c.lastrowid
        conn.commit(); conn.close()
        return jsonify({"id":pid,"success":True})

@app.route('/api/posts/<int:post_id>/like', methods=['POST'])
@login_required
def like_post(post_id):
    uid=session.get('user_id')
    conn=get_conn(); c=conn.cursor()
    try:
        if USE_POSTGRES:
            c.execute("SELECT id FROM likes WHERE user_id=%s AND post_id=%s", (uid,post_id))
            exists=c.fetchone()
            if exists:
                c.execute("DELETE FROM likes WHERE user_id=%s AND post_id=%s", (uid,post_id))
                c.execute("UPDATE posts SET likes_count=likes_count-1 WHERE id=%s", (post_id,))
                conn.commit()
                return jsonify({"liked":False})
            else:
                c.execute("INSERT INTO likes (user_id,post_id) VALUES (%s,%s)", (uid,post_id))
                c.execute("UPDATE posts SET likes_count=likes_count+1 WHERE id=%s", (post_id,))
                conn.commit()
                return jsonify({"liked":True})
        else:
            c.execute("SELECT id FROM likes WHERE user_id=? AND post_id=?", (uid,post_id))
            exists=c.fetchone()
            if exists:
                c.execute("DELETE FROM likes WHERE user_id=? AND post_id=?", (uid,post_id))
                c.execute("UPDATE posts SET likes_count=likes_count-1 WHERE id=?", (post_id,))
                conn.commit()
                return jsonify({"liked":False})
            else:
                c.execute("INSERT INTO likes (user_id,post_id,created_at) VALUES (?,?,?)", (uid,post_id,datetime.now()))
                c.execute("UPDATE posts SET likes_count=likes_count+1 WHERE id=?", (post_id,))
                conn.commit()
                return jsonify({"liked":True})
    finally:
        conn.close()

@app.route('/api/posts/<int:post_id>/comments', methods=['GET','POST'])
def comments(post_id):
    uid=session.get('user_id')
    conn=get_conn(); c=conn.cursor()
    if request.method=='GET':
        c.execute("SELECT c.id,c.content,c.created_at,u.username,u.profile_pic FROM comments c JOIN users u ON c.user_id=u.id WHERE c.post_id=%s ORDER BY c.id ASC" if USE_POSTGRES else "SELECT c.id,c.content,c.created_at,u.username,u.profile_pic FROM comments c JOIN users u ON c.user_id=u.id WHERE c.post_id=? ORDER BY c.id ASC", (post_id,))
        rows=c.fetchall(); conn.close()
        return jsonify([{"id":r[0],"content":r[1],"created_at":str(r[2]),"username":r[3],"profile_pic":r[4]} for r in rows])
    else:
        if not uid: return jsonify({"error":"login"}),401
        data=request.get_json() or {}
        content=data.get('content')
        if not content: return jsonify({"error":"empty"}),400
        if USE_POSTGRES:
            c.execute("INSERT INTO comments (user_id,post_id,content) VALUES (%s,%s,%s) RETURNING id", (uid,post_id,content))
            cid=c.fetchone()[0]
        else:
            c.execute("INSERT INTO comments (user_id,post_id,content,created_at) VALUES (?,?,?,?)", (uid,post_id,content,datetime.now()))
            cid=c.lastrowid
        conn.commit(); conn.close()
        return jsonify({"id":cid,"success":True})

@app.route('/api/stories', methods=['GET','POST'])
def stories():
    uid=session.get('user_id')
    conn=get_conn(); c=conn.cursor()
    if request.method=='GET':
        q="SELECT s.id,s.image,s.video,s.created_at,u.username,u.profile_pic,u.id FROM stories s JOIN users u ON s.user_id=u.id WHERE s.expires_at > NOW() ORDER BY s.id DESC" if USE_POSTGRES else "SELECT s.id,s.image,s.video,s.created_at,u.username,u.profile_pic,u.id FROM stories s JOIN users u ON s.user_id=u.id WHERE datetime(s.expires_at) > datetime('now') ORDER BY s.id DESC"
        c.execute(q); rows=c.fetchall(); conn.close()
        return jsonify([{"id":r[0],"image":r[1],"video":r[2],"created_at":str(r[3]),"username":r[4],"profile_pic":r[5],"user_id":r[6]} for r in rows])
    else:
        if not uid: return jsonify({"error":"login"}),401
        img=None; vid=None
        if 'file' in request.files and request.files['file'].filename:
            f=request.files['file']
            url=upload_to_cloud(f)
            if f.filename.lower().endswith(('.mp4','.mov','.avi','.webm')):
                vid=url
            else:
                img=url
        exp=datetime.now()+timedelta(hours=24)
        if USE_POSTGRES:
            c.execute("INSERT INTO stories (user_id,image,video,created_at,expires_at) VALUES (%s,%s,%s,%s,%s)", (uid,img,vid,datetime.now(),exp))
        else:
            c.execute("INSERT INTO stories (user_id,image,video,created_at,expires_at) VALUES (?,?,?,?,?)", (uid,img,vid,datetime.now(),exp))
        conn.commit(); conn.close()
        return jsonify({"success":True})

@app.route('/api/chat/list')
def chat_list():
    uid=session.get('user_id')
    if not uid: return jsonify([])
    conn=get_conn(); c=conn.cursor()
    try:
        if USE_POSTGRES:
            c.execute("""
                SELECT u.id,u.username,u.profile_pic,
                (SELECT content FROM messages WHERE ((sender_id=u.id AND receiver_id=%s) OR (sender_id=%s AND receiver_id=u.id)) AND is_deleted=FALSE ORDER BY id DESC LIMIT 1) as last_msg,
                (SELECT COUNT(*) FROM messages WHERE sender_id=u.id AND receiver_id=%s AND is_deleted=FALSE) as unread,
                COALESCE(us.online,FALSE) as online
                FROM users u LEFT JOIN user_status us ON us.id=u.id WHERE u.id!=%s ORDER BY u.id DESC
            """, (uid,uid,uid,uid))
        else:
            c.execute("SELECT id,username,profile_pic FROM users WHERE id!=? ORDER BY id DESC", (uid,))
        rows=c.fetchall()
        out=[]
        for r in rows:
            if USE_POSTGRES:
                out.append({"id":r[0],"username":r[1],"profile_pic":r[2],"last_message":r[3] or "", "unread":int(r[4] or 0), "online":bool(r[5])})
            else:
                out.append({"id":r[0],"username":r[1],"profile_pic":r[2],"last_message":"","unread":0,"online":False})
        return jsonify(out)
    except Exception as e:
        print(e)
        c.execute("SELECT id,username,profile_pic FROM users WHERE id!=%s" if USE_POSTGRES else "SELECT id,username,profile_pic FROM users WHERE id!=?", (uid,))
        rows=c.fetchall()
        return jsonify([{"id":r[0],"username":r[1],"profile_pic":r[2],"last_message":"","unread":0,"online":False} for r in rows])
    finally:
        conn.close()

@app.route('/api/messages/<int:other_id>')
def get_messages(other_id):
    uid=session.get('user_id')
    if not uid: return jsonify([])
    conn=get_conn(); c=conn.cursor()
    try:
        if USE_POSTGRES:
            c.execute("INSERT INTO user_status (id,last_seen,online) VALUES (%s,NOW(),TRUE) ON CONFLICT (id) DO UPDATE SET last_seen=NOW(), online=TRUE", (uid,))
        else:
            c.execute("INSERT OR REPLACE INTO user_status (id,last_seen,online) VALUES (?,?,1)", (uid,datetime.now()))
        conn.commit()
    except: pass
    q="SELECT id,sender_id,receiver_id,content,created_at,reply_to FROM messages WHERE ((sender_id=%s AND receiver_id=%s) OR (sender_id=%s AND receiver_id=%s)) AND is_deleted=FALSE ORDER BY id ASC" if USE_POSTGRES else "SELECT id,sender_id,receiver_id,content,created_at,reply_to FROM messages WHERE ((sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?)) AND (is_deleted=0 OR is_deleted IS NULL) ORDER BY id ASC"
    c.execute(q,(uid,other_id,other_id,uid))
    rows=c.fetchall(); conn.close()
    return jsonify([{"id":r[0],"sender_id":r[1],"receiver_id":r[2],"content":r[3],"created_at":str(r[4]),"reply_to":r[5]} for r in rows])

@app.route('/api/messages', methods=['POST'])
@login_required
def send_message():
    uid=session.get('user_id')
    data=request.get_json() or {}
    rec=data.get('receiver_id'); content=data.get('content'); reply=data.get('reply_to')
    if not rec or not content: return jsonify({"error":"missing"}),400
    conn=get_conn(); c=conn.cursor()
    if USE_POSTGRES:
        c.execute("INSERT INTO messages (sender_id,receiver_id,content,reply_to) VALUES (%s,%s,%s,%s) RETURNING id,created_at", (uid,rec,content,reply))
        r=c.fetchone(); pid=r[0]; ts=str(r[1])
    else:
        c.execute("INSERT INTO messages (sender_id,receiver_id,content,reply_to,created_at) VALUES (?,?,?,?,?)", (uid,rec,content,reply,datetime.now()))
        pid=c.lastrowid; ts=str(datetime.now())
    conn.commit(); conn.close()
    return jsonify({"id":pid,"sender_id":uid,"receiver_id":rec,"content":content,"created_at":ts,"reply_to":reply})

@app.route('/api/message/delete/<int:msg_id>', methods=['POST'])
@login_required
def delete_msg(msg_id):
    uid=session.get('user_id')
    conn=get_conn(); c=conn.cursor()
    if USE_POSTGRES:
        c.execute("UPDATE messages SET is_deleted=TRUE WHERE id=%s AND sender_id=%s", (msg_id,uid))
    else:
        c.execute("UPDATE messages SET is_deleted=1 WHERE id=? AND sender_id=?", (msg_id,uid))
    conn.commit(); conn.close()
    return jsonify({"success":True})

@app.route('/api/update_profile', methods=['POST'])
@login_required
def update_profile():
    uid=session.get('user_id')
    bio=request.form.get('bio','')
    conn=get_conn(); c=conn.cursor()
    if 'profile_pic' in request.files and request.files['profile_pic'].filename:
        pic=upload_to_cloud(request.files['profile_pic'])
        if USE_POSTGRES:
            c.execute("UPDATE users SET bio=%s, profile_pic=%s WHERE id=%s", (bio,pic,uid))
        else:
            c.execute("UPDATE users SET bio=?, profile_pic=? WHERE id=?", (bio,pic,uid))
    else:
        if USE_POSTGRES:
            c.execute("UPDATE users SET bio=%s WHERE id=%s", (bio,uid))
        else:
            c.execute("UPDATE users SET bio=? WHERE id=?", (bio,uid))
    conn.commit(); conn.close()
    return jsonify({"success":True})

@app.route('/static/uploads/<path:filename>')
def serve_uploads(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__=='__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",5000)))
