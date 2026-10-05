import os, uuid, sqlite3, time, traceback
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, session, redirect, url_for, render_template, render_template_string, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import cloudinary
import cloudinary.uploader

# CONFIGURE CLOUDINARY - THIS WAS MISSING
cloudinary.config(
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key = os.getenv("CLOUDINARY_API_KEY"),
    api_secret = os.getenv("CLOUDINARY_API_SECRET"),
    secure = True
)

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def upload_to_cloud(file_storage):
    try:
        if not file_storage:
            return None
        file_storage.stream.seek(0)
        # resource_type="auto" = works for image AND video
        result = cloudinary.uploader.upload(file_storage, resource_type="auto")
        url = result.get("secure_url")
        print(f"UPLOAD OK: {url}")
        return url
    except Exception as e:
        print(f"CLOUD FAIL, trying local: {e}")
        try:
            file_storage.stream.seek(0)
            original = os.path.basename(file_storage.filename or "")
            ext = os.path.splitext(original)[1].lower()
            allowed_exts = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".webm", ".mov", ".m4v", ".avi", ".mp3", ".wav", ".ogg", ".m4a", ".aac"}
            if ext not in allowed_exts:
                ext = ".bin"
            fname = uuid.uuid4().hex + ext
            path = os.path.join(UPLOAD_FOLDER, fname)
            file_storage.save(path)
            return "/static/uploads/" + fname
        except Exception as e2:
            print(f"LOCAL FAIL TOO: {e2}")
            import traceback; traceback.print_exc()
            return None

