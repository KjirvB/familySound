import os
from uuid import uuid4
from fastapi import FastAPI, Request, Form, Depends, UploadFile, File, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from . import models, database, auth

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

templates = Jinja2Templates(directory="templates")

REGISTER_KEY = os.environ.get("REGISTER_KEY", "letmein")
JURY_NAME = os.environ.get("JURY_USER", "jury")
JURY_PASS = os.environ.get("JURY_PASS", "jurypass")


@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    response = await call_next(request)
    return response


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(auth.get_db)):
    team = auth.get_current_team(request, db)
    if team:
        return RedirectResponse("/dashboard", status_code=302)
    token = request.cookies.get("access_token")
    if token:
        try:
            payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
            if payload.get("sub") == "jury":
                return RedirectResponse("/jury", status_code=302)
        except auth.JWTError:
            pass
    return templates.TemplateResponse(
        "home.html",
        {"request": request, "title": "Home", "is_jury": auth.is_jury(request)},
    )


@app.get("/register", response_class=HTMLResponse)
async def get_register(request: Request):
    return templates.TemplateResponse(
        "register.html",
        {"request": request, "title": "Register", "is_jury": auth.is_jury(request)},
    )


@app.post("/register")
async def post_register(request: Request, name: str = Form(...), password: str = Form(...), reg_key: str = Form(...), db: Session = Depends(auth.get_db)):
    if reg_key != REGISTER_KEY:
        raise HTTPException(status_code=400, detail="Invalid registration key")
    if db.query(models.Team).filter_by(name=name).first():
        raise HTTPException(status_code=400, detail="Team already exists")
    team = models.Team(name=name, pass_hash=auth.get_password_hash(password))
    db.add(team)
    db.commit()
    return RedirectResponse("/login", status_code=302)


@app.get("/login", response_class=HTMLResponse)
async def get_login(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "title": "Login", "is_jury": auth.is_jury(request)},
    )


@app.post("/login")
async def post_login(request: Request, name: str = Form(...), password: str = Form(...), db: Session = Depends(auth.get_db)):
    if name == JURY_NAME and password == JURY_PASS:
        token = auth.create_access_token({"sub": "jury"})
        response = RedirectResponse("/jury", status_code=302)
        response.set_cookie("access_token", token, httponly=True)
        return response
    team = db.query(models.Team).filter_by(name=name).first()
    if not team or not auth.verify_password(password, team.pass_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    token = auth.create_access_token({"sub": str(team.id)})
    response = RedirectResponse("/dashboard", status_code=302)
    response.set_cookie("access_token", token, httponly=True)
    return response


@app.get("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie("access_token")
    return response


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(auth.get_db)):
    team = auth.get_current_team(request, db)
    if not team:
        return RedirectResponse("/login", status_code=302)
    originals = db.query(models.Original).filter_by(team_id=team.id).all()
    others = db.query(models.Original).filter(models.Original.team_id != team.id).all()
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "team": team,
            "originals": originals,
            "others": others,
            "title": "Dashboard",
            "is_jury": auth.is_jury(request),
        },
    )


@app.post("/originals")
async def upload_original(request: Request, file: UploadFile = File(...), note: str = Form(None), db: Session = Depends(auth.get_db)):
    team = auth.get_current_team(request, db)
    if not team:
        raise HTTPException(status_code=401, detail="Not authenticated")
    ext = os.path.splitext(file.filename)[1]
    uid = uuid4().hex
    dest = f"uploads/originals/{uid}{ext}"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as f:
        f.write(await file.read())
    orig = models.Original(team_id=team.id, filepath=dest, note=note)
    db.add(orig)
    db.commit()
    return RedirectResponse("/dashboard", status_code=302)


@app.post("/attempts/{original_id}")
async def upload_attempt(original_id: int, request: Request, file: UploadFile = File(...), db: Session = Depends(auth.get_db)):
    team = auth.get_current_team(request, db)
    if not team:
        raise HTTPException(status_code=401, detail="Not authenticated")
    ext = os.path.splitext(file.filename)[1]
    uid = uuid4().hex
    dest = f"uploads/attempts/{uid}{ext}"
    with open(dest, "wb") as f:
        f.write(await file.read())
    attempt = models.Attempt(team_id=team.id, original_id=original_id, filepath=dest)
    db.add(attempt)
    db.commit()
    return RedirectResponse("/dashboard", status_code=302)


