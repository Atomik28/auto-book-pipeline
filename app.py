import os
import re
import sys
import subprocess

import streamlit as st
from dotenv import load_dotenv
import google.generativeai as genai
import chromadb

from versioning import save_to_chromadb, get_next_version

# ── Environment & LLM Setup ──────────────────────────────────────────────────

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# ── ChromaDB Client ─────────────────────────────────────────────────────────

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name="book_chapters")

# ── Helpers ─────────────────────────────────────────────────────────────────

def load_text(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    # Normalize line endings and split paragraphs
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    return [p.strip() for p in re.split(r'\n{2,}', text) if p.strip()]

def extract_doc_id(url):
    last = url.rstrip('/').split('/')[-1]
    return last.replace(' ', '_').replace('-', '_')

# ── Sidebar: Scrape & Initial AI Pipeline ───────────────────────────────────

st.sidebar.header("Step 1: Scrape & Generate Initial Versions")
url = st.sidebar.text_input(
    "Enter chapter URL",
    value="https://en.wikisource.org/wiki/The_Gates_of_Morning/Book_1/Chapter_1"
)
doc_id = extract_doc_id(url)

if st.sidebar.button("Run Scraper & AI Pipeline (First Time)"):
    # Clean old outputs
    for fname in [
        f"output/{doc_id}.txt",
        f"output/{doc_id}_spun.txt",
        f"output/{doc_id}_reviewed.txt",
        f"output/{doc_id}_screenshot.png",
    ]:
        try: os.remove(fname)
        except FileNotFoundError: pass

    # Execute pipeline scripts
    result1 = subprocess.run(
        [sys.executable, "scraper.py", url, doc_id],
        capture_output=True, text=True
    )
    result2 = subprocess.run(
        [sys.executable, "ai_writer.py", doc_id],
        capture_output=True, text=True
    )
    result3 = subprocess.run(
        [sys.executable, "ai_reviewer.py", doc_id],
        capture_output=True, text=True
    )

    st.sidebar.success("Scraping and initial AI pipeline complete!")
    st.sidebar.text_area("Scraper Output", result1.stdout + result1.stderr, height=100)
    st.sidebar.text_area("AI Writer Output", result2.stdout + result2.stderr, height=100)
    st.sidebar.text_area("AI Reviewer Output", result3.stdout + result3.stderr, height=100)

# ── Main UI: Human-in-the-Loop Review ────────────────────────────────────────

# Only show tabs if all three base files exist
paths = [
    f"output/{doc_id}.txt",
    f"output/{doc_id}_spun.txt",
    f"output/{doc_id}_reviewed.txt",
]
if all(os.path.exists(p) for p in paths):
    original = load_text(paths[0])
    spun     = load_text(paths[1])
    reviewed = load_text(paths[2])

    st.title("Human-in-the-Loop: Chapter Review & Approval")
    tab = st.radio("Select Chapter Version", ("Original", "Spun", "Reviewed"), horizontal=True)

    # ── Original Tab ─────────────────────────────────────────────────────────
    if tab == "Original":
        current = "\n\n".join(original)
        st.header("Original Chapter (View Only)")
        st.write(current)
        if st.button("Save to ChromaDB (OG)"):
            version = get_next_version(collection, doc_id)
            save_to_chromadb(doc_id, version, "og", current, is_final=False)
            st.success("Original version saved to ChromaDB.")

    # ── Spun Tab ─────────────────────────────────────────────────────────────
    elif tab == "Spun":
        current = "\n\n".join(spun)
        st.header("Spun Chapter (View Only)")
        st.write(current)
        if st.button("Save to ChromaDB (Spun)"):
            version = get_next_version(collection, doc_id)
            save_to_chromadb(doc_id, version, "spun", current, is_final=False)
            st.success("Spun version saved to ChromaDB.")

    # ── Reviewed Tab ─────────────────────────────────────────────────────────
    else:
        current = "\n\n".join(reviewed)
        st.header("Reviewed Chapter (Editable)")
        edited_text = st.text_area("Edit Reviewed Chapter", value=current, height=600)

        col1, col2, col3, col4 = st.columns(4)

        # — Save human edits —
        with col1:
            if st.button("Save Changes"):
                try:
                    with open(paths[2], "w", encoding="utf-8") as f:
                        f.write(edited_text)
                    version = get_next_version(collection, doc_id)
                    save_to_chromadb(doc_id, version, "human_edited", edited_text, is_final=False)
                    st.success("Saved human-edited version.")
                except Exception as e:
                    st.error(f"Error saving: {e}")

        # — Re-spin with AI Writer —
        with col2:
            if st.button("Re-spin (AI Writer)"):
                try:
                    model = genai.GenerativeModel('models/gemini-1.5-pro-latest')
                    prompt = (
                        "Rewrite this chapter to be more engaging, vivid, and modernized, "
                        "while keeping the original meaning intact. DO NOT summarize. Retain full details.\n\n"
                        + edited_text
                    )
                    response = model.generate_content(prompt)
                    new_text = response.text.strip()

                    # Overwrite spun file for Tab 2
                    with open(paths[1], "w", encoding="utf-8") as f:
                        f.write(new_text)

                    version = get_next_version(collection, doc_id)
                    save_to_chromadb(doc_id, version, "respun", new_text, is_final=False)

                    # Pass to Reviewed textarea
                    st.session_state['editor_text'] = new_text
                    st.info("Re-spun with AI Writer.")
                except Exception as e:
                    st.error(f"AI Writer error: {e}")

        # — Re-review with AI Reviewer —
        with col3:
            if st.button("Re-review (AI Reviewer)"):
                try:
                    model = genai.GenerativeModel('models/gemini-1.5-pro-latest')
                    prompt = (
                        "You are an AI reviewer. Review the following chapter for grammar, "

                        "coherence, readability, and consistency. Make small improvements where necessary "
                        "but retain the original structure and meaning.\n\n"
                        + edited_text
                    )
                    response = model.generate_content(prompt)
                    new_text = response.text.strip()

                    # Overwrite reviewed file so Tab stays in sync
                    with open(paths[2], "w", encoding="utf-8") as f:
                        f.write(new_text)

                    version = get_next_version(collection, doc_id)
                    save_to_chromadb(doc_id, version, "rereviewed", new_text, is_final=False)

                    st.session_state['editor_text'] = new_text
                    st.info("Re-reviewed with AI Reviewer.")
                except Exception as e:
                    st.error(f"AI Reviewer error: {e}")

        # — Approve & Finalize —
        with col4:
            if st.button("Approve & Save to ChromaDB"):
                try:
                    version = get_next_version(collection, doc_id)
                    save_to_chromadb(doc_id, version, "reviewed", edited_text, is_final=True)
                    st.success("Approved final version saved.")
                except Exception as e:
                    st.error(f"Failed to save: {e}")

        # Pull edited or AI-generated text into editor
        if 'editor_text' in st.session_state:
            edited_text = st.session_state.pop('editor_text')
# ── Step 2: RL-Like Retrieval of Final Version ───────────────────────────────
st.sidebar.header("Step 2: Retrieve Published Chapter")
query_id = st.sidebar.text_input("Enter doc_id to retrieve", value=doc_id)

if st.sidebar.button("Get Final Version"):
    # Fetch only final versions for this doc_id
    results = collection.get(
        where={"doc_id": query_id, "is_final": True},
        include=["ids", "documents", "metadatas"]
    )
    if not results["ids"]:
        st.sidebar.error(f"No final version found for `{query_id}`")
    else:
        # Pick the entry with the highest version number
        metas = results["metadatas"]
        docs  = results["documents"]
        best_idx = max(range(len(metas)), key=lambda i: metas[i]["version"])
        meta = metas[best_idx]
        final_doc = docs[best_idx]

        st.sidebar.success(f"Found final v{meta['version']} — {meta['timestamp']}")
        st.sidebar.write(final_doc)

else:
    st.info("Please run the scraper and AI pipeline from the sidebar to generate the initial files.")