app = Flask(__name__)
CORS(app, supports_credentials=True)
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
    print("=== DATABASE REPAIR V38 ===")
    conn=get_conn();c=conn.cursor()
    try:
        if USE_POSTGRES:
            stmts=[
                "CREATE TABLE IF NOT EXISTS auth (username TEXT PRIMARY KEY, password TEXT, created_at TEXT)",
                "CREATE TABLE IF NOT EXISTS profiles (username TEXT PRIMARY KEY, pic_url TEXT, bio TEXT, last_seen TEXT)",
                "CREATE TABLE IF NOT EXISTS posts (id SERIAL PRIMARY KEY, username TEXT, text TEXT, media_url TEXT, created_at TEXT)",
                "CREATE TABLE IF NOT EXISTS post_likes (post_id INT, username TEXT, PRIMARY KEY(post_id,username))",
                "CREATE TABLE IF NOT EXISTS comments (id SERIAL PRIMARY KEY, post_id INT, username TEXT, text TEXT, created_at TEXT)",
                "CREATE TABLE IF NOT EXISTS messages (id SERIAL PRIMARY KEY, sender TEXT, receiver TEXT, text TEXT, media_url TEXT, created_at TEXT, read INT DEFAULT 0, reply_to TEXT)",
                "CREATE TABLE IF NOT EXISTS stories (id SERIAL PRIMARY KEY, username TEXT, media_url TEXT, text TEXT, created_at TEXT, expires_at TEXT)",
                "CREATE TABLE IF NOT EXISTS story_views (story_id INT, viewer TEXT, PRIMARY KEY(story_id,viewer))",
                "CREATE TABLE IF NOT EXISTS friends (id SERIAL PRIMARY KEY, sender TEXT, receiver TEXT, status TEXT, created_at TEXT)",
                "CREATE TABLE IF NOT EXISTS notifications (id SERIAL PRIMARY KEY, username TEXT, type TEXT, from_user TEXT, text TEXT, created_at TEXT, is_read INT DEFAULT 0)",
                "CREATE TABLE IF NOT EXISTS user_status (username TEXT PRIMARY KEY, last_seen REAL)",
                "CREATE TABLE IF NOT EXISTS message_reactions (message_id INT, username TEXT, reaction TEXT, PRIMARY KEY(message_id,username))",
                "CREATE TABLE IF NOT EXISTS blocked_users (blocker TEXT, blocked TEXT, PRIMARY KEY(blocker,blocked))",
                "CREATE TABLE IF NOT EXISTS follows (follower TEXT, following TEXT, PRIMARY KEY(follower,following))",
                "CREATE TABLE IF NOT EXISTS post_media (id SERIAL PRIMARY KEY, post_id INT, media_url TEXT, media_type TEXT)",
                "CREATE TABLE IF NOT EXISTS post_shares (id SERIAL PRIMARY KEY, post_id INT, username TEXT, created_at TEXT, UNIQUE(post_id,username))",
                "CREATE TABLE IF NOT EXISTS reports (id SERIAL PRIMARY KEY, reporter TEXT, target_type TEXT, target_id TEXT, reason TEXT, created_at TEXT)",
                "CREATE TABLE IF NOT EXISTS user_typing (username TEXT, peer TEXT, last_seen REAL, PRIMARY KEY(username,peer))",
                "CREATE TABLE IF NOT EXISTS user_settings (username TEXT PRIMARY KEY, private_account INT DEFAULT 0, message_privacy TEXT DEFAULT 'friends', show_last_seen INT DEFAULT 1, show_read_receipts INT DEFAULT 1)"]
        else:
            stmts=[
                "CREATE TABLE IF NOT EXISTS auth (username TEXT PRIMARY KEY, password TEXT, created_at TEXT)",
                "CREATE TABLE IF NOT EXISTS profiles (username TEXT PRIMARY KEY, pic_url TEXT, bio TEXT, last_seen TEXT)",
                "CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, text TEXT, media_url TEXT, created_at TEXT)",
                "CREATE TABLE IF NOT EXISTS post_likes (post_id INT, username TEXT, PRIMARY KEY(post_id,username))",
                "CREATE TABLE IF NOT EXISTS comments (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INT, username TEXT, text TEXT, created_at TEXT)",
                "CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, receiver TEXT, text TEXT, media_url TEXT, created_at TEXT, read INT DEFAULT 0, reply_to TEXT)",
                "CREATE TABLE IF NOT EXISTS stories (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, media_url TEXT, text TEXT, created_at TEXT, expires_at TEXT)",
                "CREATE TABLE IF NOT EXISTS story_views (story_id INT, viewer TEXT, PRIMARY KEY(story_id,viewer))",
                "CREATE TABLE IF NOT EXISTS friends (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, receiver TEXT, status TEXT, created_at TEXT)",
                "CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, type TEXT, from_user TEXT, text TEXT, created_at TEXT, is_read INTEGER DEFAULT 0)",
                "CREATE TABLE IF NOT EXISTS user_status (username TEXT PRIMARY KEY, last_seen REAL)",
                "CREATE TABLE IF NOT EXISTS message_reactions (message_id INT, username TEXT, reaction TEXT, PRIMARY KEY(message_id,username))",
                "CREATE TABLE IF NOT EXISTS blocked_users (blocker TEXT, blocked TEXT, PRIMARY KEY(blocker,blocked))",
                "CREATE TABLE IF NOT EXISTS follows (follower TEXT, following TEXT, PRIMARY KEY(follower,following))",
                "CREATE TABLE IF NOT EXISTS post_media (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INT, media_url TEXT, media_type TEXT)",
                "CREATE TABLE IF NOT EXISTS post_shares (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INT, username TEXT, created_at TEXT, UNIQUE(post_id,username))",
                "CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY AUTOINCREMENT, reporter TEXT, target_type TEXT, target_id TEXT, reason TEXT, created_at TEXT)",
                "CREATE TABLE IF NOT EXISTS user_typing (username TEXT, peer TEXT, last_seen REAL, PRIMARY KEY(username,peer))",
                "CREATE TABLE IF NOT EXISTS user_settings (username TEXT PRIMARY KEY, private_account INT DEFAULT 0, message_privacy TEXT DEFAULT 'friends', show_last_seen INT DEFAULT 1, show_read_receipts INT DEFAULT 1)"]
        for sql in stmts:
            c.execute(sql)
        conn.commit()
    finally:
        conn.close()
    cols=[
        ("profiles","cover_url","TEXT"),("profiles","private_account","INT DEFAULT 0"),("profiles","message_privacy","TEXT DEFAULT 'friends'"),("profiles","show_last_seen","INT DEFAULT 1"),("profiles","show_read_receipts","INT DEFAULT 1"),
        ("messages","edited_at","TEXT"),("messages","deleted_at","TEXT"),("posts","shared_post_id","INT"),("posts","edited_at","TEXT"),("auth","session_version","INT DEFAULT 1")]
    for tbl,col,typ in cols:
        run_alter(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS {col} {typ}" if USE_POSTGRES else f"ALTER TABLE {tbl} ADD COLUMN {col} {typ}")
    print("DATABASE REPAIR COMPLETE")

def init_db():
    try: nuclear_repair()
    except: pass
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
        c.execute("CREATE TABLE IF NOT EXISTS story_reactions (story_id INT, username TEXT, reaction TEXT, PRIMARY KEY(story_id,username))")
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
        c.execute("CREATE TABLE IF NOT EXISTS story_reactions (story_id INT, username TEXT, reaction TEXT, PRIMARY KEY(story_id,username))")
        c.execute("CREATE TABLE IF NOT EXISTS friends (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, receiver TEXT, status TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS friend (id INTEGER PRIMARY KEY AUTOINCREMENT, sender TEXT, receiver TEXT, status TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, type TEXT, from_user TEXT, text TEXT, created_at TEXT, is_read INTEGER DEFAULT 0)")
        c.execute("CREATE TABLE IF NOT EXISTS user_status (username TEXT PRIMARY KEY, last_seen REAL)")
        c.execute("CREATE TABLE IF NOT EXISTS story_reactions (story_id INT, username TEXT, reaction TEXT, PRIMARY KEY(story_id,username))")
    # Feature tables are also created here so older databases are upgraded safely.
    if USE_POSTGRES:
        c.execute("CREATE TABLE IF NOT EXISTS message_reactions (message_id INT, username TEXT, reaction TEXT, PRIMARY KEY(message_id,username))")
        c.execute("CREATE TABLE IF NOT EXISTS blocked_users (blocker TEXT, blocked TEXT, PRIMARY KEY(blocker,blocked))")
        c.execute("CREATE TABLE IF NOT EXISTS follows (follower TEXT, following TEXT, PRIMARY KEY(follower,following))")
        c.execute("CREATE TABLE IF NOT EXISTS post_media (id SERIAL PRIMARY KEY, post_id INT, media_url TEXT, media_type TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS post_shares (id SERIAL PRIMARY KEY, post_id INT, username TEXT, created_at TEXT, UNIQUE(post_id,username))")
        c.execute("CREATE TABLE IF NOT EXISTS reports (id SERIAL PRIMARY KEY, reporter TEXT, target_type TEXT, target_id TEXT, reason TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS user_typing (username TEXT, peer TEXT, last_seen REAL, PRIMARY KEY(username,peer))")
        c.execute("CREATE TABLE IF NOT EXISTS user_settings (username TEXT PRIMARY KEY, private_account INT DEFAULT 0, message_privacy TEXT DEFAULT 'friends', show_last_seen INT DEFAULT 1, show_read_receipts INT DEFAULT 1)")
    else:
        c.execute("CREATE TABLE IF NOT EXISTS message_reactions (message_id INT, username TEXT, reaction TEXT, PRIMARY KEY(message_id,username))")
        c.execute("CREATE TABLE IF NOT EXISTS blocked_users (blocker TEXT, blocked TEXT, PRIMARY KEY(blocker,blocked))")
        c.execute("CREATE TABLE IF NOT EXISTS follows (follower TEXT, following TEXT, PRIMARY KEY(follower,following))")
        c.execute("CREATE TABLE IF NOT EXISTS post_media (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INT, media_url TEXT, media_type TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS post_shares (id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INT, username TEXT, created_at TEXT, UNIQUE(post_id,username))")
        c.execute("CREATE TABLE IF NOT EXISTS reports (id INTEGER PRIMARY KEY AUTOINCREMENT, reporter TEXT, target_type TEXT, target_id TEXT, reason TEXT, created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS user_typing (username TEXT, peer TEXT, last_seen REAL, PRIMARY KEY(username,peer))")
        c.execute("CREATE TABLE IF NOT EXISTS user_settings (username TEXT PRIMARY KEY, private_account INT DEFAULT 0, message_privacy TEXT DEFAULT 'friends', show_last_seen INT DEFAULT 1, show_read_receipts INT DEFAULT 1)")
    # New profile/message/auth columns for upgraded installs.
    for tbl,col,typ in [("profiles","cover_url","TEXT"),("profiles","private_account","INT DEFAULT 0"),("profiles","message_privacy","TEXT DEFAULT 'friends'"),("profiles","show_last_seen","INT DEFAULT 1"),("profiles","show_read_receipts","INT DEFAULT 1"),("messages","edited_at","TEXT"),("messages","deleted_at","TEXT"),("posts","shared_post_id","INT") ,("posts","edited_at","TEXT"),("auth","session_version","INT DEFAULT 1")]:
        try:
            c.execute((f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS {col} {typ}") if USE_POSTGRES else (f"ALTER TABLE {tbl} ADD COLUMN {col} {typ}"))
        except Exception:
            pass
    # Ensure settings rows exist for current accounts.
    try:
        c.execute("SELECT username FROM auth")
        for (u,) in c.fetchall():
            if USE_POSTGRES:
                c.execute("INSERT INTO user_settings (username) VALUES (%s) ON CONFLICT (username) DO NOTHING",(u,))
            else:
                c.execute("INSERT OR IGNORE INTO user_settings (username) VALUES (?)",(u,))
    except Exception:
        pass
    conn.commit(); conn.close()
    print("DB READY V38 - SOCIAL FEATURES ENABLED")

init_db()


def notify(username, ntype, from_user='', text=''):
    if not username or username==from_user: return
    conn=get_conn(); c=conn.cursor()
    try:
        q="INSERT INTO notifications (username,type,from_user,text,created_at,is_read) VALUES (%s,%s,%s,%s,%s,0)" if USE_POSTGRES else "INSERT INTO notifications (username,type,from_user,text,created_at,is_read) VALUES (?,?,?,?,?,0)"
        c.execute(q,(username,ntype,from_user,text,datetime.now().isoformat()))
        conn.commit()
    except Exception:
        conn.rollback()
    finally: conn.close()

def is_friend(a,b):
    if not a or not b: return False
    conn=get_conn(); c=conn.cursor()
    q="SELECT 1 FROM friends WHERE ((sender=%s AND receiver=%s) OR (sender=%s AND receiver=%s)) AND status='accepted' LIMIT 1" if USE_POSTGRES else "SELECT 1 FROM friends WHERE ((sender=? AND receiver=?) OR (sender=? AND receiver=?)) AND status='accepted' LIMIT 1"
    c.execute(q,(a,b,b,a)); ok=bool(c.fetchone()); conn.close(); return ok

def is_blocked(a,b):
    conn=get_conn(); c=conn.cursor()
    q="SELECT 1 FROM blocked_users WHERE blocker=%s AND blocked=%s LIMIT 1" if USE_POSTGRES else "SELECT 1 FROM blocked_users WHERE blocker=? AND blocked=? LIMIT 1"
    c.execute(q,(a,b)); ok=bool(c.fetchone()); conn.close(); return ok

def get_mentions(text):
    import re
    return list(dict.fromkeys(re.findall(r'@([A-Za-z0-9_.-]{3,20})', text or '')))

LOGIN_HTML="""<!DOCTYPE html><html><head><meta name=viewport content="width=device-width,initial-scale=1"><style>body{background:#000;color:#fff;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0}.box{background:#111;padding:24px;border-radius:22px;width:330px;text-align:center;border:1px solid #222}input{width:100%;padding:13px;margin:8px 0;border-radius:12px;border:none;background:#222;color:#fff;font-size:16px}button{width:100%;padding:13px;background:#ffcc00;border:none;border-radius:12px;font-weight:bold}.msg-actions{font-size:11px;margin-top:5px;display:flex;gap:7px;flex-wrap:wrap}.msg-actions button{border:0;background:var(--sec);color:var(--text);border-radius:12px;padding:4px 7px}.reaction-row{font-size:12px;margin-top:4px}.typing{font-size:12px;color:#888;padding:0 12px}.profile-cover{width:100%;height:130px;object-fit:cover;border-radius:14px;background:#222}.feature-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}.small-btn{border:1px solid var(--border);background:var(--sec);color:var(--text);padding:8px 10px;border-radius:10px;font-weight:700}.danger-btn{background:#ff4444;color:#fff;border:none;padding:8px 10px;border-radius:10px;font-weight:700}.post-media-grid{display:grid;grid-template-columns:1fr 1fr;gap:3px}.post-media-grid img,.post-media-grid video{width:100%;max-height:280px;object-fit:cover}.profile-modal{position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:1000;display:none;align-items:flex-end}.profile-sheet{background:var(--card);color:var(--text);width:100%;max-height:85vh;overflow:auto;border-radius:22px 22px 0 0;padding:16px}</style></head><body><div class=box><h2 style=color:#ffcc00>PROVE AM</h2><input id=u placeholder=Username><input id=p type=password placeholder=Password><button onclick=login()>Login</button><button onclick=signup() style=background:#222;color:#fff;margin-top:8px>Sign Up</button><p id=msg style=color:#ff5555></p></div><script>async function login(){let r=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u.value,password:p.value})});let d=await r.json();if(d.ok)location.href='/';else msg.innerText=d.error}async function signup(){let r=await fetch('/signup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u.value,password:p.value})});let d=await r.json();if(d.ok)location.href='/';else msg.innerText=d.error}</script></body></html>"""

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
.notif-dot{position:absolute;top:-4px;right:-6px;background:#ff4444;color:#fff;font-size:10px;font-weight:900;padding:2px 6px;border-radius:12px;min-width:10px;text-align:center}
.low-on{background:#ffcc00!important;color:#000!important}
.friend-btn{padding:6px 12px;border-radius:20px;border:none;font-weight:700;font-size:12px;cursor:pointer}
.f-add{background:#ffcc00;color:#000}
.f-pending{background:#ddd;color:#666}
.f-friends{background:#00c851;color:#fff}
.onlineDot{width:10px;height:10px;background:#00c853;border-radius:50%;display:inline-block;border:2px solid #fff}
.offlineDot{width:10px;height:10px;background:#999;border-radius:50%;display:inline-block;border:2px solid #fff}
.badge{background:red;color:#fff;border-radius:10px;padding:2px 6px;font-size:11px;margin-left:6px;font-weight:900}
.replyBox{border-left:3px solid #ffcc00;background:#fff8e1;padding:6px;border-radius:8px;font-size:12px;margin-bottom:4px;color:#000}
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
<div style="display:flex;justify-content:space-between;padding:12px;background:var(--card)"><b>Friends ></b><small style="color:#888">Friends can view (once chatting)</small><b style="color:#a855f7;cursor:pointer" onclick="document.getElementById('storyFile').click()">+ Add</b><input type=file id=storyFile accept="image/*,video/*,audio/*,.pdf,.doc,.docx,.xls,.xlsx,.txt,.zip" multiple style=display:none></div>
<div class=story-bar id=storyBar></div>
<div class=story-card>
<b>Post a Story ✨</b><br><small>1 user = 1 circle - Friends can view once you chat/are friends</small>
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
<div id=searchResults style="margin-top:10px"></div><div id=globalSearchResults style="margin-top:10px"></div>
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
<button onclick="uploadProfilePic()" style="width:100%;margin-top:8px;background:#ffcc00;padding:12px;border-radius:12px;font-weight:900;border:none">Update Pic - stays after redeploy</button>
<hr><h4>Profile & Privacy</h4><textarea id="bioInput" rows="3" placeholder="Write a short bio..."></textarea><div class="feature-grid"><button class="small-btn" onclick="saveBio()">Save Bio</button><button class="small-btn" onclick="changeCover()">🖼️ Cover Photo</button></div><input type=file id=coverInput accept="image/*" style="display:none"><div id=coverPreview></div><div class="feature-grid" style="margin-top:8px"><button class="small-btn" onclick="togglePrivate()" id=privateBtn>Private account</button><button class="small-btn" onclick="toggleMessagePrivacy()" id=msgPrivacyBtn>Messages: Friends</button></div><div class="feature-grid" style="margin-top:8px"><button class="small-btn" onclick="toggleLastSeen()" id=lastSeenBtn>Last seen: ON</button><button class="small-btn" onclick="toggleReadReceipts()" id=readReceiptsBtn>Read receipts: ON</button></div><button class="danger-btn" style="width:100%;margin-top:8px" onclick="logoutAllDevices()">🔐 Log out all devices</button>
<br><br>
<button onclick="switchTab('stories')" style="background:var(--sec);padding:8px 12px;border-radius:12px;border:1px solid var(--border)">Back</button>
<button onclick="logout()" style=background:#ff4444;color:#fff;padding:8px 12px;border-radius:12px;border:none;margin-left:6px>Logout</button>
</div>
</div>
<div id="profileModal" class="profile-modal" onclick="if(event.target.id==='profileModal')closeProfileModal()"><div class="profile-sheet"><button class="small-btn" style="float:right" onclick="closeProfileModal()">Close</button><div id="publicProfile"></div></div></div>
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
<button onclick="reactStory('❤️')" style="background:#222;color:#fff;border:none;border-radius:20px;padding:10px 12px">❤️</button><button onclick="reactStory('😂')" style="background:#222;color:#fff;border:none;border-radius:20px;padding:10px 12px">😂</button><button onclick="replyStory()" style="background:#ffcc00;border:none;border-radius:20px;padding:10px 16px;font-weight:800">Send</button>
</div>
</div>
<script>
let curUser='',chatWith='',stories=[],groupedStories={},currentGroup=[],currentGroupIdx=0,storyTimer=null,allUsers=[],profiles={},selectedStoryFile=null,selectedPostFile=null,selectedChatFile=null,selectedProfileFile=null,replyToText='';
let lowData = localStorage.getItem('lowData')=='1';
let dark=localStorage.getItem('theme')=='dark'; if(dark)document.body.classList.add('dark');
updateLowBtn();
function updateLowBtn(){let b=document.getElementById('lowBtn'); if(!b)return; b.innerText=lowData?'📶 Low: ON':'📶 Low: OFF'; if(lowData) b.classList.add('low-on'); else b.classList.remove('low-on');}
function toggleLow(){lowData=!lowData;localStorage.setItem('lowData',lowData?'1':'0'); updateLowBtn(); alert(lowData?'Low Data ON':'Low Data OFF'); loadPosts();}
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
  if(t=='search'){searchUsers(); loadFriendRequests(); loadMyFriends();} if(t=='post') loadPosts();
}
function openNotifs(){document.getElementById('storiesDiv').style.display='none';document.getElementById('postDiv').style.display='none';document.getElementById('chatDiv').style.display='none';document.getElementById('searchDiv').style.display='none';document.getElementById('profileDiv').style.display='none';document.getElementById('notifDiv').style.display='block';loadNotifs();}
function openProfile(){document.getElementById('storiesDiv').style.display='none';document.getElementById('postDiv').style.display='none';document.getElementById('chatDiv').style.display='none';document.getElementById('searchDiv').style.display='none';document.getElementById('notifDiv').style.display='none';document.getElementById('profileDiv').style.display='block'; loadProfiles();}
async function loadMe(){let r=await fetch('/api/me');let d=await r.json();curUser=d.username;document.getElementById('profileName').innerText=curUser;loadProfiles();ping();setInterval(ping,15000);loadNotifCount();setInterval(loadNotifCount,5000);}
function ping(){fetch('/api/status/ping',{method:'POST'});}
async function loadProfiles(){
  let r=await fetch('/api/users');let users=await r.json();allUsers=users;users.forEach(u=>{profiles[u.username]=u.pic_url});
  renderTopPic();
  let me=await fetch('/api/profile/me'); let md=await me.json();
  let url=profiles[curUser]; let big=document.getElementById('profilePicBig');
  if(url && big){ let bust=url+'?t='+Date.now(); big.innerHTML=`<img src="${bust}" style="width:100%;height:100%;object-fit:cover">`; }
  if(document.getElementById('bioInput')) document.getElementById('bioInput').value=md.bio||'';
  updatePrivacyButtons(md);
}
function renderTopPic(){let url=profiles[curUser];let el=document.getElementById('topPic'); if(!el)return; if(url){let bust=url+'?t='+Date.now(); el.innerHTML=`<img src="${bust}" style="width:100%;height:100%;object-fit:cover">`;} else {el.innerText=curUser.charAt(0).toUpperCase();}}
document.getElementById('profilePicInput').addEventListener('change', function(e){let f=e.target.files[0]; if(!f)return; selectedProfileFile=f; document.getElementById('profileFileName').innerText='📎 '+f.name.slice(0,18); let big=document.getElementById('profilePicBig'); big.innerHTML=`<img src="${URL.createObjectURL(f)}" style="width:100%;height:100%;object-fit:cover">`; document.getElementById('profileMsg').innerText='Preview - tap Update';});
document.getElementById('storyFile').addEventListener('change', function(e){let f=e.target.files[0]; if(!f)return; selectedStoryFile=f; let preview=document.getElementById('storyPreview'); let img=document.getElementById('storyPreviewImg'); let vid=document.getElementById('storyPreviewVid'); preview.style.display='block'; document.getElementById('storySendBtn').style.display='block'; document.getElementById('storyCaption').style.display='block'; if(f.type.startsWith('video')){img.style.display='none';vid.style.display='block';vid.src=URL.createObjectURL(f);} else {vid.style.display='none';img.style.display='block';img.src=URL.createObjectURL(f);} });
document.getElementById('postFile').addEventListener('change', function(e){let f=e.target.files[0]; if(!f)return; selectedPostFile=f; document.getElementById('postFileName').innerText='📎 '+f.name.slice(0,16); let preview=document.getElementById('postPreview'); let img=document.getElementById('postPreviewImg'); let vid=document.getElementById('postPreviewVid'); preview.style.display='block'; if(f.type.startsWith('video')){img.style.display='none';vid.style.display='block';vid.src=URL.createObjectURL(f);} else {vid.style.display='none';img.style.display='block';img.src=URL.createObjectURL(f);} });
async function uploadStory(){
  if(!selectedStoryFile){alert('Pick photo');return}
  let cap=document.getElementById('storyCaption').value||''; document.getElementById('storyMsg').innerText='Uploading permanent...';
  let fd=new FormData(); fd.append('media',selectedStoryFile); fd.append('text',cap);
  let r=await fetch('/api/story',{method:'POST',body:fd}); let d=await r.json();
  document.getElementById('storyMsg').innerText=d.ok?'✅ Story Posted! Friends can view - stays after redeploy':'Failed: '+(d.error||'');
  if(d.ok){document.getElementById('storyPreview').style.display='none';document.getElementById('storySendBtn').style.display='none';document.getElementById('storyCaption').style.display='none';selectedStoryFile=null;loadStories();}
}
async function createTextStory(){let t=prompt('Text story (24h) friends only:');if(!t)return;let r=await fetch('/api/story/text',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t})});let d=await r.json();if(d.ok)loadStories();}
async function loadStories(){
  let r=await fetch('/api/stories'); stories=await r.json();
  groupedStories={}; stories.forEach(s=>{ if(!groupedStories[s.username]) groupedStories[s.username]=[]; groupedStories[s.username].push(s); });
  let h='';
  Object.keys(groupedStories).forEach(username=>{
    let userStories=groupedStories[username];
    let first=userStories[0];
    let profPic=profiles[username];
    let inner=profPic?`<div class=s-ring><img src="${profPic}"></div>`:`<div class=s-ring><img src="${first.media_url||''}"></div>`;
    let countBadge=userStories.length>1?`<div class=s-count>${userStories.length}</div>`:'';
    h+=`<div class=s-item onclick="openGrouped('${username}')"><div style="position:relative">${inner}${countBadge}</div><br><small><b>${username.slice(0,8)}</b></small></div>`;
  });
  document.getElementById('storyBar').innerHTML=h||'<small style=color:#888;padding:12px>No friends stories - add friends in Search, once friends you can view each other story</small>';
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
  if(s.username==curUser){fetch('/api/story/viewers?id='+s.id).then(r=>r.json()).then(v=>{document.getElementById('viewerCounter').innerText=(currentGroupIdx+1)+'/'+currentGroup.length+' · '+v.count+' views';}).catch(()=>{});}
  storyTimer=setTimeout(()=>{nextStory()},6000);
}
function nextStory(){ if(currentGroupIdx<currentGroup.length-1){currentGroupIdx++; showGrouped();} else {closeViewer(); loadStories();} }
function prevStory(){ if(currentGroupIdx>0){currentGroupIdx--; showGrouped();} }
function closeViewer(){clearTimeout(storyTimer);document.getElementById('viewerModal').style.display='none';let v=document.getElementById('viewerVideo');v.pause();}
async function deleteStory(){if(!confirm('Delete?'))return;let s=currentGroup[currentGroupIdx];await fetch('/api/story/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:s.id})}); closeViewer(); loadStories();}
async function reactStory(reaction){let s=currentGroup[currentGroupIdx];if(!s)return;let r=await fetch('/api/story/react',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:s.id,reaction})});let d=await r.json();if(d.ok)alert('Reaction sent');}
async function replyStory(){
  let input=document.getElementById('storyReplyInput'); let text=input.value.trim(); if(!text)return;
  let s=currentGroup[currentGroupIdx]; if(!s)return;
  let fd=new FormData(); fd.append('receiver',s.username); fd.append('text','↩️ Replied to your story: '+text);
  await fetch('/api/send',{method:'POST',body:fd});
  input.value=''; alert('Reply sent to '+s.username); closeViewer(); switchTab('chat'); openChat(s.username);
}
async function loadPosts(){
  let r=await fetch('/api/posts'); let posts=await r.json(); let h=''; if(!posts.length)h='<div class=card style="text-align:center;color:#888">No posts</div>';
  posts.forEach(p=>{
    let pic=profiles[p.username];let picHtml=pic?`<img src="${pic}">`:p.username[0]; let media=(p.media||[]).map(x=>{let u=x.url||'',low=u.toLowerCase();if((x.type||'').startsWith('video')||['.mp4','.mov','.webm','.m4v'].some(z=>low.includes(z)))return `<video src="${u}" controls style="width:100%;max-height:400px"></video>`;return `<img src="${u}" style="width:100%;max-height:400px;object-fit:cover">`;}).join(''); if(p.shared){media+=`<div class=card style="margin:8px;background:var(--sec)"><b>Shared from @${p.shared.username}</b><p>${escapeHtml(p.shared.text||'')}</p>${p.shared.media_url?`<img src="${p.shared.media_url}" style="width:100%;max-height:240px;object-fit:cover">`:''}</div>`;}
    let del=p.username==curUser?`<span class=del onclick="deletePost(${p.id})">🗑️</span>`:'';
    let text=linkify(p.text||''); let actions=`<span onclick="likePost(${p.id})" style="cursor:pointer">${p.liked?'❤️':'🤍'} ${p.like_count||0}</span><span onclick="commentPost(${p.id})" style="cursor:pointer">💬 ${p.comment_count||0}</span><span onclick="sharePost(${p.id})" style="cursor:pointer">🔄 ${p.share_count||0}</span><span onclick="viewComments(${p.id})" style="cursor:pointer">View</span><span onclick="reportTarget('post',${p.id})" style="cursor:pointer">🚩</span>`;
    h+=`<div class=card style="padding:0;overflow:hidden"><div style="padding:10px;display:flex;align-items:center;gap:8px"><div class=pic>${picHtml}</div><b onclick="viewProfile('${p.username}')" style="cursor:pointer">${p.username}</b><small style="margin-left:auto">${(p.created_at||'').slice(0,16)}</small>${del}</div>${p.text?`<div style="padding:0 12px 8px">${text}</div>`:''}${media}<div style="padding:10px;display:flex;gap:12px;flex-wrap:wrap">${actions}</div></div>`;
  });
  document.getElementById('postsList').innerHTML=h;
}
function linkify(t){return escapeHtml(t).replace(/#([A-Za-z0-9_]+)/g,'<span style="color:#9a6b00;font-weight:700">#$1</span>').replace(/@([A-Za-z0-9_.-]{3,20})/g,'<span style="color:#4169e1;font-weight:700">@$1</span>');}
async function sharePost(id){let r=await fetch('/api/post/share',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:id})});let d=await r.json();if(!d.ok)alert(d.error||'Could not share');loadPosts();}
async function viewComments(id){let r=await fetch('/api/comments?post_id='+id);let d=await r.json();let text=d.map(c=>c.username+': '+c.text).join('\\n')||'No comments';alert(text);}
async function createPost(){
  let txt=document.getElementById('postText').value; let files=[...((document.getElementById('postFile').files||[]))]; if(selectedPostFile&&!files.length)files=[selectedPostFile];
  if(!txt&&!files.length){document.getElementById('postMsg').innerText='Add text or tap 📎';return;}
  document.getElementById('postMsg').innerText='Posting...';
  let fd=new FormData();fd.append('text',txt);files.slice(0,6).forEach(f=>fd.append('media',f));
  let r=await fetch('/api/post',{method:'POST',body:fd});let d=await r.json();
  if(d.ok){document.getElementById('postMsg').innerText='✅ Posted!';document.getElementById('postText').value='';document.getElementById('postPreview').style.display='none';document.getElementById('postFile').value='';selectedPostFile=null;loadPosts();}else document.getElementById('postMsg').innerText='Failed: '+(d.error||'');
}
async function deletePost(id){if(!confirm('Delete post?'))return;await fetch('/api/post/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:id})});loadPosts();}
async function likePost(id){await fetch('/api/like',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:id})});loadPosts();}
async function commentPost(id){let t=prompt('Comment:');if(!t)return;await fetch('/api/comment',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({post_id:id,text:t})});loadPosts();}
function filterChat(){let q=document.getElementById('searchChat').value.toLowerCase();let filtered=allUsers.filter(u=>u.username.toLowerCase().includes(q));renderChatUsers(filtered);}
async function renderChatUsers(users){
  let h='';
  for(let u of users){
    if(u.username==curUser) continue;
    // online check
    let onlineHtml=''; let badge='';
    try{
      let sRes=await fetch('/api/status/get?user='+u.username); let st=await sRes.json();
      onlineHtml=st.online?'<span class=onlineDot></span> <small style="color:#00c853;font-weight:700">online</small>':'<span class=offlineDot></span> <small style="color:#888">offline</small>';
      let uRes=await fetch('/api/messages/unread_count?with='+u.username); let uc=await uRes.json();
      if(uc.count>0) badge=`<span class=badge>${uc.count} unread</span>`;
    }catch{}
    let pic=u.pic_url?`<img src="${u.pic_url}">`:u.username[0];
    h+=`<div class=card style="display:flex;align-items:center;gap:10px;cursor:pointer" onclick="openChat('${u.username}')"><div class=pic>${pic}</div><div><b onclick="event.stopPropagation();viewProfile('${u.username}')">${u.username}</b><br>${onlineHtml} ${badge}</div></div>`;
  }
  document.getElementById('chatUsers').innerHTML=h||'<div class=card style=color:#888">No friends yet - add in Search (needs approval)</div>';
}
async function loadChatUsers(){
  try{
    let r=await fetch('/api/friends/list'); let friends=await r.json();
    if(friends.length==0){ renderChatUsers(allUsers); return;}
    let friendNames = friends.map(f=>f.friend);
    let filtered = allUsers.filter(u=> friendNames.includes(u.username));
    renderChatUsers(filtered);
  }catch(e){ renderChatUsers(allUsers); }
}
async function openChat(username){
  chatWith=username;
  document.getElementById('chatUsers').style.display='none';document.getElementById('searchChat').style.display='none';
  let box=document.getElementById('chatBox');box.style.display='block';
  fetch('/api/messages/mark_read',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({with:username})});
  let statusRes=await fetch('/api/status/get?user='+username); let st=await statusRes.json();
  let online=st.online?'<span class=onlineDot></span> online':'<span class=offlineDot></span> offline';
  box.innerHTML=`<div style="padding:10px"><button onclick="backChat()" style="background:var(--sec);padding:8px;border-radius:8px;border:1px solid var(--border)">← ${username} ${online}</button><button onclick="searchConversation()" class=small-btn style="float:right">🔎 Search</button></div><div id=replyPreview style="display:none;background:#fff8e1;padding:8px;margin:8px;border-radius:10px;border-left:3px solid #ffcc00"></div><div id=typingStatus class=typing></div><div id=msgs style="padding:10px;padding-bottom:130px"></div><div class=chat-bar><input id=chatText class=pill placeholder="Write message..." /><input type=file id=chatFileHidden accept="image/*,video/*,audio/*,.pdf,.doc,.docx,.xls,.xlsx,.txt,.zip" multiple style="display:none"><button class=sticker onclick="startRecording()">🎤</button><div class=sticker onclick="document.getElementById('chatFileHidden').click()">📎</div><button class=yellow onclick=sendMsg()>Send</button></div>`;
  document.getElementById('chatFileHidden').addEventListener('change',function(e){let f=e.target.files[0]; if(f)selectedChatFile=f;});
  let ci=document.getElementById('chatText'); ci.addEventListener('input',()=>sendTyping());
  if(window.typingTimer)clearInterval(window.typingTimer); window.typingTimer=setInterval(pollTyping,1500);
  loadMsgs();
}
async function searchConversation(){if(!chatWith)return;let q=prompt('Search this conversation:');if(!q)return;let r=await fetch('/api/messages/search?with='+encodeURIComponent(chatWith)+'&q='+encodeURIComponent(q));let d=await r.json();alert(d.map(m=>(m.sender===curUser?'You':m.sender)+': '+m.text).join('\\n')||'No matching messages');}
function backChat(){chatWith='';document.getElementById('chatBox').style.display='none';document.getElementById('chatUsers').style.display='block';document.getElementById('searchChat').style.display='block';loadChatUsers();}

async function sendMsg(){
  if(!chatWith){ alert('Please select a user first.'); return; }

  const input=document.getElementById('chatText');
  const fileInput=document.getElementById('chatFileHidden');
  const text=input ? input.value.trim() : '';
  const file=(typeof selectedChatFile!=='undefined' && selectedChatFile) ? selectedChatFile : (fileInput && fileInput.files ? fileInput.files[0] : null);

  if(!text && !file) return;

  const fd=new FormData();
  fd.append('receiver',chatWith);
  fd.append('text',text);
  if(typeof replyToText!=='undefined' && replyToText) fd.append('reply_to',replyToText);
  if(file) fd.append('media',file);

  try{
    const r=await fetch('/api/send',{method:'POST',body:fd,credentials:'same-origin'});
    const raw=await r.text();
    let d={};
    try{d=raw?JSON.parse(raw):{};}catch(_){}
    if(!r.ok || !d.ok){
      console.error('Message failed:',r.status,raw);
      alert(d.error || ('Could not send message (HTTP '+r.status+').'));
      return;
    }
    if(input) input.value='';
    if(fileInput) fileInput.value='';
    if(typeof selectedChatFile!=='undefined') selectedChatFile=null;
    if(typeof cancelReply==='function') cancelReply();
    await loadMsgs();
  }catch(e){
    console.error(e);
    alert('Could not send message. Please check the server connection.');
  }
}
async function loadMsgs(){
  if(!chatWith)return;
  let r=await fetch('/api/messages?with='+encodeURIComponent(chatWith)); let msgs=await r.json(); let h='';
  msgs.forEach(m=>{
    let mu=m.media_url||''; let low=mu.toLowerCase(); let media='';
    if(mu){ if(low.includes('.mp4')||low.includes('.mov')||low.includes('.webm')) media=`<br><video src="${mu}" controls playsinline style="max-width:220px;border-radius:12px;margin-top:6px"></video>`; else if(low.includes('.mp3')||low.includes('.wav')||low.includes('.ogg')||low.includes('.m4a')||m.media_type==='audio') media=`<br><audio src="${mu}" controls style="max-width:220px;margin-top:6px"></audio>`; else if(low.includes('.mp3')||low.includes('.wav')||low.includes('.ogg')||low.includes('.m4a')||m.media_type==='audio') media=`<br><audio src="${mu}" controls style="max-width:220px;margin-top:6px"></audio>`; else media=`<br><a href="${mu}" target="_blank" rel="noopener" style="display:inline-block;margin-top:6px">📎 Open attachment</a>`; }
    let isMe=m.sender==curUser; let tick=isMe?(m.read?'<small style="color:#00c853">✓✓ read</small>':'<small style="color:#888">✓ sent</small>'):'';
    let reply=m.reply_to?`<div class=replyBox>${escapeHtml(m.reply_to)}</div>`:'';
    let reactions=(m.reactions||[]).map(x=>`${x.reaction} ${x.count}`).join(' · ');
    let text=m.deleted?'This message was deleted':(m.text||'');
    let edit=isMe&&!m.deleted?`<button onclick="editMsg(${m.id},${JSON.stringify(m.text||'')})">Edit</button>`:'';
    let del=isMe&&!m.deleted?`<button onclick="deleteMsg(${m.id})">Delete</button>`:'';
    h+=`<div style="margin:12px 0;text-align:${isMe?'right':'left'}"><span data-reply-text="${escapeHtml(text.slice(0,80))}" style="background:${isMe?'#000':'#eee'};color:${isMe?'#fff':'#000'};padding:12px 16px;border-radius:22px;display:inline-block;max-width:76%;word-break:break-word;cursor:pointer">${reply}${escapeHtml(text)}${media}<br>${tick}<div class=reaction-row>${escapeHtml(reactions)}</div><div class=msg-actions><button onclick="setReply(${JSON.stringify(text.slice(0,80))})">↩ Reply</button><button onclick="reactMsg(${m.id},'❤️')">❤️</button><button onclick="reactMsg(${m.id},'😂')">😂</button><button onclick="reactMsg(${m.id},'👍')">👍</button>${edit}${del}</div></span></div>`;
  });
  let el=document.getElementById('msgs'); if(el)el.innerHTML=h||'<div style="text-align:center;color:#888;padding:30px">Start the conversation</div>'; let mbox=document.getElementById('msgs');if(mbox)mbox.scrollTop=mbox.scrollHeight;
}
function escapeHtml(s){return String(s||'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));}
async function reactMsg(id,reaction){let r=await fetch('/api/message/react',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,reaction})});let d=await r.json();if(d.ok)loadMsgs();}
async function editMsg(id,current){let t=prompt('Edit message:',current||'');if(t===null)return;let r=await fetch('/api/message/edit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,text:t})});let d=await r.json();if(!d.ok)alert(d.error||'Could not edit');loadMsgs();}
async function deleteMsg(id){if(!confirm('Delete this message?'))return;let r=await fetch('/api/message/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});let d=await r.json();if(!d.ok)alert(d.error||'Could not delete');loadMsgs();}
async function sendTyping(){if(!chatWith)return;fetch('/api/typing',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({peer:chatWith})});}
async function pollTyping(){if(!chatWith)return;try{let d=await (await fetch('/api/typing?peer='+encodeURIComponent(chatWith))).json();let el=document.getElementById('typingStatus');if(el)el.innerText=d.typing?chatWith+' is typing…':'';}catch(e){}}
let mediaRecorder=null,recordChunks=[];
async function startRecording(){if(mediaRecorder&&mediaRecorder.state==='recording'){mediaRecorder.stop();return;}if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){alert('Voice recording is not supported by this browser');return;}try{let stream=await navigator.mediaDevices.getUserMedia({audio:true});mediaRecorder=new MediaRecorder(stream);recordChunks=[];mediaRecorder.ondataavailable=e=>{if(e.data.size)recordChunks.push(e.data)};mediaRecorder.onstop=async()=>{stream.getTracks().forEach(t=>t.stop());let blob=new Blob(recordChunks,{type:mediaRecorder.mimeType||'audio/webm'});let file=new File([blob],'voice-'+Date.now()+'.webm',{type:blob.type});let fd=new FormData();fd.append('receiver',chatWith);fd.append('text','');fd.append('media',file);fd.append('media_type','audio');let r=await fetch('/api/send',{method:'POST',body:fd});let d=await r.json();if(!d.ok)alert(d.error||'Could not send voice message');else loadMsgs();};mediaRecorder.start();alert('Recording... tap 🎤 again to stop');}catch(e){alert('Microphone permission was denied or unavailable');}}
let swipeX=0;document.addEventListener('touchstart',e=>{if(e.target.closest('#msgs'))swipeX=e.touches[0].clientX},{passive:true});document.addEventListener('touchend',e=>{let el=e.target.closest('#msgs [data-reply-text]');if(el&&swipeX-e.changedTouches[0].clientX>70)setReply(el.dataset.replyText||'');swipeX=0},{passive:true});
function setReply(t){replyToText=t;let p=document.getElementById('replyPreview');p.style.display='block';p.innerHTML=`Replying to: ${t} <span onclick="cancelReply()" style="float:right;cursor:pointer;color:red">✕</span>`;}
function cancelReply(){replyToText='';document.getElementById('replyPreview').style.display='none';}
async function searchUsers(){
  let inp=document.getElementById('searchUsersInput');
  let q=inp ? inp.value : '';
  let box=document.getElementById('searchResults');
  if(!box) return;
  if(!q.trim()){ box.innerHTML=''; return; }
  box.innerHTML='Searching...';
  try{
    let r=await fetch('/api/search?q='+encodeURIComponent(q));
    let users=await r.json();
    let h='';
    users.forEach(function(u){
      
      if(typeof curUser!=='undefined' && u.username==curUser) return;
      let s=u.friend_status||'none';
      let btn='';
      if(s=='none') btn='<button data-u="'+u.username+'" onclick="sendFriendReq(this.dataset.u)">Add</button>';
      else if(s=='pending_sent') btn='<span>Requested</span>';
      else if(s=='pending_received') btn='<button data-u="'+u.username+'" onclick="acceptFriend(this.dataset.u)">Accept</button>';
      else btn='<span>Friends</span>';
      h+='<div style="padding:8px;border-bottom:1px solid #eee;display:flex;align-items:center;gap:8px"><span style="cursor:pointer" data-user="'+u.username+'" onclick="viewProfile(this.dataset.user)">'+u.username+'</span><span style="margin-left:auto">'+btn+'</span></div>';
    });
    box.innerHTML=h||'No users found'; globalSearch(q);
  }catch(e){ box.innerHTML='Error: '+e; }
}
async function globalSearch(q){let box=document.getElementById('globalSearchResults');if(!box)return;let r=await fetch('/api/global-search?q='+encodeURIComponent(q));let d=await r.json();let h='<h4>Posts</h4>';d.posts.forEach(p=>{h+=`<div class=card><b>${p.username}</b><br>${p.text||''}<br><small>${p.created_at||''}</small></div>`});box.innerHTML=h+(d.posts.length?'':'<small style="color:#888">No matching posts</small>');}

async function sendFriendReq(u){
  try{
    const r=await fetch('/api/friend/request',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      credentials:'same-origin',
      body:JSON.stringify({to:u})
    });
    const raw=await r.text();
    let d={};
    try{ d=raw?JSON.parse(raw):{}; }catch(_){}
    if(!r.ok || !d.ok){
      console.error('Friend request failed:',r.status,raw);
      alert(d.error || ('Could not send friend request (HTTP '+r.status+').'));
      return;
    }
    await searchUsers();
    await loadFriendRequests();
  }catch(e){
    console.error(e);
    alert('Could not send friend request. Please check the server connection.');
  }
}
async function acceptFriend(u){ await fetch('/api/friend/accept',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({from:u})}); searchUsers(); loadFriendRequests(); loadMyFriends(); loadNotifs(); }
async function loadFriendRequests(){
  let r=await fetch('/api/friend/requests'); let reqs=await r.json();
  document.getElementById('reqCount').innerText=reqs.length;
  let h='';
  reqs.forEach(req=>{
    let pic=profiles[req.sender]?`<img src="${profiles[req.sender]}">`:req.sender[0];
    h+=`<div class=card style="display:flex;align-items:center;gap:10px"><div class=pic>${pic}</div><b>${req.sender}</b><div style="margin-left:auto;display:flex;gap:6px"><button class=friend-btn f-add onclick="acceptFriend('${req.sender}')">Accept - approval</button><button class=friend-btn f-pending onclick="declineFriend('${req.sender}')">Decline</button></div></div>`;
  });
  document.getElementById('friendRequests').innerHTML=h||'<small style=color:#888>No pending requests</small>';
}
async function removeFriend(username){if(!confirm('Remove '+username+' from friends?'))return;await fetch('/api/friend/remove',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username})});loadMyFriends();loadChatUsers();}
async function declineFriend(username){await fetch('/api/friend/decline',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({from:username})}); loadFriendRequests();}
async function loadMyFriends(){
  let r=await fetch('/api/friends/list'); let friends=await r.json();
  let h='';
  friends.forEach(f=>{
    let pic=profiles[f.friend]?`<img src="${profiles[f.friend]}">`:f.friend[0];
    h+=`<div class=card style="display:flex;align-items:center;gap:10px"><div class=pic>${pic}</div><b>${f.friend}</b><span style="margin-left:auto;color:#00c851;font-size:12px">✓ Friends</span><button class=small-btn onclick="removeFriend('${f.friend}')">Remove</button><button class=small-btn onclick="viewProfile('${f.friend}')">Profile</button></div>`;
  });
  document.getElementById('myFriendsList').innerHTML=h||'<small style=color:#888>No friends yet</small>';
}
async function loadNotifs(){
  let r=await fetch('/api/notifications'); let notifs=await r.json();
  let h='';
  notifs.forEach(n=>{
    h+=`<div class=card><small style=color:#888">${(n.created_at||'').slice(0,16)} - ${n.type}</small><br><b>${n.from_user}</b>: ${n.text}<br>${n.type=='friend_request'?`<button class=friend-btn f-add onclick="acceptFriend('${n.from_user}'); switchTab('search');">Accept Friend</button>`:''}</div>`;
  });
  document.getElementById('notifList').innerHTML=h||'<small style=color:#888>No notifications</small>'; fetch('/api/notifications/read',{method:'POST'});
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
  document.getElementById('profileMsg').innerText='Uploading permanent...';
  let fd=new FormData();fd.append('media',f);
  let r=await fetch('/api/profile/pic',{method:'POST',body:fd}); let d=await r.json();
  if(d.ok){
    document.getElementById('profileMsg').innerText='✅ Updated! stays after redeploy';
    profiles[curUser]=d.url; renderTopPic();
    let big=document.getElementById('profilePicBig'); big.innerHTML=`<img src="${d.url}?t=${Date.now()}" style="width:100%;height:100%;object-fit:cover">`;
    selectedProfileFile=null;
  } else {document.getElementById('profileMsg').innerText='Failed: '+(d.error||' add Cloudinary keys in Render');}
}

