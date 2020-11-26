from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from models import *

from os import getenv
from data import load_users, get_points

app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["*"])

users = load_users()


@app.get("/user")
async def get_users() -> [TwitterUser]:
    return users


@app.get("/point3d")
async def get_points_3d() -> [TwitterPoint3d]:
    return get_points(users)
