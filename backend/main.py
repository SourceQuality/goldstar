from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel
from onelogin.saml2.auth import OneLogin_Saml2_Auth
import uvicorn
import uuid
import asyncio

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = {
    "users": {},
    "stars": [],
    "sessions": {}
}

def prepare_request(request: Request, body: bytes):
    url = request.url
    return {
        "https": "on" if url.scheme == "https" else "off",
        "http_host": url.hostname,
        "server_port": str(url.port or (443 if url.scheme == "https" else 80)),
        "script_name": request.scope.get("root_path", ""),
        "get_data": request.query_params,
        "post_data": body,
    }

@app.get("/api/auth/login")
async def saml_login(request: Request):
    auth = OneLogin_Saml2_Auth(prepare_request(request, b""), custom_base_path="backend/saml")
    redirect_url = auth.login()
    return RedirectResponse(redirect_url)

@app.post("/api/auth/acs")
async def saml_acs(request: Request):
    body = await request.body()
    auth = OneLogin_Saml2_Auth(prepare_request(request, body), custom_base_path="backend/saml")
    auth.process_response()
    if not auth.is_authenticated():
        raise HTTPException(status_code=401, detail="SAML authentication failed")
    email = auth.get_nameid()
    user = db["users"].setdefault(email, {"id": email, "name": email.split("@")[0]})
    token = str(uuid.uuid4())
    db["sessions"][token] = user["id"]
    html = f"<script>localStorage.setItem('token','{token}');window.location='/'</script>"
    return HTMLResponse(content=html)

@app.get("/api/auth/me")
def get_me(request: Request):
    token = request.headers.get("Authorization")
    if not token or not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = token.split(" ", 1)[1]
    user_id = db["sessions"].get(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return db["users"][user_id]

@app.get("/api/users")
def get_users():
    return list(db["users"].values())

class Star(BaseModel):
    from_: str
    to: str

@app.post("/api/stars")
def give_star(star: Star):
    db["stars"].append(star.dict())
    return {"success": True}

@app.get("/api/stars")
def get_stars():
    return db["stars"]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)