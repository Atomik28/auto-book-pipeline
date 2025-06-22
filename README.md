# Automated Book Publication Workflow

**Objective:**  
Create a system to fetch content from a web URL, apply an AI-driven “spin” to chapters, allow multiple human-in-the-loop iterations, and manage content versions.

---

## 📦 Project Structure

auto-book-pipeline/
├── app.py # Streamlit UI & pipeline orchestration
├── scraper.py # Playwright scraper + screenshot
├── ai_writer.py # AI “spin” (Gemini) of raw text
├── ai_reviewer.py # AI review/refinement (Gemini)
├── versioning.py # ChromaDB save/get helpers + version logic
├── pipeline.py # (optional) Python wrapper for full pipeline
├── test.py # CLI to inspect ChromaDB contents
├── output/ # Scraped & processed text + screenshots
├── chroma_db/ # Local ChromaDB persistent store
├── venv/ # Python virtual environment
├── .env # Gemini API key
└── requirements.txt # Python dependencies

---

## ⚙️ Core Capabilities

1. **Scraping & Screenshots**  
   Uses Playwright to fetch chapter text and save a full-page PNG.

2. **AI Writing & Review**  
   - `ai_writer.py` spins (rewrites) each chapter via Google Gemini.  
   - `ai_reviewer.py` refines the spun text for grammar, coherence, readability.

3. **Human-in-the-Loop**  
   Streamlit UI displays Original, Spun, and Reviewed versions in tabs with an editable area for final review.

4. **Agentic API**  
   Each step (scrape, spin, review, version) is exposed as a Python function, and `pipeline.py` wraps them into a single `run_full_pipeline(url, doc_id)` call.

5. **Versioning & Consistency**  
   Uses ChromaDB for persisting all versions with metadata:
   ```json
   {
     "id": "<doc_id>_v<version>_<stage>",
     "document": "<text…>",
     "metadata": {
       "doc_id": "...",
       "version": n,
       "stage": "...",
       "timestamp": "...",
       "is_final": true|false
     }
   }
Dynamic versioning always picks the next free version.

5. **RL-Like Retrieval**
A simple heuristic in Streamlit sidebar: from all is_final=true versions of a chapter, select the one with the highest version number.

🚀 Quick Start

## ⚙️ Setup Instructions

1. **Clone the repo:**
   ```bash
   git clone https://github.com/Atomik28/auto-book-pipeline
   cd auto-book-pipeline

    python3 -m venv venv
    source venv/bin/activate    # On Windows: `venv\Scripts\activate`
    pip install -r requirements.txt
    Add your Gemini API key
    Create a .env file:
    Run the Streamlit app


🎯 Usage
Step 1: Scrape & Generate

Enter a chapter URL (e.g. Wikisource).

Click Run Scraper & AI Pipeline.

Outputs in output/ and logs in sidebar.

Step 2: Human-in-the-Loop Review

Switch between Original, Spun, and Reviewed tabs.

Edit Reviewed text, then click:

Save Changes → human-edited draft

Re-spin (AI Writer) → AI rewrite

Re-review (AI Reviewer) → AI refinement

Approve & Save to ChromaDB → final version

Step 3: Retrieve Published Chapter

In sidebar “Retrieve Published Chapter”, pick or enter a doc_id.

Click Get Final Version to display the highest-version final draft.

🛠️ **Inspecting ChromaDB**
Use test.py to dump all IDs & metadata:

    python test.py

📈 **Future Enhancements**
True RL policy for retrieval (train on user feedback).

FastAPI wrapper for REST-style agent orchestration.

Batch processing of multiple chapters.

Export to ePub/PDF for final publication.

Enjoy your AI-powered book pipeline! Questions or PRs welcome. 🚀