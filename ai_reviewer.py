import sys
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables from .env
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

def review_text(spun_text):
    model = genai.GenerativeModel('models/gemini-1.5-pro-latest')
    prompt = (
        "You are an AI reviewer.\n"
        "Review the following rewritten chapter for:\n"
        "- grammar\n"
        "- coherence\n"
        "- readability\n"
        "- consistency\n\n"
        "Make small improvements where necessary but retain the original structure and meaning.\n\n"
        "Here is the rewritten content:\n"
        f"{spun_text}"
    )
    response = model.generate_content(prompt)
    return response.text.strip()

def review_chapter(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as f:
        spun_text = f.read()
    reviewed_text = review_text(spun_text)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(reviewed_text)
    print(f"AI-reviewed chapter saved to {output_path} ✅")

if __name__ == "__main__":
    # Accept doc_id as argument
    if len(sys.argv) > 1:
        doc_id = sys.argv[1]
    else:
        doc_id = "chapter1"
    review_chapter(f"output/{doc_id}_spun.txt", f"output/{doc_id}_reviewed.txt")
    # Save all three versions to ChromaDB after review is complete
    from versioning import save_initial_versions
    save_initial_versions(doc_id)
