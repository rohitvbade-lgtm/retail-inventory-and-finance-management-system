from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from .database import engine, Base
from .seed_data import seed_database
from .routers import inventory, finance, discounts, ai_chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup database tables and seed
    Base.metadata.create_all(bind=engine)
    seed_database()
    yield


app = FastAPI(
    title="Inventory & Finance Management POS with AI Discount Machine",
    version="1.0.0",
    description="Full-stack retail system featuring real-time inventory alerts, counter invoicing, and an AI-driven deterministic discount engine.",
    lifespan=lifespan
)

# Enable CORS for Angular frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(inventory.router)
app.include_router(finance.router)
app.include_router(discounts.router)
app.include_router(ai_chat.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "pos-backend"}

