from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
  model_config = SettingsConfigDict(
    env_file = ".env",
    env_file_encoding = "utf-8",
    case_sensitive = False,
    extra = "ignore"
  )

  llm_provider: str = "groq"
  llm_fallback_provider: str = "gemini"

  groq_api_key: str = ""
  gemini_api_key: str = ""

  groq_model: str = "groq/llama-3.3-70b-versatile"
  gemini_model: str = "gemini/gemini-2.5-flash"

  youtube_api_key: str = ""

  youtube_cookies_path: str = ""
  youtube_cookies_browser: str = ""

  chunk_size: int = 300
  chunk_overlap: int = 50
  
  top_k_results: int = 5

  chroma_db_path: Path = Path("./data/vectordb")
  sqlite_db_path: Path = Path("./data/metadata.db")
  bm25_index_path: Path = Path("./data/bm25_index.pkl")
  
  ingest_interval_minutes: int = 60

  jwt_secret_key: str = "supersecret_default_key_change_me_in_production"
  jwt_algorithm: str = "HS256"
  access_token_expire_minutes: int = 60

  @property
  def active_llm_model(self) -> str:
    models = {
      "groq": self.groq_model,
      "gemini": self.gemini_model
    }

    return models.get(self.llm_provider, self.groq_model)


  @property
  def fallback_llm_model(self) -> str:
    models = {
      "groq": self.groq_model,
      "gemini": self.gemini_model,
    }
    return models.get(self.llm_fallback_provider, self.gemini_model)

  def ensure_data_dirs(self) -> None:
    self.chroma_db_path.parent.mkdir(parents=True, exist_ok=True)
    self.sqlite_db_path.parent.mkdir(parents=True, exist_ok=True)
    self.bm25_index_path.parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
  settings = Settings()
  settings.ensure_data_dirs()
  return settings