async function saveBio(){let bio=document.getElementById('bioInput').value.slice(0,500);let r=await fetch('/api/profile/update',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({bio})});let d=await r.json();alert(d.ok?'Bio updated':'Could not update bio');}
function changeCover(){document.getElementById('coverInput').click();}
document.addEventListener('change',async function(e){if(e.target.id!=='coverInput')return;let f=e.target.files[0];if(!f)return;let fd=new FormData();fd.append('media',f);let r=await fetch('/api/profile/cover',{method:'POST',body:fd});let d=await r.json();if(d.ok){document.getElementById('coverPreview').innerHTML=`<img class=profile-cover src="${d.url}?t=${Date.now()}">`;alert('Cover photo updated');}else alert(d.error||'Could not update cover');});
function updatePrivacyButtons(md){if(document.getElementById('privateBtn'))document.getElementById('privateBtn').innerText=md.private_account?'🔒 Private: ON':'🔓 Private: OFF';if(document.getElementById('msgPrivacyBtn'))document.getElementById('msgPrivacyBtn').innerText='Messages: '+(md.message_privacy==='everyone'?'Everyone':'Friends');if(document.getElementById('lastSeenBtn'))document.getElementById('lastSeenBtn').innerText='Last seen: '+(md.show_last_seen?'ON':'OFF');if(document.getElementById('readReceiptsBtn'))document.getElementById('readReceiptsBtn').innerText='Read receipts: '+(md.show_read_receipts?'ON':'OFF');}
async function privacyPatch(data){let r=await fetch('/api/profile/settings',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});let d=await r.json();if(d.ok)updatePrivacyButtons(d);}
async function togglePrivate(){let md=await (await fetch('/api/profile/me')).json();privacyPatch({private_account:md.private_account?0:1});}
async function toggleMessagePrivacy(){let md=await (await fetch('/api/profile/me')).json();privacyPatch({message_privacy:md.message_privacy==='everyone'?'friends':'everyone'});}
async function toggleLastSeen(){let md=await (await fetch('/api/profile/me')).json();privacyPatch({show_last_seen:md.show_last_seen?0:1});}
async function toggleReadReceipts(){let md=await (await fetch('/api/profile/me')).json();privacyPatch({show_read_receipts:md.show_read_receipts?0:1});}
async function logoutAllDevices(){if(!confirm('Log out this account from all devices?'))return;let r=await fetch('/api/security/logout_all',{method:'POST'});let d=await r.json();if(d.ok)location.href='/login';}
async function viewProfile(username){let r=await fetch('/api/profile/'+encodeURIComponent(username));let d=await r.json();let h=`<div style="text-align:center"><div class=pic style="width:90px;height:90px;font-size:32px;margin:0 auto 8px">${d.pic_url?`<img src="${d.pic_url}">`:username[0]}</div><h2>${username}</h2>${d.cover_url?`<img class=profile-cover src="${d.cover_url}">`:''}<p>${d.bio||'No bio yet.'}</p><p><b>${d.friends_count}</b> friends · <b>${d.followers}</b> followers · <b>${d.following}</b> following</p><div class=feature-grid><button class=small-btn onclick="followUser('${username}')">${d.following_me?'Following':'Follow'}</button><button class=small-btn onclick="blockUser('${username}')">${d.blocked?'Unblock':'Block'}</button></div><button class=danger-btn style="width:100%;margin-top:8px" onclick="reportTarget('user','${username}')">Report user</button></div>`;document.getElementById('publicProfile').innerHTML=h;document.getElementById('profileModal').style.display='flex';}
function closeProfileModal(){document.getElementById('profileModal').style.display='none';}
async function followUser(u){let r=await fetch('/api/follow',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u})});let d=await r.json();if(!d.ok)alert(d.error||'Follow failed');else viewProfile(u);}
async function blockUser(u){let r=await fetch('/api/block',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u})});let d=await r.json();if(!d.ok)alert(d.error||'Block failed');else {alert(d.blocked?'User blocked':'User unblocked');viewProfile(u);}}
async function reportTarget(type,id){let reason=prompt('Reason for report?');if(!reason)return;let r=await fetch('/api/report',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({target_type:type,target_id:String(id),reason})});let d=await r.json();alert(d.ok?'Report submitted':'Could not submit report');}

