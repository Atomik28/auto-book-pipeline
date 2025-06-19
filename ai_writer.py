import sys
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables from .env
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

def spin_text(input_text):
    model = genai.GenerativeModel('models/gemini-1.5-pro-latest')
    prompt = (
        "You are an AI book content spinner.\n"
        "Given a chapter text, rewrite (spin) it to make it more engaging, vivid, and slightly modernized, while keeping the original meaning intact.\n"
        "DO NOT summarize. Retain full details.\n\n"
        "Here is the chapter content:\n"
        f"{input_text}"
    )
    response = model.generate_content(prompt)
    return response.text.strip()

def spin_chapter(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as f:
        chapter_text = f.read()
    spun_text = spin_text(chapter_text)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(spun_text)
    print(f"AI-spun chapter saved to {output_path} ✅")

if __name__ == "__main__":
    # Accept doc_id as argument
    if len(sys.argv) > 1:
        doc_id = sys.argv[1]
    else:
        doc_id = "chapter1"
    spin_chapter(f"output/{doc_id}.txt", f"output/{doc_id}_spun.txt")
