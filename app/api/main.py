import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import channels, health, search
from app.config import get_settings
from app.core.rag import RAGPipeline
from app.core.retriever import HybridRetriever
from app.db.sqlite import create_tables
from app.ingestion.pipeline import IngestionPipeline
from app.ingestion.scheduler import create_scheduler

@asynccontextmanager
async def lifespan(app : FastAPI):
  print("Starting Youtube RAG Engine...")

  create_tables()

  retriever = HybridRetriever()
  retriever.load_or_build_bm25()

  from app.core.reranker import get_reranker
  get_reranker()

  rag_pipeline = RAGPipeline(retriever=retriever)

  # Store on app.state — accessible in all route handlers via req.app.state
  # This is the FastAPI-idiomatic way to share resources across requests
  # without global variables
  app.state.retriever = retriever
  app.state.rag_pipeline = rag_pipeline

  #start background scheduler
  pipeline = IngestionPipeline()
  scheduler = create_scheduler(pipeline)
  scheduler.start()
  app.state.scheduler = scheduler


  settings = get_settings()
  print(f"LLM: {settings.active_llm_model} (fallback: {settings.fallback_llm_model})")
  print("Ready.")

  yield

  print("Shutting down...")
  app.state.scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
  settings = get_settings()

  app = FastAPI(
    title="YouTube RAG Engine",
    description="Search and ask questions across YouTube channel transcripts",
    version="1.0.0",
    lifespan=lifespan,
  )

  # CORS — allow all origins in development
  # In production: replace "*" with your frontend domain
  app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
  )

  app.include_router(health.router, tags=["health"])
  app.include_router(channels.router, tags=["channels"])
  app.include_router(search.router, tags=["search"])

  # Serve React + Vite compiled SPA frontend if it exists
  if os.path.exists("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")

  return app


app = create_app()
