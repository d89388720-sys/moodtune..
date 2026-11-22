"""MoodTunes: a privacy-conscious Flask music and wellbeing app."""
import base64
import json
import os
import secrets
from datetime import datetime, date
from functools import wraps

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()
db = SQLAlchemy()

MOODS = ["Happy", "Sad", "Stressed", "Relaxed", "Angry", "Lonely", "Motivated", "Romantic", "Sleepy", "Energetic", "Focused", "Anxious", "Excited", "Bored", "Peaceful", "Nostalgic"]
LANGUAGES = ["English", "Telugu", "Tamil", "Malayalam", "Kannada", "Hindi", "Bengali", "Punjabi", "Marathi", "Spanish", "Korean", "Japanese"]
THEMES = ["Midnight Purple", "Ocean Blue", "Rose Pink", "Lavender Dream", "Emerald Green", "Sunset Orange", "Crimson Red", "Golden Theme", "Minimal White", "AMOLED Black"]

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(40), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    profiles = db.relationship("Profile", cascade="all,delete-orphan")

class Profile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    kind = db.Column(db.String(20), default="Personal")
    theme = db.Column(db.String(40), default="Midnight Purple")
    preferences = db.Column(db.Text, default="{}")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class MoodEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("profile.id", ondelete="CASCADE"), nullable=False)
    mood = db.Column(db.String(30), nullable=False)
    note = db.Column(db.String(500), default="")
    source = db.Column(db.String(20), default="manual")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DiaryEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("profile.id", ondelete="CASCADE"), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    body = db.Column(db.Text, nullable=False)
    mood = db.Column(db.String(30), default="")
    tags = db.Column(db.String(300), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Playlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("profile.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PlaylistTrack(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    playlist_id = db.Column(db.Integer, db.ForeignKey("playlist.id", ondelete="CASCADE"), nullable=False)
    track_id = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    artist = db.Column(db.String(200), default="")
    position = db.Column(db.Integer, default=0)

class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("profile.id", ondelete="CASCADE"), nullable=False)
    item_type = db.Column(db.String(30), nullable=False)
    item_key = db.Column(db.String(200), nullable=False)
    label = db.Column(db.String(200), default="")

class GameSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("profile.id", ondelete="CASCADE"), nullable=False)
    game = db.Column(db.String(40), nullable=False)
    score = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AudiobookProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("profile.id", ondelete="CASCADE"), nullable=False)
    book_key = db.Column(db.String(120), nullable=False)
    seconds = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SpotifyConnection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("profile.id", ondelete="CASCADE"), unique=True, nullable=False)
    access_token = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text, nullable=False)
    expires_at = db.Column(db.Integer, nullable=False)

