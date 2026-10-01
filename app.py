from flask import Flask,request,jsonify,send_from_directory,render_template_string,session,redirect
import sqlite3,os,secrets,base64,io,time
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from werkzeug.security import generate_password_hash,check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image

app=Flask(__name__)
app.secret_key=os.getenv("SECRET_KEY",secrets.token_hex(32))
DB="proveam.db"
UP="uploads"
os.makedirs(UP,exist_ok=True)
ACCRA=ZoneInfo("Africa/Accra")
hits={}

def rate(ip,lim=20,s=60):
 n=time.time()
 l=hits.get(ip,[])
 l=[t for t in l if n-t<s]
 if len(l)>=lim: return True
 l.append(n);hits[ip]=l
 return False

def init():
 c=sqlite3.connect(DB)
 cur=c.cursor()
 cur.execute("CREATE TABLE IF NOT EXISTS auth (username TEXT PRIMARY KEY,password TEXT,created_at TEXT)")
 cur.execute("CREATE TABLE IF NOT EXISTS posts (id INTEGER PRIMARY KEY,username TEXT,image_path TEXT,type TEXT,time TEXT,created_at TEXT)")
 cur.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY,streak INT,last_date TEXT,longest INT)")
 c.commit();c.close()
init()

def csrf():
 if 'csrf_token' not in session: session['csrf_token']=secrets.token_hex(16)
 return session['csrf_token']

def stats(u):
 con=sqlite3.connect(DB);cur=con.cursor()
 cur.execute("SELECT streak,last_date,longest FROM users WHERE username=?",(u,));r=cur.fetchone()
 cur.execute("SELECT COUNT(*) FROM posts WHERE username=? AND type='proven'",(u,));pr=cur.fetchone()[0]
 cur.execute("SELECT COUNT(*) FROM posts WHERE username=?",(u,));tot=cur.fetchone()[0]
 cur.execute("SELECT created_at FROM auth WHERE username=?",(u,));j=cur.fetchone()
 con.close()
 return {"streak":r[0] if r else 0,"last":r[1] if r and r[1] else None,"longest":r[2] if r else 0,"proven":pr,"total":tot,"joined":j[0] if j else "?"}

LOGIN="""<!DOCTYPE html><html><head><meta name=viewport content="width=device-width,initial-scale=1"><style>body{background:#000;color:#fff;font-family:system-ui;display:flex;justify-content:center;align-items:center;height:100vh}.b{background:#111;border:1px solid #222;padding:25px;border-radius:16px;width:90%;max-width:350px;text-align:center}.l{width:70px;height:70px;border-radius:50%;border:2px solid #D4AF37} h1{color:#D4AF37} input{width:100%;padding:12px;margin:8px 0;background:#000;border:1px solid #333;color:#fff;border-radius:10px}.btn{width:100%;padding:12px;background:#D4AF37;color:#000;font-weight:900;border:none;border-radius:10px} a{color:#D4AF37;font-size:12px}</style></head><body><div class=b><img src=/logo.jpg class=l><h1>PROVE AM</h1><h3 id=t>Login</h3><input id=u placeholder=Username><input id=p type=password placeholder=Password><button class=btn onclick=go()>Continue</button><p><a href=# onclick=tog() id=lk>No account? Sign Up</a> • <a href=/forgot>Forgot?</a></p><p id=m style=color:#f55;font-size:12px></p></div><script>let mode='login';function tog(){mode=mode=='login'?'signup':'login';document.getElementById('t').innerText=mode=='login'?'Login':'Sign Up';document.getElementById('lk').innerText=mode=='login'?'No account? Sign Up':'Have account? Login'} async function go(){let u=document.getElementById('u').value,p=document.getElementById('p').value;let r=await fetch('/'+mode,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p,csrf_token:'{{CSRF}}'})});let d=await r.json();if(d.ok)location.href='/';else document.getElementById('m').innerText=d.error}</script></body></html>"""

