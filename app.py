import os
import streamlit as st
from dotenv import load_dotenv
import google.generativeai as genai
import chromadb
import re
from versioning import save_to_chromadb
import subprocess
import sys

# Load env
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Configure ChromaDB client (local directory)
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection(name="book_chapters")

# File paths
def load_text(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    # Replace Windows/Mac line endings with \n
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Split on two or more newlines, and strip whitespace
    paragraphs = [p.strip() for p in re.split(r'\n{2,}', text) if p.strip()]
    return paragraphs

# Sidebar for scraping and initial AI pipeline
st.sidebar.header("Step 1: Scrape & Generate Initial Versions")
url = st.sidebar.text_input("Enter chapter URL", value="https://en.wikisource.org/wiki/The_Gates_of_Morning/Book_1/Chapter_1")
# Extract doc_id from URL (last part, normalized)
def extract_doc_id(url):
    last = url.rstrip('/').split('/')[-1]
    return last.replace(' ', '_').replace('-', '_')
doc_id = extract_doc_id(url)

if st.sidebar.button("Run Scraper & AI Pipeline (First Time)"):
    # Remove old output files if they exist
    for fname in [f"output/{doc_id}.txt", f"output/{doc_id}_spun.txt", f"output/{doc_id}_reviewed.txt", f"output/{doc_id}_screenshot.png"]:
        try:
            os.remove(fname)
        except FileNotFoundError:
            pass
    # Run scraper.py with URL and doc_id
    result1 = subprocess.run([sys.executable, "scraper.py", url, doc_id], capture_output=True, text=True)
    # Run ai_writer.py with doc_id
    result2 = subprocess.run([sys.executable, "ai_writer.py", doc_id], capture_output=True, text=True)
    # Run ai_reviewer.py with doc_id (this will also save initial versions to ChromaDB)
    result3 = subprocess.run([sys.executable, "ai_reviewer.py", doc_id], capture_output=True, text=True)
    st.sidebar.success("Scraping and initial AI pipeline complete!")
    st.sidebar.text_area("Scraper Output", result1.stdout + '\n' + result1.stderr, height=100)
    st.sidebar.text_area("AI Writer Output", result2.stdout + '\n' + result2.stderr, height=100)
    st.sidebar.text_area("AI Reviewer Output", result3.stdout + '\n' + result3.stderr, height=100)


# Only show the review UI if all three files exist
if all(os.path.exists(f) for f in [f"output/{doc_id}.txt", f"output/{doc_id}_spun.txt", f"output/{doc_id}_reviewed.txt"]):
    # Load chapters
    original = load_text(f"output/{doc_id}.txt")
    spun = load_text(f"output/{doc_id}_spun.txt")
    reviewed = load_text(f"output/{doc_id}_reviewed.txt")

    st.title("Human-in-the-Loop: Chapter Review & Approval")

    # Track version in session state
    if 'version' not in st.session_state:
        st.session_state['version'] = 1

    # Tab selector for chapter version
    tab = st.radio("Select Chapter Version", ("Original", "Spun", "Reviewed"), horizontal=True)

    # Determine which text to show in editor
    if tab == "Original":
        current_text = "\n\n".join(original)
        file_path = f"output/{doc_id}.txt"
        st.header("Original Chapter (View Only)")
        st.write(current_text)
        if st.button("Save to ChromaDB (OG)"):
            save_to_chromadb(
                doc_id=doc_id,
                version=st.session_state['version'],
                stage="og",
                text=current_text,
                is_final=False
            )
            st.success("Original version saved to ChromaDB.")
    elif tab == "Spun":
        current_text = "\n\n".join(spun)
        file_path = f"output/{doc_id}_spun.txt"
        st.header("Spun Chapter (View Only)")
        st.write(current_text)
        if st.button("Save to ChromaDB (Spun)"):
            save_to_chromadb(
                doc_id=doc_id,
                version=st.session_state['version'],
                stage="spun",
                text=current_text,
                is_final=False
            )
            st.success("Spun version saved to ChromaDB.")
    else:
        current_text = "\n\n".join(reviewed)
        file_path = f"output/{doc_id}_reviewed.txt"
        st.header("Reviewed Chapter (Editable)")
        # Editable text area for reviewed version only
        edited_text = st.text_area(f"Edit Reviewed Chapter", value=current_text, height=600)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("Save Changes"):
                try:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(edited_text)
                    st.session_state['version'] += 1
                    save_to_chromadb(
                        doc_id=doc_id,
                        version=st.session_state['version'],
                        stage="human_edited",
                        text=edited_text,
                        is_final=False
                    )
                    st.success(f"Reviewed chapter saved and versioned as human_edited!")
                except Exception as e:
                    st.error(f"Failed to save: {e}")
        with col2:
            if st.button("Re-spin (AI Writer)"):
                try:
                    model = genai.GenerativeModel('models/gemini-1.5-pro-latest')
                    prompt = ("Rewrite this chapter to be more engaging, vivid, and modernized, while keeping the original meaning intact. DO NOT summarize. Retain full details.\n\n" + edited_text)
                    response = model.generate_content(prompt)
                    st.session_state['editor_text'] = response.text.strip()
                    st.session_state['version'] += 1
                    save_to_chromadb(
                        doc_id=doc_id,
                        version=st.session_state['version'],
                        stage="respun",
                        text=response.text.strip(),
                        is_final=False
                    )
                    st.info("Re-spun with AI Writer. You can review and save this version.")
                except Exception as e:
                    st.error(f"AI Writer error: {e}")
        with col3:
            if st.button("Re-review (AI Reviewer)"):
                try:
                    model = genai.GenerativeModel('models/gemini-1.5-pro-latest')
                    prompt = ("You are an AI reviewer. Review the following chapter for grammar, coherence, readability, and consistency. Make small improvements where necessary but retain the original structure and meaning.\n\n" + edited_text)
                    response = model.generate_content(prompt)
                    st.session_state['editor_text'] = response.text.strip()
                    st.session_state['version'] += 1
                    save_to_chromadb(
                        doc_id=doc_id,
                        version=st.session_state['version'],
                        stage="rereviewed",
                        text=response.text.strip(),
                        is_final=False
                    )
                    st.info("Re-reviewed with AI Reviewer. You can review and save this version.")
                except Exception as e:
                    st.error(f"AI Reviewer error: {e}")
        with col4:
            if st.button("Approve & Save to ChromaDB"):
                try:
                    st.session_state['version'] += 1
                    save_to_chromadb(
                        doc_id=doc_id,
                        version=st.session_state['version'],
                        stage="reviewed",
                        text=edited_text,
                        is_final=True
                    )
                    st.success(f"Approved and saved to ChromaDB as reviewed version.")
                except Exception as e:
                    st.error(f"Failed to save to ChromaDB: {e}")
        # If AI output is generated, update the editor
        if 'editor_text' in st.session_state:
            edited_text = st.session_state.pop('editor_text')
            st.experimental_rerun()
else:
    st.info("Please run the scraper and AI pipeline from the sidebar to generate the initial files.")
