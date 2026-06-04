from functools import lru_cache
from fastembed.rerank.cross_encoder import TextCrossEncoder

class Reranker:
  """
  Cross-encoder reranker wrapper using FastEmbed's TextCrossEncoder (ONNX).
  Scores (query, chunk) pairs jointly to improve retrieval precision.
  """

  MODEL_NAME = "Xenova/ms-marco-MiniLM-L-6-v2"

  def __init__(self):
    print(f"Loading Reranker model : {self.MODEL_NAME}")

    self.model = TextCrossEncoder(model_name=self.MODEL_NAME)

  def score(self, query: str, texts: list[str]) -> list[float]:
    if not texts:
      return []
    
    # TextCrossEncoder.rerank(query, documents) returns a generator of scores
    scores = self.model.rerank(query, texts)
    return [float(s) for s in scores]
  
@lru_cache
def get_reranker() -> Reranker:
  return Reranker()