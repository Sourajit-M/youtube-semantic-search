import pytest
from app.core.retriever import BM25Index, reciprocal_rank_fusion
from app.db.vectordb import ChunkResult


@pytest.fixture
def bm25_index():
  index = BM25Index()
  texts = [
    "photosynthesis converts sunlight into glucose in plant cells",
    "chlorophyll absorbs red and blue light reflects green",
    "CRISPR cas9 is a gene editing tool derived from bacteria",
    "Jennifer Doudna won the Nobel Prize for CRISPR research",
    "the Calvin cycle fixes carbon dioxide into sugar molecules",
  ]
  ids = [f"chunk_{i}" for i in range(len(texts))]
  metadatas = [
    {
      "video_youtube_id": f"vid_{i}",
      "video_title": f"Video {i}",
      "channel_name": "Test",
      "chunk_index": i,
    }
    for i in range(len(texts))
  ]
  index.build(texts=texts, chunk_ids=ids, metadatas=metadatas)
  return index


def test_bm25_returns_results(bm25_index):
  results = bm25_index.search("photosynthesis", top_k=3)
  assert len(results) > 0


def test_bm25_exact_term_ranks_first(bm25_index):
  results = bm25_index.search("CRISPR Nobel Prize", top_k=5)
  top_ids = [r[0] for r in results[:2]]

  # chunks 2 and 3 contain CRISPR/Nobel terms
  assert "chunk_2" in top_ids or "chunk_3" in top_ids


def test_bm25_no_match_returns_empty(bm25_index):
  results = bm25_index.search("quantum mechanics black holes", top_k=3)

  # BM25 returns 0.0 scores for no term overlap — all filtered out
  assert len(results) == 0


def test_bm25_channel_filter(bm25_index):
  results = bm25_index.search(
    "photosynthesis",
    top_k=3,
    channel_name="NonExistent",
  )
  assert len(results) == 0


def test_rrf_fusion_boosts_dual_ranked():
  """A chunk in both lists should outscore one in only one list."""
  bm25_results = [
    (
      "chunk_A",
      10.0,
      "text A",
      {
        "video_youtube_id": "v1",
        "video_title": "V1",
        "channel_name": "C",
        "chunk_index": 0,
      },
    ),
    (
      "chunk_B",
      5.0,
      "text B",
      {
        "video_youtube_id": "v2",
        "video_title": "V2",
        "channel_name": "C",
        "chunk_index": 0,
      },
    ),
  ]

  vector_results = [
    ChunkResult(
      chunk_id="chunk_B",
      text="text B",
      video_youtube_id="v2",
      video_title="V2",
      channel_name="C",
      chunk_index=0,
      distance=0.1,
    ),
    ChunkResult(
      chunk_id="chunk_C",
      text="text C",
      video_youtube_id="v3",
      video_title="V3",
      channel_name="C",
      chunk_index=0,
      distance=0.2,
    ),
  ]

  fused = reciprocal_rank_fusion(
    bm25_results,
    vector_results,
    top_k=3,
  )

  # chunk_B appears in both lists — should rank highest
  assert fused[0]["chunk_id"] == "chunk_B"


def test_rrf_top_k_respected():
  bm25_results = [
    (
      f"chunk_{i}",
      float(10 - i),
      f"text {i}",
      {
        "video_youtube_id": f"v{i}",
        "video_title": f"V{i}",
        "channel_name": "C",
        "chunk_index": i,
      },
    )
    for i in range(5)
  ]

  fused = reciprocal_rank_fusion(
    bm25_results,
    [],
    top_k=3,
  )

  assert len(fused) <= 3


def test_bm25_index_clear_on_empty():
  """Verify that BM25Index clears the database virtual table on empty input."""
  index = BM25Index()
  
  # Build with actual text
  index.build(
    texts=["photosynthesis converts sunlight"],
    chunk_ids=["chunk_clear_1"],
    metadatas=[{"video_youtube_id": "v1", "video_title": "V1", "channel_name": "C", "chunk_index": 0}]
  )
  
  assert index.is_ready
  res = index.search("photosynthesis", 5)
  assert len(res) == 1
  
  # Clear it by building with empty lists
  index.build([], [], [])
  
  res = index.search("photosynthesis", 5)
  assert len(res) == 0


def test_timestamp_parsing_in_fts():
  """Verify that FTS search preserves and extracts start_second correctly."""
  index = BM25Index()
  index.build(
    texts=["this chunk starts later"],
    chunk_ids=["chunk_time_1"],
    metadatas=[{"video_youtube_id": "v_time", "video_title": "Time Video", "channel_name": "C", "chunk_index": 0, "start_second": 125}]
  )
  
  res = index.search("starts", 5)
  assert len(res) == 1
  assert res[0][3]["start_second"] == 125


def test_resolve_channel_id_robustness():
  """Test that resolve_channel_id handles various URL forms robustly (mocked)."""
  from unittest.mock import MagicMock, patch
  from app.ingestion.youtube_api import resolve_channel_id
  
  mock_youtube = MagicMock()
  mock_youtube.channels().list().execute.return_value = {
    "items": [{
      "id": "UC1234567890123456789012",
      "snippet": {"title": "Test Channel"}
    }]
  }
  
  with patch("app.ingestion.youtube_api.get_youtube_client", return_value=mock_youtube):
    # Test UC... direct ID
    cid, ctitle = resolve_channel_id("UC1234567890123456789012")
    assert cid == "UC1234567890123456789012"
    
    # Test channel/UC... path
    cid, ctitle = resolve_channel_id("https://youtube.com/channel/UC1234567890123456789012")
    assert cid == "UC1234567890123456789012"
    
    # Test channel/UC... path with videos suffix and trailing slash
    cid, ctitle = resolve_channel_id("https://www.youtube.com/channel/UC1234567890123456789012/videos/")
    assert cid == "UC1234567890123456789012"


def test_vectordb_search_clipping():
  """Verify that VectorDB.search clips top_k to total chunks count to prevent ValueError."""
  from unittest.mock import MagicMock, patch
  from app.db.vectordb import VectorDB
  
  mock_collection = MagicMock()
  mock_collection.count.return_value = 2
  mock_collection.query.return_value = {
    "ids": [["chunk_1", "chunk_2"]],
    "documents": [["text 1", "text 2"]],
    "metadatas": [[
      {"video_youtube_id": "v1", "video_title": "V1", "channel_name": "C", "chunk_index": 0},
      {"video_youtube_id": "v1", "video_title": "V1", "channel_name": "C", "chunk_index": 1}
    ]],
    "distances": [[0.1, 0.2]]
  }
  
  mock_client = MagicMock()
  mock_client.get_or_create_collection.return_value = mock_collection
  
  with patch("chromadb.PersistentClient", return_value=mock_client):
    vdb = VectorDB()
    # Query with top_k = 10, but count is only 2
    results = vdb.search(query_embedding=[0.1]*384, top_k=10)
    
    # Check that n_results passed to query was clipped to 2
    mock_collection.query.assert_called_once()
    kwargs = mock_collection.query.call_args[1]
    assert kwargs["n_results"] == 2
    assert len(results) == 2