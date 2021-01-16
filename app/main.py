from fastapi import FastAPI, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import *
from typing import List

from os import getenv
from data import load_users, load_parties, load_coalitions

app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["*"])

users = load_users()
parties = load_parties()
coalitions = load_coalitions()


@app.get("/user")
async def get_all_users() -> List[User]:
    return users


@app.get("/user/{username}")
async def get_user(username: str) -> User:
    user = next((user for user in users if user.username == username), None)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='User not found')
    else:
        return user


@app.get("/party")
async def get_all_parties() -> List[Party]:
    return parties


@app.get("/party/{party_id}")
async def get_user(party_id: int) -> Party:
    party = next((party for party in parties if party.party_id == party_id), None)

    if party is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Party not found')
    else:
        return party


@app.get("/coalition")
async def get_all_users() -> List[Coalition]:
    return coalitions


@app.get("/coalition/{coalition_id}")
async def get_user(coalition_id: int) -> Coalition:
    coalition = next((coalition for coalition in coalitions if coalition.coalition_id == coalition_id), None)

    if coalition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Coalition not found')
    else:
        return coalition
