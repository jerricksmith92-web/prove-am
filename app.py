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