@app.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard(request: Request, db: Session = Depends(auth.get_db)):
    teams = db.query(models.Team).all()
    leaderboard = []
    for t in teams:
        points = 0
        for orig in t.originals:
            judgments = [a.judgment for a in orig.attempts if a.judgment]
            if not judgments:
                points += 3
            else:
                matches = [j for j in judgments if j.verdict == 'match']
                if matches and len(matches) == len(judgments):
                    points += sum(1 for _ in matches)
                elif matches:
                    points += 0  # poster team gets none
                else:
                    pass
        for attempt in t.attempts:
            j = attempt.judgment
            if j and j.verdict == 'match':
                orig_attempts = attempt.original.attempts
                judgments = [a.judgment for a in orig_attempts if a.judgment]
                matches = [jj for jj in judgments if jj.verdict == 'match']
                if len(matches) == len(judgments):
                    points += 1
                else:
                    points += 2
        leaderboard.append({"team": t.name, "points": points})
    leaderboard.sort(key=lambda x: x["points"], reverse=True)
    return templates.TemplateResponse(
        "leaderboard.html",
        {
            "request": request,
            "leaderboard": leaderboard,
            "title": "Leaderboard",
            "is_jury": auth.is_jury(request),
        },
    )


@app.get("/jury", response_class=HTMLResponse)
async def jury_panel(request: Request, db: Session = Depends(auth.get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login", status_code=302)
    try:
        payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
    except auth.JWTError:
        return RedirectResponse("/login", status_code=302)
    if payload.get("sub") != "jury":
        return RedirectResponse("/dashboard", status_code=302)
    attempt = db.query(models.Attempt).filter(~models.Attempt.judgment.has()).first()
    return templates.TemplateResponse(
        "jury.html",
        {
            "request": request,
            "attempt": attempt,
            "title": "Jury",
            "is_jury": True,
        },
    )


@app.post("/jury/attempt/{attempt_id}")
async def judge_attempt(attempt_id: int, request: Request, verdict: str = Form(...), comment: str = Form(None), db: Session = Depends(auth.get_db)):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401)
    try:
        payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
    except auth.JWTError:
        raise HTTPException(status_code=401)
    if payload.get("sub") != "jury":
        raise HTTPException(status_code=401)
    attempt = db.query(models.Attempt).filter_by(id=attempt_id).first()
    if not attempt:
        raise HTTPException(status_code=404)
    judgment = models.Judgment(attempt_id=attempt.id, verdict=verdict, comment=comment, juror=JURY_NAME)
    db.add(judgment)
    db.commit()
    return RedirectResponse("/jury", status_code=302)


@app.get("/jury/password", response_class=HTMLResponse)
async def change_password_form(request: Request, db: Session = Depends(auth.get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse("/login", status_code=302)
    try:
        payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
    except auth.JWTError:
        return RedirectResponse("/login", status_code=302)
    if payload.get("sub") != "jury":
        return RedirectResponse("/dashboard", status_code=302)
    teams = db.query(models.Team).all()
    success = request.query_params.get("success") == "1"
    return templates.TemplateResponse(
        "change_password.html",
        {
            "request": request,
            "teams": teams,
            "title": "Change Team Password",
            "success": success,
            "is_jury": True,
        },
    )


@app.post("/jury/password")
async def change_password(request: Request, team_id: int = Form(...), password: str = Form(...), db: Session = Depends(auth.get_db)):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401)
    try:
        payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
    except auth.JWTError:
        raise HTTPException(status_code=401)
    if payload.get("sub") != "jury":
        raise HTTPException(status_code=401)
    team = db.query(models.Team).filter_by(id=team_id).first()
    if not team:
        raise HTTPException(status_code=404)
    team.pass_hash = auth.get_password_hash(password)
    db.commit()
    return RedirectResponse("/jury/password?success=1", status_code=302)