FEED="""<!DOCTYPE html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>PROVE AM</title><style>*{margin:0;padding:0;box-sizing:border-box;font-family:system-ui}body{background:#000;color:#fff}.h{text-align:center;padding:15px;border-bottom:1px solid #222;position:relative}.logo{width:70px;height:70px;border-radius:50%;border:2px solid #D4AF37}.links{position:absolute;top:15px;right:15px;display:flex;gap:8px}.links a{color:#888;font-size:11px;border:1px solid #333;padding:5px 8px;border-radius:20px;text-decoration:none}h1{color:#D4AF37;font-weight:900}.bar{background:#111;border:1px solid #D4AF37;margin:12px;border-radius:12px;padding:12px;display:flex;justify-content:space-between}.ctrl{display:flex;gap:10px;padding:0 12px}.b{flex:1;padding:12px;border-radius:12px;border:none;font-weight:800}.bp{background:#D4AF37;color:#000}.bg{background:#222;color:#fff;border:1px solid #444}.feed{padding:12px;display:flex;flex-direction:column;gap:12px}.card{background:#111;border:1px solid #222;border-radius:16px;overflow:hidden}.ct{padding:8px 10px;display:flex;justify-content:space-between;font-size:13px}video{width:100%;border-radius:12px;display:none}#ca{display:none;gap:10px;margin-top:10px}</style></head><body><div class=h><div class=links><a href=/profile>Profile</a><a href=/logout>Logout</a></div><img src=/logo.jpg class=logo><h1>PROVE AM</h1><div style=color:#666;font-size:11px>@{{U}}</div></div><div class=bar><div>Streak: <span id=s style=color:#D4AF37;font-weight:900>0</span></div><div id=lg style=font-size:11px;color:#666></div></div><div class=ctrl><button class="b bp" onclick=start()>📸 PROVE AM</button><button class="b bg" onclick=document.getElementById('gi').click()>🖼️ Gallery</button></div><div style=padding:0 12px><video id=v autoplay playsinline></video><canvas id=c style=display:none></canvas><div id=ca><button class="b bp" onclick=cap()>CAPTURE</button><button class="b bg" onclick=stop()>Cancel</button></div></div><input type=file id=gi accept=image/* style=display:none><div class=feed id=f></div><script>const CSRF='{{CSRF}}';let stream=null;async function start(){let v=document.getElementById('v');try{stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:"user"}});v.srcObject=stream;v.style.display='block';document.getElementById('ca').style.display='flex'}catch(e){alert('Camera')}}function stop(){if(stream)stream.getTracks().forEach(t=>t.stop());document.getElementById('v').style.display='none';document.getElementById('ca').style.display='none'}function cap(){let v=document.getElementById('v'),cn=document.getElementById('c');cn.width=v.videoWidth;cn.height=v.videoHeight;cn.getContext('2d').drawImage(v,0,0);up(cn.toDataURL('image/jpeg',0.6),'proven');stop()}document.getElementById('gi').addEventListener('change',e=>{let f=e.target.files[0];if(!f)return;let r=new FileReader();r.onload=ev=>up(ev.target.result,'unverified');r.readAsDataURL(f)});async function up(img,type){let res=await fetch('/upload',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({image:img,type:type,csrf_token:CSRF})});let d=await res.json();if(d.ok){load();st()}else alert(d.error)}async function load(){let r=await fetch('/feed');let p=await r.json();document.getElementById('f').innerHTML=p.map(x=>`<div class=card><div class=ct><b>@${x.username}</b><span style="padding:3px 7px;border-radius:20px;font-size:9px;font-weight:900;${x.type=='proven'?'background:#D4AF37;color:#000':'background:#333;color:#999'}">${x.type=='proven'?'✓ PROVEN':'◐ UNVERIFIED'}</span></div><img src="${x.image_path}" style=width:100%><div style=padding:8px;font-size:11px;color:#555>${x.time}</div></div>`).join('')}async function st(){let r=await fetch('/streak');let d=await r.json();let fl=d.streak==0?'':d.streak<7?'🟡 ':d.streak<30?'🔥 ':'👑 ';document.getElementById('s').innerText=fl+d.streak+' days';document.getElementById('lg').innerText='Longest: '+d.longest}setInterval(load,4000);load();st();</script></body></html>"""

@app.route('/login',methods=['GET','POST'])
def log():
 if request.method=='GET': return render_template_string(LOGIN,CSRF=csrf())
 if rate(request.remote_addr): return jsonify({"ok":False,"error":"Slow"}),429
 d=request.json
 if d.get('csrf_token')!=session.get('csrf_token'): return jsonify({"ok":False,"error":"CSRF"}),403
 u=d.get('username','').strip()[:20];p=d.get('password','')
 con=sqlite3.connect(DB);cur=con.cursor();cur.execute("SELECT password FROM auth WHERE username=?",(u,));r=cur.fetchone();con.close()
 if not r or not check_password_hash(r[0],p): return jsonify({"ok":False,"error":"Wrong"})
 session['username']=u;session['csrf_token']=secrets.token_hex(16)
 return jsonify({"ok":True})

@app.route('/signup',methods=['POST'])
def sign():
 d=request.json
 if d.get('csrf_token')!=session.get('csrf_token'): return jsonify({"ok":False,"error":"CSRF"}),403
 u=d.get('username','').strip()[:20];p=d.get('password','')
 if len(u)<3 or len(p)<4: return jsonify({"ok":False,"error":"3 chars user 4 pass"})
 con=sqlite3.connect(DB);cur=con.cursor();cur.execute("SELECT 1 FROM auth WHERE username=?",(u,))
 if cur.fetchone(): con.close(); return jsonify({"ok":False,"error":"Taken"})
 cur.execute("INSERT INTO auth VALUES (?,?,?)",(u,generate_password_hash(p),datetime.now(ACCRA).strftime("%Y-%m-%d")));con.commit();con.close()
 session['username']=u;session['csrf_token']=secrets.token_hex(16)
 return jsonify({"ok":True})

