from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()

# I copied this over from Moritz's commit to the backend, unsure if it works or if its necessary.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"],  # Backend URL
    allow_credentials=True,
    allow_methods=["*"],  # Alle HTTP-Methoden erlauben
    allow_headers=["*"],  # Alle Headers erlauben
)

@app.get("/")
def read_root():
    return {"Hello": "World"}
