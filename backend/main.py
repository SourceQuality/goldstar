from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

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
    "stars": []
}

@app.get("/api/auth/me")
def get_me(request: Request):
    email = request.headers.get("x-user-email")
    if not email:
        raise HTTPException(status_code=401, detail="Missing SSO email header")
    user = db["users"].setdefault(email, {"id": email, "name": email.split("@")[0], "stars": 0})
    return user

@app.get("/api/users")
def get_users():
    return list(db["users"].values())

class Star(BaseModel):
    from_: str
    to: str

@app.post("/api/stars")
def give_star(star: Star):
    db["stars"].append(star.dict())
    if star.to in db["users"]:
        db["users"][star.to]["stars"] += 1
    return {"success": True}

@app.get("/api/stars")
def get_stars():
    return db["stars"]

@app.get("/api/user_stars")
def get_user_stars():
    return {uid: user["stars"] for uid, user in db["users"].items()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