def make_app():
    app = Flask(__name__)
    app.config.update(SECRET_KEY=os.getenv("SECRET_KEY") or secrets.token_hex(32), SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///moodtunes.db").replace("postgres://", "postgresql://", 1), SQLALCHEMY_TRACK_MODIFICATIONS=False, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "false").lower() == "true", MAX_CONTENT_LENGTH=4 * 1024 * 1024)
    db.init_app(app)
    with app.app_context(): db.create_all()

    @app.before_request
    def csrf_guard():
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and request.path != "/spotify/callback":
            token = session.get("csrf_token")
            if not token or not secrets.compare_digest(token, request.headers.get("X-CSRF-Token", "")):
                return jsonify(error="Your session expired. Refresh the page and try again."), 403

    def auth(fn):
        @wraps(fn)
        def wrapped(*a, **kw):
            if not session.get("user_id"): return jsonify(error="Please sign in to continue."), 401
            return fn(*a, **kw)
        return wrapped

    def profile_required(fn):
        @wraps(fn)
        def wrapped(*a, **kw):
            if not session.get("user_id"): return jsonify(error="Please sign in to continue."), 401
            p = Profile.query.filter_by(id=session.get("profile_id"), user_id=session["user_id"]).first()
            if not p: return jsonify(error="Choose a profile first."), 400
            request.profile = p
            return fn(*a, **kw)
        return wrapped

    @app.get("/")
    def home(): return render_template("index.html")

    @app.get("/api/session")
    def whoami():
        u = User.query.get(session.get("user_id")) if session.get("user_id") else None
        session.setdefault("csrf_token", secrets.token_urlsafe(32))
        return jsonify(user={"name":u.name,"username":u.username} if u else None, profiles=[{"id":p.id,"name":p.name,"kind":p.kind,"theme":p.theme} for p in u.profiles] if u else [], active=session.get("profile_id"))

    @app.post("/api/register")
    def register():
        d=request.get_json() or {}; name=(d.get("name") or "").strip(); username=(d.get("username") or "").strip().lower(); email=(d.get("email") or "").strip().lower(); password=d.get("password") or ""
        if not name or len(username)<3 or "@" not in email or len(password)<10: return jsonify(error="Enter a name, username (3+ characters), valid email, and password (10+ characters)."),400
        if User.query.filter(db.or_(User.username==username,User.email==email)).first(): return jsonify(error="That username or email is already registered."),409
        csrf=session.get("csrf_token"); u=User(name=name,username=username,email=email,password_hash=generate_password_hash(password)); db.session.add(u); db.session.flush(); p=Profile(user_id=u.id,name=name,kind="Personal"); db.session.add(p); db.session.commit(); session.clear(); session["user_id"]=u.id; session["profile_id"]=p.id; session["csrf_token"]=csrf or secrets.token_urlsafe(32)
        return jsonify(ok=True)

    @app.post("/api/login")
    def login():
        d=request.get_json() or {}; identifier=(d.get("identifier") or "").strip().lower(); u=User.query.filter(db.or_(User.username==identifier,User.email==identifier)).first()
        if not u or not check_password_hash(u.password_hash,d.get("password") or ""): return jsonify(error="Username/email or password is incorrect."),401
        csrf=session.get("csrf_token"); session.clear(); session["csrf_token"]=csrf or secrets.token_urlsafe(32); session["user_id"]=u.id; p=Profile.query.filter_by(user_id=u.id).first(); session["profile_id"]=p.id if p else None
        return jsonify(ok=True)

    @app.post("/api/logout")
    def logout():
        csrf=session.get("csrf_token") or secrets.token_urlsafe(32); session.clear(); session["csrf_token"]=csrf; return jsonify(ok=True)

    @app.post("/api/profiles")
    @auth
    def profiles_create():
        d=request.get_json() or {}; name=(d.get("name") or "").strip(); kind=d.get("kind","Personal")
        if not name or kind not in ["Personal","Family","Kids","Guest"]: return jsonify(error="Enter a profile name and valid profile type."),400
        p=Profile(user_id=session["user_id"],name=name,kind=kind); db.session.add(p); db.session.commit(); return jsonify(id=p.id,name=p.name,kind=p.kind)

    @app.patch("/api/profile/settings")
    @profile_required
    def profile_settings():
        d=request.get_json() or {}
        if d.get("theme") in THEMES: request.profile.theme=d["theme"]
        try: prefs=json.loads(request.profile.preferences or "{}")
        except ValueError: prefs={}
        allowed={"accent","mode","fontSize","density"}
        prefs.update({k:v for k,v in d.items() if k in allowed})
        request.profile.preferences=json.dumps(prefs); db.session.commit(); return jsonify(ok=True,theme=request.profile.theme,preferences=prefs)

    @app.get("/api/playlists")
    @profile_required
    def playlist_list():
        ps=Playlist.query.filter_by(profile_id=request.profile.id).all()
        return jsonify([{"id":p.id,"name":p.name,"tracks":[{"id":t.track_id,"title":t.title,"artist":t.artist} for t in PlaylistTrack.query.filter_by(playlist_id=p.id).order_by(PlaylistTrack.position).all()]} for p in ps])

    @app.post("/api/playlists")
    @profile_required
    def playlist_create():
        name=(request.get_json() or {}).get("name", "").strip()
        if not name:return jsonify(error="Give your playlist a name."),400
        p=Playlist(profile_id=request.profile.id,name=name[:100]); db.session.add(p); db.session.commit(); return jsonify(id=p.id,name=p.name)

    @app.route("/api/playlists/<int:pid>",methods=["PATCH","DELETE"])
    @profile_required
    def playlist_item(pid):
        p=Playlist.query.filter_by(id=pid,profile_id=request.profile.id).first()
        if not p:return jsonify(error="Playlist not found."),404
        if request.method=="DELETE":db.session.delete(p);db.session.commit();return jsonify(ok=True)
        p.name=(request.get_json() or {}).get("name",p.name).strip()[:100];db.session.commit();return jsonify(ok=True)

    @app.post("/api/playlists/<int:pid>/tracks")
    @profile_required
    def playlist_track_add(pid):
        p=Playlist.query.filter_by(id=pid,profile_id=request.profile.id).first()
        if not p:return jsonify(error="Playlist not found."),404
        d=request.get_json() or {}; tid=str(d.get("id",""))[:100]; title=str(d.get("title",""))[:200]
        if not tid or not title:return jsonify(error="Select a valid track."),400
        pos=PlaylistTrack.query.filter_by(playlist_id=p.id).count();db.session.add(PlaylistTrack(playlist_id=p.id,track_id=tid,title=title,artist=str(d.get("artist",""))[:200],position=pos));db.session.commit();return jsonify(ok=True)

    @app.delete("/api/playlists/<int:pid>/tracks/<int:trackid>")
    @profile_required
    def playlist_track_delete(pid,trackid):
        p=Playlist.query.filter_by(id=pid,profile_id=request.profile.id).first();t=PlaylistTrack.query.filter_by(id=trackid,playlist_id=pid).first()
        if not p or not t:return jsonify(error="Track not found."),404
        db.session.delete(t);db.session.commit();return jsonify(ok=True)

    @app.post("/api/profiles/<int:pid>/switch")
    @auth
    def profile_switch(pid):
        if not Profile.query.filter_by(id=pid,user_id=session["user_id"]).first(): return jsonify(error="Profile not found."),404
        session["profile_id"]=pid; return jsonify(ok=True)

    @app.route("/api/profiles/<int:pid>",methods=["PATCH","DELETE"])
    @auth
    def profile_edit(pid):
        p=Profile.query.filter_by(id=pid,user_id=session["user_id"]).first()
        if not p:return jsonify(error="Profile not found."),404
        if request.method=="DELETE":
            if Profile.query.filter_by(user_id=session["user_id"]).count()<2:return jsonify(error="Keep at least one profile."),400
            db.session.delete(p); db.session.commit(); session["profile_id"]=Profile.query.filter_by(user_id=session["user_id"]).first().id; return jsonify(ok=True)
        d=request.get_json() or {}; p.name=(d.get("name") or p.name).strip(); p.kind=d.get("kind",p.kind); db.session.commit(); return jsonify(ok=True)

    @app.post("/api/moods")
    @profile_required
    def mood_save():
        d=request.get_json() or {}; mood=d.get("mood")
        if mood not in MOODS:return jsonify(error="Choose a supported mood."),400
        e=MoodEntry(profile_id=request.profile.id,mood=mood,note=(d.get("note") or "")[:500],source=d.get("source","manual")[:20]); db.session.add(e); db.session.commit(); return jsonify(id=e.id,mood=e.mood,created_at=e.created_at.isoformat())

    @app.get("/api/moods")
    @profile_required
    def moods_list():
        rows=MoodEntry.query.filter_by(profile_id=request.profile.id).order_by(MoodEntry.created_at.desc()).limit(365).all(); return jsonify([{"mood":e.mood,"note":e.note,"source":e.source,"date":e.created_at.isoformat()} for e in rows])

    @app.post("/api/diary")
    @profile_required
    def diary_create():
        d=request.get_json() or {}; title=(d.get("title") or "").strip(); body=(d.get("body") or "").strip()
        if not title or not body:return jsonify(error="A title and entry are required."),400
        e=DiaryEntry(profile_id=request.profile.id,title=title[:120],body=body[:10000],mood=d.get("mood",""),tags=(d.get("tags") or "")[:300]); db.session.add(e); db.session.commit(); return jsonify(id=e.id)

    @app.get("/api/diary")
    @profile_required
    def diary_list():
        rows=DiaryEntry.query.filter_by(profile_id=request.profile.id).order_by(DiaryEntry.created_at.desc()).all(); return jsonify([{"id":e.id,"title":e.title,"body":e.body,"mood":e.mood,"tags":e.tags,"date":e.created_at.isoformat()} for e in rows])

    @app.route("/api/diary/<int:eid>",methods=["PATCH","DELETE"])
    @profile_required
    def diary_item(eid):
        e=DiaryEntry.query.filter_by(id=eid,profile_id=request.profile.id).first()
        if not e:return jsonify(error="Entry not found."),404
        if request.method=="DELETE": db.session.delete(e); db.session.commit(); return jsonify(ok=True)
        d=request.get_json() or {}; e.title=(d.get("title") or e.title)[:120]; e.body=(d.get("body") or e.body)[:10000]; e.mood=d.get("mood",e.mood); e.tags=d.get("tags",e.tags); db.session.commit(); return jsonify(ok=True)

    @app.get("/api/favorites")
    @profile_required
    def favorites_list():return jsonify([{"type":f.item_type,"key":f.item_key,"label":f.label} for f in Favorite.query.filter_by(profile_id=request.profile.id).all()])

    @app.post("/api/favorites")
    @profile_required
    def favorites_toggle():
        d=request.get_json() or {}; key=str(d.get("key",""))[:200]; typ=str(d.get("type","song"))[:30]
        if not key:return jsonify(error="Missing item key."),400
        f=Favorite.query.filter_by(profile_id=request.profile.id,item_type=typ,item_key=key).first()
        if f:db.session.delete(f); db.session.commit(); return jsonify(favorite=False)
        db.session.add(Favorite(profile_id=request.profile.id,item_type=typ,item_key=key,label=str(d.get("label",""))[:200])); db.session.commit(); return jsonify(favorite=True)

    @app.post("/api/game-sessions")
    @profile_required
    def game_save():
        d=request.get_json() or {}; game=d.get("game", "")
        if game not in {"breathing","color","memory","garden","bubbles","mindfulness"}: return jsonify(error="Unknown game."),400
        try: score=max(0,min(100000,int(d.get("score",0))))
        except (ValueError,TypeError): score=0
        db.session.add(GameSession(profile_id=request.profile.id,game=game,score=score)); db.session.commit(); return jsonify(ok=True)

    @app.get("/api/quotes")
    def quotes():
        # A rotating set of original prompts keeps quote content attributed honestly.
        lines=["Make room for the next small good thing.","Rest is part of the rhythm.","You can begin again from exactly here.","A gentle pace still moves you forward.","Let today be a little softer than yesterday.","You are allowed to grow at your own speed.","Small steps count, especially on hard days.","Notice one thing that is working.","Your attention is a place you can return to.","Hope can be quiet and still be real."]
        n=date.today().toordinal(); return jsonify(text=lines[n%len(lines)],author="MoodTunes",date=date.today().isoformat())

    @app.post("/api/ai/text")
    @profile_required
    def ai_text():
        key=os.getenv("EMERGENT_API_KEY"); text=(request.get_json() or {}).get("text","").strip()
        if not text or len(text)>3000:return jsonify(error="Describe your day in 1–3000 characters."),400
        if not key:return jsonify(error="AI mood analysis is not configured. Add EMERGENT_API_KEY on the server, or choose a mood manually."),503
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            import asyncio
            async def ask():
                chat=LlmChat(api_key=key,session_id="moodtunes-text",system_message="Analyze text for a non-clinical likely mood. Return JSON only with mood from this list: Happy, Sad, Stressed, Relaxed, Angry, Lonely, Motivated, Romantic, Sleepy, Energetic, Focused, Anxious, Excited, Bored, Peaceful, Nostalgic; explanation (one short sentence); uncertain boolean. Never diagnose.").with_model("gemini", "gemini-2.0-flash")
                return await chat.send_message(UserMessage(text=text))
            raw=asyncio.run(ask()); result=json.loads(raw); result["source"]="ai-text"; return jsonify(result)
        except Exception as exc:
            app.logger.warning("Text mood service failed (%s)",type(exc).__name__); return jsonify(error="The AI mood service is unavailable right now. Choose a mood manually."),502

    @app.post("/api/ai/face")
    @profile_required
    def ai_face():
        key=os.getenv("EMERGENT_API_KEY"); image_data=(request.get_json() or {}).get("image","")
        if not key:return jsonify(error="Facial analysis is not configured. Add EMERGENT_API_KEY on the server, or choose a mood manually."),503
        try:
            import cv2, numpy as np
            data=base64.b64decode(image_data.split(",",1)[-1],validate=True); arr=np.frombuffer(data,dtype=np.uint8); frame=cv2.imdecode(arr,cv2.IMREAD_COLOR)
            if frame is None:return jsonify(error="Could not read the camera frame."),400
            cascade=cv2.CascadeClassifier(cv2.data.haarcascades+"haarcascade_frontalface_default.xml"); faces=cascade.detectMultiScale(cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY),1.1,5)
            if len(faces)==0:return jsonify(error="No face was detected. Try again with your face in view, or choose a mood manually."),422
            ok,encoded=cv2.imencode(".jpg",frame)
            if not ok:return jsonify(error="Could not prepare the camera frame."),400
            # Image bytes exist only in this request's memory and are never persisted.
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            import asyncio
            async def ask():
                chat=LlmChat(api_key=key,session_id="moodtunes-face",system_message="Estimate only the visible facial expression, never infer actual feelings. Return JSON only: expression one of Happy, Sad, Angry, Surprised, Neutral, Fearful, or Uncertain; explanation; confidence only if you can support it, otherwise null. Be cautious.").with_model("gemini", "gemini-2.0-flash")
                from emergentintegrations.llm.chat import ImageContent
                return await chat.send_message(UserMessage(text="Estimate visible expression only.",file_contents=[ImageContent(base64.b64encode(encoded).decode())]))
            result=json.loads(asyncio.run(ask())); result["source"]="ai-face"; return jsonify(result)
        except Exception as exc:
            app.logger.warning("Face analysis failed (%s)",type(exc).__name__); return jsonify(error="Facial analysis is unavailable. Choose a mood manually."),502

    @app.get("/api/spotify/connect")
    @profile_required
    def spotify_connect():
        cid=os.getenv("SPOTIFY_CLIENT_ID"); redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI")
        if not cid or not redirect_uri:return jsonify(error="Configure Spotify client ID and deployed redirect URI first."),503
        state=secrets.token_urlsafe(24); session["spotify_state"]=state; scope="user-read-private user-read-playback-state user-modify-playback-state streaming"
        from urllib.parse import urlencode
        return redirect("https://accounts.spotify.com/authorize?"+urlencode({"client_id":cid,"response_type":"code","redirect_uri":redirect_uri,"scope":scope,"state":state}))

    @app.get("/spotify/callback")
    def spotify_callback():
        if request.args.get("state")!=session.get("spotify_state"):return "Spotify sign-in state mismatch",400
        cid=os.getenv("SPOTIFY_CLIENT_ID"); secret=os.getenv("SPOTIFY_CLIENT_SECRET"); uri=os.getenv("SPOTIFY_REDIRECT_URI")
        if not all([cid,secret,uri,request.args.get("code")]):return "Spotify credentials are incomplete",400
        try:
            r=requests.post("https://accounts.spotify.com/api/token",data={"grant_type":"authorization_code","code":request.args["code"],"redirect_uri":uri},auth=(cid,secret),timeout=15); r.raise_for_status(); token=r.json(); p=Profile.query.filter_by(id=session.get("profile_id"),user_id=session.get("user_id")).first()
            if not p:return redirect("/?spotify=error")
            c=SpotifyConnection.query.filter_by(profile_id=p.id).first() or SpotifyConnection(profile_id=p.id,access_token="",refresh_token="",expires_at=0); c.access_token=token["access_token"]; c.refresh_token=token.get("refresh_token",c.refresh_token); c.expires_at=int(datetime.utcnow().timestamp())+token.get("expires_in",3600); db.session.add(c); db.session.commit(); return redirect("/?spotify=connected")
        except Exception:return redirect("/?spotify=error")

    @app.get("/api/spotify/status")
    @profile_required
    def spotify_status():return jsonify(connected=SpotifyConnection.query.filter_by(profile_id=request.profile.id).first() is not None)

    @app.get("/api/config")
    def config():
        session.setdefault("csrf_token", secrets.token_urlsafe(32))
        return jsonify(moods=MOODS,languages=LANGUAGES,themes=THEMES,csrf=session["csrf_token"],ai_configured=bool(os.getenv("EMERGENT_API_KEY")),spotify_configured=bool(os.getenv("SPOTIFY_CLIENT_ID") and os.getenv("SPOTIFY_CLIENT_SECRET")))

    @app.errorhandler(413)
    def too_large(_):return jsonify(error="Request is too large."),413
    return app

app=make_app()
if __name__=="__main__":app.run(host="0.0.0.0",port=int(os.getenv("PORT",5000)),debug=False)
