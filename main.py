import os
import time
import requests
import streamlit as st

# Use environment variable for API URL in deployment
API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
  page_title="YouTube RAG Engine",
  page_icon="▶",
  layout="wide",
  initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  /* Base typography and theme */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
  
  html, body, [class*="css"] {
      font-family: 'Inter', sans-serif;
  }

  /* Main background */
  .stApp { background-color: #09090b; }

  /* Sidebar */
  [data-testid="stSidebar"] { 
      background-color: #09090b; 
      border-right: 1px solid #18181b; 
  }

  /* Cards */
  .rag-card {
      background: #09090b;
      border: 1px solid #27272a;
      border-radius: 8px;
      padding: 1.2rem 1.4rem;
      margin-bottom: 12px;
      transition: border-color 0.2s ease;
  }
  .rag-card:hover {
      border-color: #3f3f46;
  }

  /* Answer box */
  .answer-box {
      background: #09090b;
      border: 1px solid #27272a;
      border-radius: 8px;
      padding: 1.4rem;
      margin: 12px 0;
      font-size: 15px;
      line-height: 1.7;
      color: #fafafa;
  }

  /* Source chip */
  .source-chip {
      display: inline-block;
      background: #18181b;
      border: 1px solid #27272a;
      border-radius: 6px;
      padding: 4px 10px;
      font-size: 12px;
      color: #a1a1aa;
      margin: 3px 4px 3px 0;
  }

  /* Score badge */
  .score-badge {
      background: #18181b;
      border: 1px solid #27272a;
      border-radius: 6px;
      padding: 2px 8px;
      font-size: 11px;
      color: #a1a1aa;
      font-family: monospace;
  }

  /* Chunk text */
  .chunk-text {
      background: #09090b;
      border-left: 2px solid #3f3f46;
      padding: 10px 14px;
      font-size: 13px;
      color: #a1a1aa;
      line-height: 1.6;
      margin-top: 8px;
  }

  /* Metric pill */
  .metric-pill {
      background: #09090b;
      border: 1px solid #27272a;
      border-radius: 6px;
      padding: 6px 16px;
      font-size: 13px;
      color: #a1a1aa;
      text-align: center;
  }

  /* Status dot */
  .dot-green { color: #a1a1aa; }
  .dot-red   { color: #ef4444; }

  /* Hide streamlit branding */
  #MainMenu, footer { visibility: hidden; }

  /* Button styling */
  .stButton button {
      background: #ffffff !important;
      border: 1px solid #ffffff !important;
      color: #000000 !important;
      border-radius: 6px !important;
      font-weight: 500 !important;
      transition: all 0.2s ease;
  }
  .stButton button:hover {
      background: #e4e4e7 !important;
      border-color: #e4e4e7 !important;
      color: #000000 !important;
  }
  
  /* Inputs */
  .stTextInput input, .stTextArea textarea, .stSelectbox > div > div {
      background: #09090b !important;
      border: 1px solid #27272a !important;
      color: #fafafa !important;
      border-radius: 6px !important;
  }
  .stTextInput input:focus, .stTextArea textarea:focus, .stSelectbox > div > div:focus {
      border-color: #52525b !important;
      box-shadow: none !important;
  }
</style>
""", unsafe_allow_html=True)


# ── API helpers ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)  # cache health check for 30 seconds
def get_health() -> dict | None:
  try:
      r = requests.get(f"{API_URL}/health", timeout=5)
      return r.json() if r.status_code == 200 else None
  except Exception:
      return None


@st.cache_data(ttl=30)
def get_channels() -> list:
  try:
      r = requests.get(f"{API_URL}/channels", timeout=5)
      return r.json() if r.status_code == 200 else []
  except Exception:
      return []

def get_channel_videos(youtube_id: str) -> list:
    try:
        r = requests.get(
            f"{API_URL}/channels/{youtube_id}/videos",
            timeout=5
        )
        return r.json() if r.status_code == 200 else []
    except Exception:
        return []


def ask_question(question: str, channel_name: str | None, top_k: int) -> dict | None:
  try:
      payload = {"question": question, "top_k": top_k}
      if channel_name and channel_name != "All channels":
          payload["channel_name"] = channel_name
      r = requests.post(f"{API_URL}/ask", json=payload, timeout=60)
      return r.json() if r.status_code == 200 else {"error": r.text}
  except Exception as e:
      return {"error": str(e)}


def search_chunks(query: str, channel_name: str | None, top_k: int) -> dict | None:
  try:
      payload = {"query": query, "top_k": top_k}
      if channel_name and channel_name != "All channels":
          payload["channel_name"] = channel_name
      r = requests.post(f"{API_URL}/search", json=payload, timeout=30)
      return r.json() if r.status_code == 200 else {"error": r.text}
  except Exception as e:
      return {"error": str(e)}


def add_channel(channel_input: str, max_videos: int) -> dict | None:
  try:
      r = requests.post(
          f"{API_URL}/channels",
          json={"channel_input": channel_input, "max_videos": max_videos},
          timeout=300,  # ingestion takes time
      )
      return r.json()
  except Exception as e:
      return {"error": str(e)}


def ingest_single_video(video_id: str) -> bool:
  try:
      r = requests.post(f"{API_URL}/videos/{video_id}/ingest", timeout=300)
      return r.status_code == 200
  except Exception:
      return False


def delete_channel(youtube_id: str) -> bool:
  """Calls DELETE /channels/{youtube_id}. Returns True on success."""
  try:
      r = requests.delete(f"{API_URL}/channels/{youtube_id}", timeout=30)
      return r.status_code == 204
  except Exception:
      return False


# ── Page Functions ────────────────────────────────────────────────────────────

def ask_page():
  st.markdown("## 💬 Ask a question")
  st.markdown(
      "Ask anything — the answer is grounded in real video transcripts, "
      "not LLM memory."
  )

  # Example questions
  st.markdown("**Try these:**")
  example_cols = st.columns(3)
  examples = [
      "How was the Earth formed?",
      "What is the difference between crust and mantle?",
      "How do scientists study Earth's interior?",
  ]
  for i, ex in enumerate(examples):
      if example_cols[i].button(ex, key=f"ex_{i}"):
          st.session_state["ask_input"] = ex

  question = st.text_area(
      "Your question",
      value=st.session_state.get("ask_input", ""),
      placeholder="e.g. How was the Earth formed?",
      height=80,
      label_visibility="collapsed",
  )

  ask_clicked = st.button("Ask ↗", type="primary", use_container_width=False)

  if ask_clicked and question.strip():
      with st.spinner("Retrieving and generating answer..."):
          result = ask_question(
              question=question.strip(),
              channel_name=st.session_state.get("selected_channel", "All channels"),
              top_k=st.session_state.get("top_k", 5),
          )

      if not result or "error" in result:
          st.error(f"Error: {result.get('error', 'Unknown error')}")
      else:
          # Answer
          st.markdown(
              f'<div class="answer-box">{result["answer"]}</div>',
              unsafe_allow_html=True,
          )

          # Metadata row
          meta_col1, meta_col2, meta_col3 = st.columns(3)
          meta_col1.markdown(
              f'<div class="metric-pill">📄 {result["chunks_used"]} chunks used</div>',
              unsafe_allow_html=True,
          )
          meta_col2.markdown(
              f'<div class="metric-pill">🤖 {result["provider"].split("/")[-1]}</div>',
              unsafe_allow_html=True,
          )
          meta_col3.markdown(
              f'<div class="metric-pill">📺 {len(result["sources"])} source(s)</div>',
              unsafe_allow_html=True,
          )

          # Sources
          if result["sources"]:
              st.markdown("#### Sources")
              for source in result["sources"]:
                  start_sec = source.get("start_second", 0)
                  mins = start_sec // 60
                  secs = start_sec % 60
                  time_str = f"{mins}:{secs:02d}"
                  
                  yt_url = f"https://youtube.com/watch?v={source['video_youtube_id']}&t={start_sec}s"
                  st.markdown(
                      f'<div class="rag-card">'
                      f'<a href="{yt_url}" target="_blank" style="color:#fafafa;text-decoration:none;font-weight:500;">'
                      f'▶ {source["video_title"]}</a>'
                      f'<br><span style="color:#a1a1aa;font-size:12px">'
                      f'{source["channel_name"]} at {time_str}</span>'
                      f'&nbsp;&nbsp;<span class="score-badge">RRF {source["rrf_score"]:.4f}</span>'
                      f'</div>',
                      unsafe_allow_html=True,
                  )

  elif ask_clicked:
      st.warning("Please enter a question.")


def channels_page():
  st.markdown("## 📺 Channels")
  channels = get_channels()

  # Add channel form
  with st.expander("➕ Add channel or video", expanded=not channels):
      st.markdown(
          "Paste a YouTube channel handle, URL, or a direct **video URL**. "
          "Transcripts will be extracted and indexed automatically."
      )

      col1, col2 = st.columns([3, 1])
      new_channel = col1.text_input(
          "Channel or Video URL",
          placeholder="@3blue1brown or https://youtube.com/watch?v=...",
          label_visibility="collapsed",
      )
      max_vids = col2.number_input(
          "Max videos",
          min_value=0,
          max_value=200,
          value=10,
          help="Set to 0 to fetch ALL videos from the channel.",
          label_visibility="collapsed",
      )

      # Warning for large ingestions
      if max_vids > 50:
          st.warning(
              f"Ingesting {max_vids} videos will take ~{max_vids * 30 // 60} minutes. "
              "Start with 10-20 to test."
          )

      ingest_clicked = st.button("Add channel & ingest ↗", type="primary")

      if ingest_clicked and new_channel.strip():
          progress = st.progress(0, text="Resolving channel...")
          with st.spinner(f"Ingesting {new_channel} — this takes 30-60s per video..."):
              progress.progress(20, text="Fetching video list...")
              result = add_channel(new_channel.strip(), max_vids)
              progress.progress(100, text="Done!")

          if not result or "error" in result:
              st.error(f"Failed: {result.get('error', 'Unknown')}")
          else:
              st.success(
                  f"✓ {result['channel_name']} added — "
                  f"{result['videos_ingested']} videos ingested, "
                  f"{result['videos_failed']} failed"
              )
              # Clear cache so sidebar updates
              get_health.clear()
              get_channels.clear()
              st.rerun()

      elif ingest_clicked:
          st.warning("Please enter a channel handle or URL.")

  # Existing channels
  st.markdown("### Indexed channels")

  if not channels:
      st.info("No channels yet. Add one above.")
  else:
      for ch in channels:
          videos = get_channel_videos(ch["youtube_id"])
          ingested = [v for v in videos if v["ingested"]]
          pending  = [v for v in videos if not v["ingested"]]

          # ── Channel card header ─────────────────────────────────
          card_col, del_col = st.columns([10, 1])

          with card_col:
              st.markdown(
                  f'<div class="rag-card">'
                  f'<span style="font-weight:500;color:#fafafa;font-size:15px">'
                  f'📺 {ch["name"]}</span>'
                  f'&nbsp;&nbsp;<span style="color:#a1a1aa;font-size:12px">'
                  f'{ch["url"]}</span><br><br>'
                  f'<span style="background:#18181b;border:1px solid #27272a;'
                  f'border-radius:6px;padding:2px 8px;font-size:11px;'
                  f'color:#a1a1aa;font-family:monospace">'
                  f'✓ {len(ingested)} indexed</span>&nbsp;'
                  f'<span style="background:#18181b;border:1px solid #27272a;'
                  f'border-radius:6px;padding:2px 8px;font-size:11px;'
                  f'color:#a1a1aa;font-family:monospace">'
                  f'⏳ {len(pending)} pending</span>&nbsp;'
                  f'<span style="color:#71717a;font-size:12px">'
                  f'Last checked: '
                  f'{ch["last_checked_at"][:10] if ch["last_checked_at"] else "never"}'
                  f'</span></div>',
                  unsafe_allow_html=True,
              )

          with del_col:
              confirm_key = f"confirm_del_{ch['youtube_id']}"
              if st.session_state.get(confirm_key):
                  # Second click — actually delete
                  if st.button("✓ confirm", key=f"do_del_{ch['youtube_id']}",
                               help="Click to confirm deletion"):
                      with st.spinner(f"Removing {ch['name']}..."):
                          ok = delete_channel(ch["youtube_id"])
                      if ok:
                          st.session_state.pop(confirm_key, None)
                          get_health.clear()
                          get_channels.clear()
                          st.rerun()
                      else:
                          st.error("Delete failed")
              else:
                  if st.button("🗑", key=f"del_{ch['youtube_id']}",
                               help="Remove this channel"):
                      st.session_state[confirm_key] = True
                      st.rerun()

          if videos:
              with st.expander(
                  f"See all {len(videos)} videos", expanded=False
              ):
                  filter_text = st.text_input(
                      "Filter",
                      placeholder="type to filter...",
                      key=f"filter_{ch['youtube_id']}",
                      label_visibility="collapsed",
                  )
                  status_filter = st.radio(
                      "Status",
                      ["All", "Indexed only", "Pending only"],
                      horizontal=True,
                      key=f"status_{ch['youtube_id']}",
                  )

                  filtered = videos
                  if filter_text:
                      filtered = [
                          v for v in filtered
                          if filter_text.lower() in v["title"].lower()
                      ]
                  if status_filter == "Indexed only":
                      filtered = [v for v in filtered if v["ingested"]]
                  elif status_filter == "Pending only":
                      filtered = [v for v in filtered if not v["ingested"]]

                  st.caption(f"{len(filtered)} of {len(videos)} videos")

                  for v in filtered:
                      yt_url = (
                          f"https://youtube.com/watch?v={v['youtube_id']}"
                      )
                      icon  = "✓" if v["ingested"] else "⏳"
                      color = "#a1a1aa" if v["ingested"] else "#fbbf24"

                      mins = v.get("duration_seconds", 0) // 60
                      secs = v.get("duration_seconds", 0) % 60
                      dur  = f"{mins}:{secs:02d}" if mins else ""

                      vc = v.get("view_count", 0) or 0
                      views = (
                          f"{vc/1_000_000:.1f}M" if vc >= 1_000_000
                          else f"{vc/1_000:.0f}K" if vc >= 1_000
                          else ""
                      )

                      col_icon, col_title, col_dur, col_views, col_btn = st.columns([0.5, 8, 1, 1, 2.5])
                      with col_icon:
                          st.markdown(f'<span style="color:{color};font-size:14px">{icon}</span>', unsafe_allow_html=True)
                      with col_title:
                          st.markdown(f'<a href="{yt_url}" target="_blank" style="color:#e4e4e7;text-decoration:none;font-size:13px;display:block;overflow:hidden;white-space:nowrap;text-overflow:ellipsis">{v["title"]}</a>', unsafe_allow_html=True)
                      with col_dur:
                          st.markdown(f'<span style="color:#52525b;font-size:12px;white-space:nowrap">{dur}</span>', unsafe_allow_html=True)
                      with col_views:
                          st.markdown(f'<span style="color:#52525b;font-size:12px;white-space:nowrap">{views}</span>', unsafe_allow_html=True)
                      with col_btn:
                          if not v["ingested"]:
                              if st.button("Index ↗", key=f"ingest_{v['youtube_id']}", 
                                           help="Index this video now"):
                                  with st.spinner(f"Indexing {v['title']}..."):
                                      if ingest_single_video(v["youtube_id"]):
                                          st.success(f"Indexed {v['title']}")
                                          get_health.clear()
                                          st.rerun()
                                      else:
                                          st.error("Indexing failed")


# ── Navigation Setup ──────────────────────────────────────────────────────────

pg = st.navigation([
  st.Page(ask_page, title="Ask", icon="💬"),
  st.Page(channels_page, title="Channels", icon="📺"),
])


# ── Sidebar (Shared) ──────────────────────────────────────────────────────────

with st.sidebar:
  st.markdown("## ▶ YouTube RAG Engine")
  st.markdown("---")

  # API health
  health = get_health()
  if health:
      st.markdown(
          f'<span class="dot-green">●</span> API connected',
          unsafe_allow_html=True
      )
      col1, col2 = st.columns(2)
      col1.metric("Chunks", health.get("chunks_indexed", 0))
      col2.metric("Channels", health.get("channels_tracked", 0))
      st.caption(f"LLM: `{health.get('active_llm', '—')}`")
  else:
      st.markdown(
          f'<span class="dot-red">●</span> API offline — start with `uvicorn app.api.main:app`',
          unsafe_allow_html=True
      )

  st.markdown("---")

  # Channel filter (shared across Ask and Search)
  channels = get_channels()
  channel_names = ["All channels"] + [ch["name"] for ch in channels]
  st.selectbox("Filter by channel", channel_names, key="selected_channel")
  st.slider("Results (top-k)", min_value=1, max_value=10, value=5, key="top_k")


# ── Run Navigation ────────────────────────────────────────────────────────────

pg.run()