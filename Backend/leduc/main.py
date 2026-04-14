from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import os
app = FastAPI()

app = FastAPI(title="GetOut API", version="0.1.0")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SetCardRequest(BaseModel):
    player: str
    cardID: str

@app.middleware("http")
async def private_network_access(request, call_next):
    response = await call_next(request)
    if request.headers.get("Access-Control-Request-Private-Network"):
        response.headers["Access-Control-Allow-Private-Network"] = "true"
    return response



@app.get("/")
def main():
    return {"message": "Hello World"}

@app.post("/SetCard")
def GetCard(request: SetCardRequest):
    print(request.player + request.cardID)
    return {"message":"worked"}