from functools import lru_cache
from sentence_transformers import CrossEncoder

class Reranker:
  """
  Cross-encoder reranker wrapper using sentence-transformers.
  Scores (query, chunk) pairs jointly to improve retrieval precision.
  """

  MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

  def __init__(self):
    print(f"Loading Reranker model : {self.MODEL_NAME}")

    self.model = CrossEncoder(self.MODEL_NAME)

  def score(self, query: str, texts: list[str]) -> list[float]:
    if not texts:
      return []
    
    pairs = [[query, text] for text in texts]
    scores = self.model.predict(pairs)

    return [float(s) for s in scores]
  
@lru_cache
def get_reranker() -> Reranker:
  return Reranker()