async function logout(){await fetch('/logout');location.href='/login'}
loadMe();switchTab('stories');
</script></body></html>"""


@app.before_request
def enforce_session_version():
    if request.endpoint in ('login_page','login_api','signup','static') or request.path.startswith('/static/'):
        return
    me=session.get('username')
    if not me:return
    try:
        conn=get_conn();c=conn.cursor();q="SELECT session_version FROM auth WHERE username=%s" if USE_POSTGRES else "SELECT session_version FROM auth WHERE username=?";c.execute(q,(me,));r=c.fetchone();conn.close();
        if r and int(r[0] or 1)!=int(session.get('session_version',1)):
            session.clear();return jsonify({"ok":False,"error":"Session expired. Please log in again."}),401
    except Exception:pass

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
    session['username']=u; session['session_version']=1; return jsonify({"ok":True})

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
    conn.commit(); conn.close(); session['username']=u; session['session_version']=1; return jsonify({"ok":True})

@app.route('/api/me')
def api_me(): return jsonify({"username":session.get('username','')})

@app.route('/api/users')
def api_users():
    conn=get_conn(); c=conn.cursor()
    try:
        c.execute("SELECT username,pic_url FROM profiles")
        rows=c.fetchall()
    except:
        rows=[]
    conn.close()
    return jsonify([{"username":r[0],"pic_url":(r[1] or "")} for r in rows])
      
@app.route('/api/friend/request', methods=['POST'])
def api_friend_request():
    me = (session.get('username') or '').strip()
    data = request.get_json(silent=True) or {}
    to = (data.get('to') or '').strip()

    if not me:
        return jsonify({"ok":False,"error":"Not logged in"}),401
    if not to:
        return jsonify({"ok":False,"error":"Missing username"}),400
    if to == me:
        return jsonify({"ok":False,"error":"You cannot add yourself"}),400
    if is_blocked(me,to) or is_blocked(to,me):
        return jsonify({"ok":False,"error":"Friend request unavailable"}),403

    conn = get_conn()
    c = conn.cursor()
    try:
        # Check the actual account in auth. Profiles from older accounts may
        # be missing even though the login account exists.
        q_user = "SELECT username FROM auth WHERE username=%s" if USE_POSTGRES else "SELECT username FROM auth WHERE username=?"
        c.execute(q_user, (to,))
        if not c.fetchone():
            return jsonify({"ok":False,"error":"User not found"}),404

        q = (
            "SELECT sender,receiver,status FROM friends WHERE (sender=%s AND receiver=%s) OR (sender=%s AND receiver=%s)"
            if USE_POSTGRES else
            "SELECT sender,receiver,status FROM friends WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?)"
        )
        c.execute(q, (me,to,to,me))
        existing = c.fetchone()

        if existing:
            sender, receiver, status = existing
            if status == "accepted":
                return jsonify({"ok":False,"error":"You are already friends"}),409
            if sender == me and receiver == to:
                return jsonify({"ok":False,"error":"Friend request already sent"}),409
            return jsonify({"ok":False,"error":"This user has already sent you a friend request"}),409

        q2 = (
            "INSERT INTO friends (sender,receiver,status,created_at) VALUES (%s,%s,%s,%s)"
            if USE_POSTGRES else
            "INSERT INTO friends (sender,receiver,status,created_at) VALUES (?,?,?,?)"
        )
        c.execute(q2, (me,to,'pending',datetime.now().isoformat()))

        # Notification is created in the same transaction, but a notification
        # failure must not make the friend request disappear.
        try:
            q3 = (
                "INSERT INTO notifications (username,type,from_user,text,created_at,is_read) VALUES (%s,%s,%s,%s,%s,0)"
                if USE_POSTGRES else
                "INSERT INTO notifications (username,type,from_user,text,created_at,is_read) VALUES (?,?,?,?,?,0)"
            )
            c.execute(q3, (to,'friend_request',me,me+" sent you a friend request",datetime.now().isoformat()))
        except Exception:
            pass

        conn.commit()
        return jsonify({"ok":True})
    except Exception:
        conn.rollback()
        print("FRIEND REQUEST ERROR:")
        traceback.print_exc()
        return jsonify({"ok":False,"error":"Server could not save the friend request"}),500
    finally:
        conn.close()

@app.route('/api/friend/accept', methods=['POST'])
def api_friend_accept():
    me=session.get('username'); frm=(request.json.get('from') if request.json else None)
    conn=get_conn(); c=conn.cursor()
    q = "UPDATE friends SET status='accepted' WHERE sender=%s AND receiver=%s" if USE_POSTGRES else "UPDATE friends SET status='accepted' WHERE sender=? AND receiver=?"
    c.execute(q, (frm,me)); conn.commit(); conn.close(); notify(frm,'friend_accept',me,me+' accepted your friend request'); return jsonify({"ok":True})

@app.route('/api/friend/decline', methods=['POST'])
def api_friend_decline():
    me=session.get('username'); frm=(request.json.get('from') if request.json else None)
    conn=get_conn(); c=conn.cursor()
    q = "DELETE FROM friends WHERE sender=%s AND receiver=%s" if USE_POSTGRES else "DELETE FROM friends WHERE sender=? AND receiver=?"
    c.execute(q, (frm,me))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/api/friend/requests')
def api_friend_requests():
    me=session.get('username')
    conn=get_conn(); c=conn.cursor()
    q = "SELECT sender FROM friends WHERE receiver=%s AND status='pending'" if USE_POSTGRES else "SELECT sender FROM friends WHERE receiver=? AND status='pending'"
    c.execute(q, (me,))
    rows=c.fetchall(); conn.close()
    return jsonify([{"sender":r[0],"username":r[0]} for r in rows])

@app.route('/api/friends/list')
def api_friends_list():
    me=session.get('username')
    conn=get_conn(); c=conn.cursor()
    q = "SELECT sender,receiver FROM friends WHERE (sender=%s OR receiver=%s) AND status='accepted'" if USE_POSTGRES else "SELECT sender,receiver FROM friends WHERE (sender=? OR receiver=?) AND status='accepted'"
    c.execute(q, (me,me))
    rows=c.fetchall(); conn.close()
    friends=[]
    for s,r in rows:
        other=r if s==me else s
        if other:
            friends.append(other)
    return jsonify([{"username":u,"friend":u} for u in friends if u])

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
    c.execute("SELECT last_seen FROM user_status WHERE username=%s" if USE_POSTGRES else "SELECT last_seen FROM user_status WHERE username=?",(u,)); row=c.fetchone();
    try:
        qp="SELECT show_last_seen FROM profiles WHERE username=%s" if USE_POSTGRES else "SELECT show_last_seen FROM profiles WHERE username=?";c.execute(qp,(u,));sp=c.fetchone();
    except: sp=None
    conn.close()
    if sp and sp[0]==0 and u!=session.get('username'): return jsonify({"online":False,"hidden":True})
    if not row:return jsonify({"online":False})
    return jsonify({"online":(time.time()-float(row[0]))<40})

@app.route('/api/posts')
def api_posts():
    me=session.get('username'); conn=get_conn(); c=conn.cursor()
    c.execute("SELECT id,username,text,media_url,created_at,shared_post_id FROM posts ORDER BY id DESC LIMIT 50")
    rows=c.fetchall(); out=[]
    allowed_private={me}
    try:
        qf="SELECT sender,receiver FROM friends WHERE (sender=%s OR receiver=%s) AND status='accepted'" if USE_POSTGRES else "SELECT sender,receiver FROM friends WHERE (sender=? OR receiver=?) AND status='accepted'";c.execute(qf,(me,me));
        for aa,bb in c.fetchall():allowed_private.add(bb if aa==me else aa)
    except:pass
    for r in rows:
        try:
            qp="SELECT private_account FROM profiles WHERE username=%s" if USE_POSTGRES else "SELECT private_account FROM profiles WHERE username=?";c.execute(qp,(r[1],));pv=c.fetchone();
            if pv and pv[0] and r[1] not in allowed_private: continue
        except:pass
        pid=r[0]; lc=0; liked=False
        try:
            c.execute("SELECT COUNT(*) FROM post_likes WHERE post_id=%s" if USE_POSTGRES else "SELECT COUNT(*) FROM post_likes WHERE post_id=?",(pid,));lc=c.fetchone()[0]
            c.execute("SELECT 1 FROM post_likes WHERE post_id=%s AND username=%s" if USE_POSTGRES else "SELECT 1 FROM post_likes WHERE post_id=? AND username=?",(pid,me));liked=bool(c.fetchone())
        except: pass
        try:c.execute("SELECT COUNT(*) FROM comments WHERE post_id=%s" if USE_POSTGRES else "SELECT COUNT(*) FROM comments WHERE post_id=?",(pid,));cc=c.fetchone()[0]
        except:cc=0
        try:c.execute("SELECT COUNT(*) FROM post_shares WHERE post_id=%s" if USE_POSTGRES else "SELECT COUNT(*) FROM post_shares WHERE post_id=?",(pid,));sc=c.fetchone()[0]
        except:sc=0
        media=[]
        try:
            c.execute("SELECT media_url,media_type FROM post_media WHERE post_id=%s ORDER BY id" if USE_POSTGRES else "SELECT media_url,media_type FROM post_media WHERE post_id=? ORDER BY id",(pid,));media=[{"url":x[0],"type":x[1] or ''} for x in c.fetchall()]
        except:pass
        if not media and r[3]:media=[{"url":r[3],"type":""}]
        shared=None
        if r[5]:
            try:
                q="SELECT username,text,media_url,created_at FROM posts WHERE id=%s" if USE_POSTGRES else "SELECT username,text,media_url,created_at FROM posts WHERE id=?";c.execute(q,(r[5],));x=c.fetchone()
                if x:shared={"username":x[0],"text":x[1],"media_url":x[2],"created_at":str(x[3])}
            except:pass
        out.append({"id":pid,"username":r[1],"text":r[2],"media_url":r[3],"created_at":str(r[4]),"like_count":lc,"liked":liked,"comment_count":cc,"share_count":sc,"shared_post_id":r[5],"media":media,"shared":shared})
    conn.close();return jsonify(out)

@app.route('/api/post', methods=['POST'])
def api_post():
    me=session.get('username'); txt=request.form.get('text','')[:500]; files=request.files.getlist('media')
    if not txt and not files:return jsonify({"ok":False,"error":"empty"}),400
    conn=get_conn();c=conn.cursor();now=datetime.now().isoformat();urls=[]
    try:
        for f in files[:6]:
            if f and f.filename:
                url=upload_to_cloud(f)
                if url:urls.append((url,f.mimetype or ''))
        first=urls[0][0] if urls else ''
        q="INSERT INTO posts (username,text,media_url,created_at) VALUES (%s,%s,%s,%s) RETURNING id" if USE_POSTGRES else "INSERT INTO posts (username,text,media_url,created_at) VALUES (?,?,?,?)"
        if USE_POSTGRES:
            c.execute(q,(me,txt,first,now));pid=c.fetchone()[0]
        else:
            c.execute(q,(me,txt,first,now));pid=c.lastrowid
        for url,mtype in urls:
            q2="INSERT INTO post_media (post_id,media_url,media_type) VALUES (%s,%s,%s)" if USE_POSTGRES else "INSERT INTO post_media (post_id,media_url,media_type) VALUES (?,?,?)";c.execute(q2,(pid,url,mtype))
        for mention in get_mentions(txt):
            try:
                qu="SELECT username FROM auth WHERE username=%s" if USE_POSTGRES else "SELECT username FROM auth WHERE username=?";c.execute(qu,(mention,));
                if c.fetchone() and mention!=me:
                    qn="INSERT INTO notifications (username,type,from_user,text,created_at,is_read) VALUES (%s,%s,%s,%s,%s,0)" if USE_POSTGRES else "INSERT INTO notifications (username,type,from_user,text,created_at,is_read) VALUES (?,?,?,?,?,0)";c.execute(qn,(mention,'mention',me,me+' mentioned you in a post',now))
            except:pass
        conn.commit();return jsonify({"ok":True,"id":pid})
    except Exception:
        conn.rollback();traceback.print_exc();return jsonify({"ok":False,"error":"Could not create post"}),500
    finally:conn.close()

@app.route('/api/post/delete', methods=['POST'])
def api_post_delete():
    me=session.get('username'); data=request.json; pid=data.get('id')
    conn=get_conn(); c=conn.cursor()
    c.execute("DELETE FROM posts WHERE id=%s AND username=%s" if USE_POSTGRES else "DELETE FROM posts WHERE id=? AND username=?", (pid,me)); conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/api/like', methods=['POST'])
def api_like():
    me=session.get('username'); data=request.json; pid=data.get('post_id'); conn=get_conn(); c=conn.cursor()
    try:
        c.execute("SELECT 1 FROM post_likes WHERE post_id=%s AND username=%s" if USE_POSTGRES else "SELECT 1 FROM post_likes WHERE post_id=? AND username=?", (pid,me))
        if c.fetchone(): c.execute("DELETE FROM post_likes WHERE post_id=%s AND username=%s" if USE_POSTGRES else "DELETE FROM post_likes WHERE post_id=? AND username=?", (pid,me))
        else: c.execute("INSERT INTO post_likes VALUES (%s,%s)" if USE_POSTGRES else "INSERT INTO post_likes VALUES (?,?)", (pid,me))
        conn.commit()
        try:
            qown="SELECT username FROM posts WHERE id=%s" if USE_POSTGRES else "SELECT username FROM posts WHERE id=?";c.execute(qown,(pid,));own=c.fetchone()
            if own and own[0]!=me: notify(own[0],'like',me,me+' liked your post')
        except: pass
    except: pass
    conn.close(); return jsonify({"ok":True})

@app.route('/api/search')
def api_search():
    me = session.get('username')
    if not me:
        return jsonify({"error": "Not logged in"}), 401
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
    conn = get_conn()
    c = conn.cursor()
    like = f"%{q.lower()}%"
    try:
        c.execute("SELECT username,pic_url FROM profiles WHERE LOWER(username) LIKE %s AND username!=%s LIMIT 30" if USE_POSTGRES else "SELECT username,pic_url FROM profiles WHERE LOWER(username) LIKE? AND username!=? LIMIT 30", (like, me))
        rows = c.fetchall()
    except Exception as e:
        rows=[]
    result=[]
    for r in rows:
        uname=r[0]; pic=r[1] or ""
        status="none"
        try:
            c2q="SELECT sender,receiver,status FROM friends WHERE (sender=%s AND receiver=%s) OR (sender=%s AND receiver=%s)" if USE_POSTGRES else "SELECT sender,receiver,status FROM friends WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?)"
            c.execute(c2q,(me,uname,uname,me))
            fr=c.fetchone()
            if fr:
                s,r2,st=fr
                if st=="accepted": status="friends"
                elif s==me: status="pending_sent"
                else: status="pending_received"
        except: pass
        result.append({"username":uname,"pic_url":pic,"profile_pic":pic,"friend_status":status})
    conn.close()
    return jsonify(result)
   
@app.route('/api/comment', methods=['POST'])
def api_comment():
    me=session.get('username'); data=request.json; pid=data.get('post_id'); txt=data.get('text','')[:200]
    conn=get_conn(); c=conn.cursor()
    now=datetime.now().isoformat();c.execute("INSERT INTO comments (post_id,username,text,created_at) VALUES (%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO comments (post_id,username,text,created_at) VALUES (?,?,?,?)",(pid,me,txt,now))
    try:
        qown="SELECT username FROM posts WHERE id=%s" if USE_POSTGRES else "SELECT username FROM posts WHERE id=?";c.execute(qown,(pid,));own=c.fetchone()
        if own and own[0]!=me:
            qn="INSERT INTO notifications (username,type,from_user,text,created_at,is_read) VALUES (%s,%s,%s,%s,%s,0)" if USE_POSTGRES else "INSERT INTO notifications (username,type,from_user,text,created_at,is_read) VALUES (?,?,?,?,?,0)";c.execute(qn,(own[0],'comment',me,me+' commented on your post',now))
    except: pass
    for mention in get_mentions(txt):
        try:
            qu="SELECT username FROM auth WHERE username=%s" if USE_POSTGRES else "SELECT username FROM auth WHERE username=?";c.execute(qu,(mention,))
            if c.fetchone() and mention!=me:
                qn="INSERT INTO notifications (username,type,from_user,text,created_at,is_read) VALUES (%s,%s,%s,%s,%s,0)" if USE_POSTGRES else "INSERT INTO notifications (username,type,from_user,text,created_at,is_read) VALUES (?,?,?,?,?,0)";c.execute(qn,(mention,'mention',me,me+' mentioned you in a comment',now))
        except:pass
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/api/stories')
def api_stories():
    me=session.get('username')
    if not me:return jsonify([])
    conn=get_conn();cur=conn.cursor();now=datetime.now().isoformat()
    try:
        q="SELECT id,username,media_url,text,created_at FROM stories WHERE expires_at>%s ORDER BY id DESC" if USE_POSTGRES else "SELECT id,username,media_url,text,created_at FROM stories WHERE expires_at>? ORDER BY id DESC";cur.execute(q,(now,));rows=cur.fetchall()
    except:rows=[]
    allowed={me}
    try:
        qf="SELECT sender,receiver FROM friends WHERE (sender=%s OR receiver=%s) AND status='accepted'" if USE_POSTGRES else "SELECT sender,receiver FROM friends WHERE (sender=? OR receiver=?) AND status='accepted'";cur.execute(qf,(me,me));
        for a,b in cur.fetchall():allowed.add(b if a==me else a)
    except:pass
    result=[{"id":r[0],"username":r[1],"media_url":r[2] or "","text":r[3] or "","created_at":str(r[4])} for r in rows if r[1] in allowed]
    conn.close();return jsonify(result)

@app.route('/api/story', methods=['POST'])
def api_story():
    me=session.get('username'); f=request.files.get('media'); txt=request.form.get('text','')[:200]
    if not f or not f.filename: return jsonify({"ok":False,"error":"no file"}),400
    url=upload_to_cloud(f)
    if not url: return jsonify({"ok":False,"error":"Add Cloudinary keys in Render"}),500
    conn=get_conn(); c=conn.cursor(); now=datetime.now(); exp=now+timedelta(hours=24)
    c.execute("INSERT INTO stories (username,media_url,text,created_at,expires_at) VALUES (%s,%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO stories (username,media_url,text,created_at,expires_at) VALUES (?,?,?,?,?)",(me,url,txt,now.isoformat(),exp.isoformat()))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/api/story/delete', methods=['POST'])
def api_story_delete():
    me=session.get('username'); data=request.json; sid=data.get('id')
    conn=get_conn(); c=conn.cursor()
    c.execute("DELETE FROM stories WHERE id=%s AND username=%s" if USE_POSTGRES else "DELETE FROM stories WHERE id=? AND username=?", (sid,me)); conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/api/story/text', methods=['POST'])
def api_story_text():
    me=session.get('username'); data=request.json; txt=data.get('text','')[:100]
    conn=get_conn(); c=conn.cursor(); now=datetime.now(); exp=now+timedelta(hours=24)
    c.execute("INSERT INTO stories (username,media_url,text,created_at,expires_at) VALUES (%s,%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO stories (username,media_url,text,created_at,expires_at) VALUES (?,?,?,?,?)", (me,"",txt,now.isoformat(),exp.isoformat()))
    conn.commit(); conn.close(); return jsonify({"ok":True})

@app.route('/api/story/viewers')
def api_story_viewers():
    me=session.get('username');sid=request.args.get('id');conn=get_conn();c=conn.cursor();q="SELECT username FROM stories WHERE id=%s" if USE_POSTGRES else "SELECT username FROM stories WHERE id=?";c.execute(q,(sid,));own=c.fetchone()
    if not own or own[0]!=me:conn.close();return jsonify({"count":0,"viewers":[]})
    qv="SELECT viewer FROM story_views WHERE story_id=%s" if USE_POSTGRES else "SELECT viewer FROM story_views WHERE story_id=?";c.execute(qv,(sid,));rows=[x[0] for x in c.fetchall()];conn.close();return jsonify({"count":len(rows),"viewers":rows})

@app.route('/api/story/react',methods=['POST'])
def api_story_react():
    me=session.get('username');d=request.get_json(silent=True) or {};sid=d.get('id');reaction=str(d.get('reaction',''))[:8];conn=get_conn();c=conn.cursor();q="INSERT INTO story_reactions (story_id,username,reaction) VALUES (%s,%s,%s) ON CONFLICT (story_id,username) DO UPDATE SET reaction=%s" if USE_POSTGRES else "INSERT OR REPLACE INTO story_reactions (story_id,username,reaction) VALUES (?,?,?)";c.execute(q,(sid,me,reaction,reaction) if USE_POSTGRES else (sid,me,reaction));
    try:
        qo="SELECT username FROM stories WHERE id=%s" if USE_POSTGRES else "SELECT username FROM stories WHERE id=?";c.execute(qo,(sid,));o=c.fetchone()
        conn.commit();conn.close();
        if o:notify(o[0],'story_reaction',me,me+' reacted to your story')
        return jsonify({"ok":True})
    except Exception:
        conn.rollback();conn.close();return jsonify({"ok":False}),500

@app.route('/api/story/view', methods=['POST'])
def api_story_view():
    me=session.get('username'); data=request.json; sid=data.get('id'); conn=get_conn(); c=conn.cursor()
    try: c.execute("INSERT INTO story_views VALUES (%s,%s) ON CONFLICT DO NOTHING" if USE_POSTGRES else "INSERT OR IGNORE INTO story_views VALUES (?,?)", (sid,me)); conn.commit()
    except: pass
    conn.close(); return jsonify({"ok":True})

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
    c.execute("SELECT id,sender,text,media_url,reply_to,read,deleted_at FROM messages WHERE (sender=%s AND receiver=%s) OR (sender=%s AND receiver=%s) ORDER BY id ASC" if USE_POSTGRES else "SELECT id,sender,text,media_url,reply_to,read,deleted_at FROM messages WHERE (sender=? AND receiver=?) OR (sender=? AND receiver=?) ORDER BY id ASC",(me,other,other,me))
    rows=c.fetchall(); conn.close()
    out=[]
    for r in rows:
        conn2=get_conn();cc=conn2.cursor();qr="SELECT reaction,COUNT(*) FROM message_reactions WHERE message_id=%s GROUP BY reaction" if USE_POSTGRES else "SELECT reaction,COUNT(*) FROM message_reactions WHERE message_id=? GROUP BY reaction";cc.execute(qr,(r[0],));rx=[{"reaction":x[0],"count":x[1]} for x in cc.fetchall()];conn2.close();out.append({"id":r[0],"sender":r[1],"text":r[2],"media_url":r[3],"reply_to":r[4],"read":r[5],"deleted":bool(r[6]),"reactions":rx,"media_type":("audio" if str(r[3] or "").lower().endswith((".mp3",".wav",".ogg",".m4a",".webm")) and "voice" in str(r[3] or "").lower() else "")})
    return jsonify(out)

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

@app.route('/api/messages/search')
def api_messages_search():
    me=session.get('username');other=request.args.get('with','');q='%'+request.args.get('q','').lower()+'%';conn=get_conn();c=conn.cursor();sql="SELECT sender,text FROM messages WHERE ((sender=%s AND receiver=%s) OR (sender=%s AND receiver=%s)) AND LOWER(COALESCE(text,'')) LIKE %s ORDER BY id DESC LIMIT 50" if USE_POSTGRES else "SELECT sender,text FROM messages WHERE ((sender=? AND receiver=?) OR (sender=? AND receiver=?)) AND LOWER(COALESCE(text,'')) LIKE ? ORDER BY id DESC LIMIT 50";c.execute(sql,(me,other,other,me,q));rows=c.fetchall();conn.close();return jsonify([{"sender":r[0],"text":r[1]} for r in rows])

@app.route('/api/send', methods=['POST'])
def api_send():
    me = (session.get('username') or '').strip()
    other = (request.form.get('receiver') or '').strip()
    txt = (request.form.get('text') or '')[:500]
    reply_to = (request.form.get('reply_to') or '')[:100]
    f = request.files.get('media')

    if not me:
        return jsonify({"ok":False,"error":"Not logged in"}),401
    if not other:
        return jsonify({"ok":False,"error":"No recipient selected"}),400
    if other == me:
        return jsonify({"ok":False,"error":"You cannot message yourself"}),400
    if not txt and not (f and f.filename):
        return jsonify({"ok":False,"error":"empty"}),400

    conn = get_conn()
    c = conn.cursor()
    try:
        if is_blocked(me,other) or is_blocked(other,me):
            return jsonify({"ok":False,"error":"Messaging is unavailable between these accounts"}),403
        qp="SELECT message_privacy FROM profiles WHERE username=%s" if USE_POSTGRES else "SELECT message_privacy FROM profiles WHERE username=?";c.execute(qp,(other,));pr=c.fetchone()
        if pr and (pr[0] or 'friends')=='friends' and not is_friend(me,other):
            return jsonify({"ok":False,"error":"This user only accepts messages from friends"}),403
        q_user = "SELECT username FROM auth WHERE username=%s" if USE_POSTGRES else "SELECT username FROM auth WHERE username=?"
        c.execute(q_user, (other,))
        if not c.fetchone():
            return jsonify({"ok":False,"error":"Recipient not found"}),404

        url = upload_to_cloud(f) if f and f.filename else ''
        q = (
            "INSERT INTO messages (sender,receiver,text,media_url,reply_to,read,created_at) VALUES (%s,%s,%s,%s,%s,0,%s)"
            if USE_POSTGRES else
            "INSERT INTO messages (sender,receiver,text,media_url,reply_to,read,created_at) VALUES (?,?,?,?,?,0,?)"
        )
        now=datetime.now().isoformat(); c.execute(q, (me,other,txt,url,reply_to,now))
        conn.commit()
        notify(other,'message',me,me+' sent you a message')
        return jsonify({"ok":True})
    except Exception:
        conn.rollback()
        print("SEND MESSAGE ERROR:")
        traceback.print_exc()
        return jsonify({"ok":False,"error":"Server could not save the message"}),500
    finally:
        conn.close()

@app.route('/api/message/delete', methods=['POST'])
def api_message_delete():
    me=session.get('username'); data=request.json or {}; mid=data.get('id')
    conn=get_conn(); c=conn.cursor()
    q="UPDATE messages SET text=%s,deleted_at=%s WHERE id=%s AND sender=%s" if USE_POSTGRES else "UPDATE messages SET text=?,deleted_at=? WHERE id=? AND sender=?"
    c.execute(q,('This message was deleted',datetime.now().isoformat(),mid,me));conn.commit();ok=c.rowcount>0;conn.close();return jsonify({"ok":ok})

@app.route('/api/notifications')
def api_notifications():
    me=session.get('username'); conn=get_conn(); c=conn.cursor()
    c.execute("SELECT id,type,from_user,text,created_at FROM notifications WHERE username=%s ORDER BY id DESC LIMIT 50" if USE_POSTGRES else "SELECT id,type,from_user,text,created_at FROM notifications WHERE username=? ORDER BY id DESC LIMIT 50",(me,))
    rows=c.fetchall(); conn.close()
    return jsonify([{"id":r[0],"type":r[1],"from_user":r[2],"text":r[3],"created_at":r[4]} for r in rows])

@app.route('/api/notifications/read',methods=['POST'])
def api_notifications_read():
    me=session.get('username');conn=get_conn();c=conn.cursor();q="UPDATE notifications SET is_read=1 WHERE username=%s" if USE_POSTGRES else "UPDATE notifications SET is_read=1 WHERE username=?";c.execute(q,(me,));conn.commit();conn.close();return jsonify({"ok":True})

@app.route('/api/notifications/count')
def api_notifications_count():
    me=session.get('username'); conn=get_conn(); c=conn.cursor()
    c.execute("SELECT COUNT(*) FROM notifications WHERE username=%s AND is_read=0" if USE_POSTGRES else "SELECT COUNT(*) FROM notifications WHERE username=? AND is_read=0",(me,))
    cnt=c.fetchone()[0]; conn.close(); return jsonify({"count":cnt})

@app.route('/api/notifications/clear', methods=['POST'])
def api_notifications_clear():
    me=session.get('username'); conn=get_conn(); c=conn.cursor()
    c.execute("DELETE FROM notifications WHERE username=%s" if USE_POSTGRES else "DELETE FROM notifications WHERE username=?",(me,)); conn.commit(); conn.close(); return jsonify({"ok":True})



@app.route('/api/security/logout_all',methods=['POST'])
def api_logout_all():
    me=session.get('username');conn=get_conn();c=conn.cursor();q="UPDATE auth SET session_version=COALESCE(session_version,1)+1 WHERE username=%s" if USE_POSTGRES else "UPDATE auth SET session_version=COALESCE(session_version,1)+1 WHERE username=?";c.execute(q,(me,));conn.commit();conn.close();session.clear();return jsonify({"ok":True})

@app.route('/api/profile/me')
def api_profile_me():
    me=session.get('username');
    if not me:return jsonify({"error":"Not logged in"}),401
    conn=get_conn();c=conn.cursor();q="SELECT pic_url,bio,cover_url,private_account,message_privacy,show_last_seen,show_read_receipts FROM profiles WHERE username=%s" if USE_POSTGRES else "SELECT pic_url,bio,cover_url,private_account,message_privacy,show_last_seen,show_read_receipts FROM profiles WHERE username=?";c.execute(q,(me,));r=c.fetchone();conn.close();r=r or ('','','',0,'friends',1,1);return jsonify({"username":me,"pic_url":r[0] or '',"bio":r[1] or '',"cover_url":r[2] or '',"private_account":int(r[3] or 0),"message_privacy":r[4] or 'friends',"show_last_seen":int(r[5] if r[5] is not None else 1),"show_read_receipts":int(r[6] if r[6] is not None else 1)})

@app.route('/api/profile/update',methods=['POST'])
def api_profile_update():
    me=session.get('username');data=request.get_json(silent=True) or {};bio=str(data.get('bio',''))[:500];conn=get_conn();c=conn.cursor();q="UPDATE profiles SET bio=%s WHERE username=%s" if USE_POSTGRES else "UPDATE profiles SET bio=? WHERE username=?";c.execute(q,(bio,me));conn.commit();conn.close();return jsonify({"ok":True})

@app.route('/api/profile/cover',methods=['POST'])
def api_profile_cover():
    me=session.get('username');f=request.files.get('media');url=upload_to_cloud(f)
    if not url:return jsonify({"ok":False,"error":"Could not upload cover"}),500
    conn=get_conn();c=conn.cursor();q="UPDATE profiles SET cover_url=%s WHERE username=%s" if USE_POSTGRES else "UPDATE profiles SET cover_url=? WHERE username=?";c.execute(q,(url,me));conn.commit();conn.close();return jsonify({"ok":True,"url":url})

@app.route('/api/profile/settings',methods=['POST'])
def api_profile_settings():
    me=session.get('username');data=request.get_json(silent=True) or {};allowed={k:data[k] for k in ('private_account','message_privacy','show_last_seen','show_read_receipts') if k in data};conn=get_conn();c=conn.cursor()
    if allowed:
        sets=[];vals=[]
        for k,v in allowed.items():sets.append(k+'=%s' if USE_POSTGRES else k+'=?');vals.append(v)
        vals.append(me);q='UPDATE profiles SET '+','.join(sets)+' WHERE username='+('%s' if USE_POSTGRES else '?');c.execute(q,tuple(vals))
    conn.commit();conn.close();return api_profile_me()

@app.route('/api/profile/<username>')
def api_public_profile(username):
    me=session.get('username');conn=get_conn();c=conn.cursor();q="SELECT pic_url,bio,cover_url,private_account FROM profiles WHERE username=%s" if USE_POSTGRES else "SELECT pic_url,bio,cover_url,private_account FROM profiles WHERE username=?";c.execute(q,(username,));r=c.fetchone();
    if not r:conn.close();return jsonify({"error":"User not found"}),404
    qf="SELECT COUNT(*) FROM friends WHERE (sender=%s OR receiver=%s) AND status='accepted'" if USE_POSTGRES else "SELECT COUNT(*) FROM friends WHERE (sender=? OR receiver=?) AND status='accepted'";c.execute(qf,(username,username));fc=c.fetchone()[0]
    q1="SELECT COUNT(*) FROM follows WHERE following=%s" if USE_POSTGRES else "SELECT COUNT(*) FROM follows WHERE following=?";c.execute(q1,(username,));followers=c.fetchone()[0]
    q2="SELECT 1 FROM follows WHERE follower=%s AND following=%s" if USE_POSTGRES else "SELECT 1 FROM follows WHERE follower=? AND following=?";c.execute(q2,(me,username));following_me=bool(c.fetchone())
    qb="SELECT 1 FROM blocked_users WHERE blocker=%s AND blocked=%s" if USE_POSTGRES else "SELECT 1 FROM blocked_users WHERE blocker=? AND blocked=?";c.execute(qb,(me,username));blocked=bool(c.fetchone());conn.close();return jsonify({"username":username,"pic_url":r[0] or '',"bio":r[1] or '',"cover_url":r[2] or '',"private_account":int(r[3] or 0),"friends_count":fc,"followers":followers,"following_me":following_me,"blocked":blocked})

@app.route('/api/follow',methods=['POST'])
def api_follow():
    me=session.get('username');u=(request.get_json(silent=True) or {}).get('username','');
    if not me or not u or me==u:return jsonify({"ok":False,"error":"Invalid user"}),400
    conn=get_conn();c=conn.cursor();q="SELECT 1 FROM follows WHERE follower=%s AND following=%s" if USE_POSTGRES else "SELECT 1 FROM follows WHERE follower=? AND following=?";c.execute(q,(me,u));exists=bool(c.fetchone())
    if exists:q2="DELETE FROM follows WHERE follower=%s AND following=%s" if USE_POSTGRES else "DELETE FROM follows WHERE follower=? AND following=?";c.execute(q2,(me,u));conn.commit();conn.close();return jsonify({"ok":True,"following":False})
    q2="INSERT INTO follows (follower,following) VALUES (%s,%s)" if USE_POSTGRES else "INSERT INTO follows (follower,following) VALUES (?,?)";c.execute(q2,(me,u));conn.commit();conn.close();notify(u,'follow',me,me+' followed you');return jsonify({"ok":True,"following":True})

@app.route('/api/block',methods=['POST'])
def api_block():
    me=session.get('username');u=(request.get_json(silent=True) or {}).get('username','');
    if not me or not u:return jsonify({"ok":False}),400
    conn=get_conn();c=conn.cursor();q="SELECT 1 FROM blocked_users WHERE blocker=%s AND blocked=%s" if USE_POSTGRES else "SELECT 1 FROM blocked_users WHERE blocker=? AND blocked=?";c.execute(q,(me,u));exists=bool(c.fetchone())
    if exists:q2="DELETE FROM blocked_users WHERE blocker=%s AND blocked=%s" if USE_POSTGRES else "DELETE FROM blocked_users WHERE blocker=? AND blocked=?";c.execute(q2,(me,u));blocked=False
    else:q2="INSERT INTO blocked_users (blocker,blocked) VALUES (%s,%s)" if USE_POSTGRES else "INSERT INTO blocked_users (blocker,blocked) VALUES (?,?)";c.execute(q2,(me,u));blocked=True
    conn.commit();conn.close();return jsonify({"ok":True,"blocked":blocked})

@app.route('/api/friend/remove',methods=['POST'])
def api_friend_remove():
    me=session.get('username');u=(request.get_json(silent=True) or {}).get('username','');conn=get_conn();c=conn.cursor();q="DELETE FROM friends WHERE ((sender=%s AND receiver=%s) OR (sender=%s AND receiver=%s)) AND status='accepted'" if USE_POSTGRES else "DELETE FROM friends WHERE ((sender=? AND receiver=?) OR (sender=? AND receiver=?)) AND status='accepted'";c.execute(q,(me,u,u,me));conn.commit();conn.close();return jsonify({"ok":True})

@app.route('/api/report',methods=['POST'])
def api_report():
    me=session.get('username');d=request.get_json(silent=True) or {};tt=str(d.get('target_type',''))[:20];tid=str(d.get('target_id',''))[:100];reason=str(d.get('reason',''))[:300];
    if not me or not tt or not tid:return jsonify({"ok":False}),400
    conn=get_conn();c=conn.cursor();q="INSERT INTO reports (reporter,target_type,target_id,reason,created_at) VALUES (%s,%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO reports (reporter,target_type,target_id,reason,created_at) VALUES (?,?,?,?,?)";c.execute(q,(me,tt,tid,reason,datetime.now().isoformat()));conn.commit();conn.close();return jsonify({"ok":True})

@app.route('/api/message/react',methods=['POST'])
def api_message_react():
    me=session.get('username');d=request.get_json(silent=True) or {};mid=d.get('id');reaction=str(d.get('reaction',''))[:8];conn=get_conn();c=conn.cursor();q="SELECT 1 FROM message_reactions WHERE message_id=%s AND username=%s" if USE_POSTGRES else "SELECT 1 FROM message_reactions WHERE message_id=? AND username=?";c.execute(q,(mid,me));exists=bool(c.fetchone())
    if exists:
        q2="UPDATE message_reactions SET reaction=%s WHERE message_id=%s AND username=%s" if USE_POSTGRES else "UPDATE message_reactions SET reaction=? WHERE message_id=? AND username=?";c.execute(q2,(reaction,mid,me))
    else:
        q2="INSERT INTO message_reactions (message_id,username,reaction) VALUES (%s,%s,%s)" if USE_POSTGRES else "INSERT INTO message_reactions (message_id,username,reaction) VALUES (?,?,?)";c.execute(q2,(mid,me,reaction))
    conn.commit();conn.close();return jsonify({"ok":True})

@app.route('/api/message/edit',methods=['POST'])
def api_message_edit():
    me=session.get('username');d=request.get_json(silent=True) or {};mid=d.get('id');text=str(d.get('text',''))[:500];conn=get_conn();c=conn.cursor();q="UPDATE messages SET text=%s,edited_at=%s WHERE id=%s AND sender=%s AND deleted_at IS NULL" if USE_POSTGRES else "UPDATE messages SET text=?,edited_at=? WHERE id=? AND sender=? AND deleted_at IS NULL";c.execute(q,(text,datetime.now().isoformat(),mid,me));conn.commit();ok=c.rowcount>0;conn.close();return jsonify({"ok":ok,"error":None if ok else 'Message cannot be edited'})

@app.route('/api/typing',methods=['POST'])
def api_typing():
    me=session.get('username');peer=(request.get_json(silent=True) or {}).get('peer','');conn=get_conn();c=conn.cursor();now=time.time();q="INSERT INTO user_typing (username,peer,last_seen) VALUES (%s,%s,%s) ON CONFLICT (username,peer) DO UPDATE SET last_seen=%s" if USE_POSTGRES else "INSERT OR REPLACE INTO user_typing (username,peer,last_seen) VALUES (?,?,?)";c.execute(q,(me,peer,now,now) if USE_POSTGRES else (me,peer,now));conn.commit();conn.close();return jsonify({"ok":True})

@app.route('/api/typing')
def api_typing_get():
    me=session.get('username');peer=request.args.get('peer','');conn=get_conn();c=conn.cursor();q="SELECT last_seen FROM user_typing WHERE username=%s AND peer=%s" if USE_POSTGRES else "SELECT last_seen FROM user_typing WHERE username=? AND peer=?";c.execute(q,(peer,me));r=c.fetchone();conn.close();return jsonify({"typing":bool(r and time.time()-float(r[0])<4)})

@app.route('/api/comments')
def api_comments():
    pid=request.args.get('post_id');conn=get_conn();c=conn.cursor();q="SELECT username,text,created_at FROM comments WHERE post_id=%s ORDER BY id ASC" if USE_POSTGRES else "SELECT username,text,created_at FROM comments WHERE post_id=? ORDER BY id ASC";c.execute(q,(pid,));rows=c.fetchall();conn.close();return jsonify([{"username":r[0],"text":r[1],"created_at":r[2]} for r in rows])

@app.route('/api/post/share',methods=['POST'])
def api_post_share():
    me=session.get('username');pid=(request.get_json(silent=True) or {}).get('post_id');conn=get_conn();c=conn.cursor();now=datetime.now().isoformat()
    try:
        q="SELECT username,text,media_url FROM posts WHERE id=%s" if USE_POSTGRES else "SELECT username,text,media_url FROM posts WHERE id=?";c.execute(q,(pid,));orig=c.fetchone()
        if not orig:return jsonify({"ok":False,"error":"Post not found"}),404
        qs="INSERT INTO post_shares (post_id,username,created_at) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING" if USE_POSTGRES else "INSERT OR IGNORE INTO post_shares (post_id,username,created_at) VALUES (?,?,?)";c.execute(qs,(pid,me,now))
        qp="INSERT INTO posts (username,text,media_url,created_at,shared_post_id) VALUES (%s,%s,%s,%s,%s)" if USE_POSTGRES else "INSERT INTO posts (username,text,media_url,created_at,shared_post_id) VALUES (?,?,?,?,?)";c.execute(qp,(me,'🔄 Shared a post','',now,pid))
        conn.commit();notify(orig[0],'share',me,me+' shared your post');return jsonify({"ok":True})
    except Exception:conn.rollback();return jsonify({"ok":False,"error":"Could not share"}),500
    finally:conn.close()

@app.route('/api/global-search')
def api_global_search():
    me=session.get('username');q=request.args.get('q','').strip();conn=get_conn();c=conn.cursor();like='%'+q.lower()+'%';qp="SELECT id,username,text,created_at FROM posts WHERE LOWER(COALESCE(text,'')) LIKE %s OR LOWER(username) LIKE %s ORDER BY id DESC LIMIT 30" if USE_POSTGRES else "SELECT id,username,text,created_at FROM posts WHERE LOWER(COALESCE(text,'')) LIKE ? OR LOWER(username) LIKE ? ORDER BY id DESC LIMIT 30";c.execute(qp,(like,like));rows=c.fetchall();conn.close();return jsonify({"posts":[{"id":r[0],"username":r[1],"text":r[2],"created_at":str(r[3])} for r in rows]})

@app.route('/static/uploads/<path:filename>')
def uploads(filename): return send_from_directory('static/uploads', filename)

if __name__=='__main__':
    port=int(os.environ.get("PORT",5000)); app.run(host='0.0.0.0',port=port)
