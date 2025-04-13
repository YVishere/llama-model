from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import pp

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the AI Assistant API!"}


@app.get("/search")
def search(query: str):
    response = pp.main_api(query)
    return response

if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