@app.route('/forgot',methods=['GET','POST'])
def forgot():
 if request.method=='GET': return render_template_string(f"<html><body style='background:#000;color:#fff;text-align:center;padding:30px;font-family:system-ui'><h2 style='color:#D4AF37'>Reset</h2><input id=u placeholder=Username style=padding:10px><input id=p type=password placeholder='New' style=padding:10px><br><button onclick=\"fetch('/forgot',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{username:document.getElementById('u').value,password:document.getElementById('p').value,csrf_token:'{csrf()}'}})}}).then(r=>r.json()).then(d=>alert(d.ok?'Changed':'Fail'))\" style='background:#D4AF37;padding:10px;border:none;border-radius:8px;margin-top:10px'>Reset</button><p><a href=/login style=color:#D4AF37>Back</a></p></body></html>")
 d=request.json;u=d.get('username','');p=d.get('password','')
 con=sqlite3.connect(DB);cur=con.cursor();cur.execute("SELECT 1 FROM auth WHERE username=?",(u,))
 if not cur.fetchone(): con.close(); return jsonify({"ok":False,"error":"No user"})
 cur.execute("UPDATE auth SET password=? WHERE username=?",(generate_password_hash(p),u));con.commit();con.close()
 return jsonify({"ok":True})

@app.route('/logo.jpg')
def logo(): return send_from_directory('.', 'logo.jpg')
@app.route('/uploads/<path:n>')
def upf(n): return send_from_directory(UP, n)
@app.route('/logout')
def out(): session.clear(); return redirect('/login')
@app.route('/')
def home():
 if 'username' not in session: return redirect('/login')
 return render_template_string(FEED,U=session['username'],CSRF=csrf())
@app.route('/profile')
def prof():
 if 'username' not in session: return redirect('/login')
 s=stats(session['username']);return render_template_string(f"<html><body style='background:#000;color:#fff;text-align:center;padding:20px;font-family:system-ui'><img src=/logo.jpg style='width:80px;height:80px;border-radius:50%;border:2px solid #D4AF37'><h2>@{session['username']}</h2><p>Joined {s['joined']}</p><div style='background:#111;border:1px solid #222;border-radius:12px;padding:15px;text-align:left'>Streak:{s['streak']}<br>Longest:{s['longest']}<br>Proven:{s['proven']}<br>Total:{s['total']}</div><p><a href=/ style=color:#D4AF37>Back</a></p></body></html>")
@app.route('/upload',methods=['POST'])
def upl():
 if 'username' not in session: return jsonify({"ok":False,"error":"Login"}),401
 if rate(request.remote_addr): return jsonify({"ok":False,"error":"Slow"}),429
 d=request.json
 if d.get('csrf_token')!=session.get('csrf_token'): return jsonify({"ok":False,"error":"CSRF"}),403
 b64=d.get('image','')
 try:
  if ',' in b64: b64=b64.split(',',1)[1]
  dat=base64.b64decode(b64)
  if len(dat)>5*1024*1024: return jsonify({"ok":False,"error":"5MB max"}),400
  im=Image.open(io.BytesIO(dat));im.thumbnail((2000,2000))
  buf=io.BytesIO();im.convert('RGB').save(buf,format='JPEG',quality=70)
  dat=buf.getvalue()
 except Exception as e: return jsonify({"ok":False,"error":"Bad image"}),400
 u=session['username'];fn=secure_filename(f"{u}_{secrets.token_hex(8)}.jpg");p=os.path.join(UP,fn)
 open(p,'wb').write(dat)
 today=datetime.now(ACCRA).date();s=stats(u)
 if d.get('type')=='proven':
  if not s["last"]: ns=1
  else:
   try: ld=datetime.fromisoformat(s["last"]).date();delta=(today-ld).days;ns=s["streak"]+1 if delta==1 else 1 if delta!=0 else s["streak"]
   except: ns=1
  con=sqlite3.connect(DB);cur=con.cursor();cur.execute("INSERT OR REPLACE INTO users VALUES (?,?,?,?)",(u,ns,today.isoformat(),max(s["longest"],ns)));con.commit();con.close()
 con=sqlite3.connect(DB);cur=con.cursor();cur.execute("INSERT INTO posts (username,image_path,type,time,created_at) VALUES (?,?,?,?,?)",(u,f"/uploads/{fn}",d.get('type'),datetime.now(ACCRA).strftime("%H:%M"),datetime.now(ACCRA).isoformat()));con.commit();con.close()
 return jsonify({"ok":True})
@app.route('/feed')
def feed():
 if 'username' not in session: return jsonify([])
 con=sqlite3.connect(DB);cur=con.cursor();cur.execute("SELECT username,image_path,type,time FROM posts ORDER BY id DESC LIMIT 100");r=cur.fetchall();con.close()
 return jsonify([{"username":x[0],"image_path":x[1],"type":x[2],"time":x[3]} for x in r])
@app.route('/streak')
def stk():
 if 'username' not in session: return jsonify({"streak":0,"longest":0})
 s=stats(session['username']);return jsonify({"streak":s["streak"],"longest":s["longest"]})

if __name__=='__main__':
 app.run(host='0.0.0.0',port=int(os.getenv("PORT",5000)))
