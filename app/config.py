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
    # Auto-reconstruct data.zip from split base64 text files if they exist
    import base64
    import zipfile
    
    parts = [Path("data_part1.txt"), Path("data_part2.txt"), Path("data_part3.txt")]
    if all(p.exists() for p in parts):
      if not self.sqlite_db_path.exists() or not self.chroma_db_path.exists():
        print("Reconstructing pre-indexed RAG database from text parts...")
        try:
          # Concatenate the base64 parts
          encoded_str = ""
          for p in parts:
            encoded_str += p.read_text(encoding="ascii")
          
          # Decode base64 bytes
          zip_data = base64.b64decode(encoded_str)
          
          # Write temporary data.zip
          temp_zip_path = Path("temp_data.zip")
          temp_zip_path.write_bytes(zip_data)
          
          # Extract zip
          with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
            zip_ref.extractall(".")
          print("RAG database reconstruction and extraction complete.")
          
          # Clean up temporary zip file
          if temp_zip_path.exists():
            temp_zip_path.unlink()
        except Exception as e:
          print(f"Error reconstructing RAG database: {e}")

    # Fallback to direct data.zip if present (for local testing flexibility)
    zip_path = Path("data.zip")
    if zip_path.exists():
      if not self.sqlite_db_path.exists() or not self.chroma_db_path.exists():
        print(f"Extracting pre-indexed RAG database from {zip_path}...")
        try:
          with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(".")
          print("RAG database extraction complete.")
        except Exception as e:
          print(f"Error extracting RAG database from {zip_path}: {e}")

    self.chroma_db_path.parent.mkdir(parents=True, exist_ok=True)
    self.sqlite_db_path.parent.mkdir(parents=True, exist_ok=True)
    self.bm25_index_path.parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
  settings = Settings()
  settings.ensure_data_dirs()
  return settings

