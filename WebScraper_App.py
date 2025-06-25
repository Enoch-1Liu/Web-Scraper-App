import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import re
import os
import urllib.request
import ssl
import certifi
from urllib.parse import urlparse, unquote

st.set_page_config(page_title="PDF Keyword Extractor", layout="wide")

# Utility Functions
def extract_keywords(text):
    return [line.strip() for line in text.splitlines() if line.strip()]

def extract_filename(url):
    parsed_url = urlparse(url)
    return unquote(os.path.basename(parsed_url.path)) or "Unknown"

def read_pdf_content(url):
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    try:
        with urllib.request.urlopen(url, context=ssl_context) as response:
            pdf_content = response.read()
        with fitz.open(stream=pdf_content) as doc:
            return "".join(page.get_text() for page in doc)
    except Exception as e:
        return None

def analyze_text_for_keywords(text, keywords):
    occurrences = {}
    found_sentences = set()
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=[.!?])\s+', text)
    for keyword in keywords:
        count = 0
        pattern = rf"\b{re.escape(keyword)}\b"
        for sentence in sentences:
            if re.search(pattern, sentence, re.IGNORECASE):
                count += 1
                found_sentences.add(sentence.strip())
        if count > 0:
            occurrences[keyword] = count
    return occurrences, list(found_sentences)


# --- Streamlit UI ---

st.title("🔍 PDF Keyword Extractor from URLs")

# -- Input Choice: Keywords --
st.subheader("📌 Keywords Input")
keywords_mode = st.radio("Choose how to input keywords:", ["Upload .txt file", "Manually enter"], key="keywords_mode")

if keywords_mode == "Upload .txt file":
    keyword_file = st.file_uploader("Upload keywords.txt", type="txt", key="kw_file")
    keywords_text = keyword_file.read().decode("utf-8") if keyword_file else ""
else:
    keywords_text = st.text_area("Enter keywords (one per line):", height=150)

# -- Input Choice: URLs --
st.subheader("🔗 PDF URLs Input")
url_mode = st.radio("Choose how to input PDF URLs:", ["Upload .txt file", "Manually enter"], key="url_mode")

if url_mode == "Upload .txt file":
    url_file = st.file_uploader("Upload pdf_urls.txt", type="txt", key="url_file")
    urls_text = url_file.read().decode("utf-8") if url_file else ""
else:
    urls_text = st.text_area("Enter PDF URLs (one per line):", height=150)

# -- Input Choice: Company Names (optional) --
st.subheader("🏢 Company Names Input (Optional)")
name_mode = st.radio("Choose how to input company names:", ["Upload .txt file", "Manually enter", "Skip"], key="name_mode")

if name_mode == "Upload .txt file":
    name_file = st.file_uploader("Upload company_names.txt", type="txt", key="name_file")
    company_names_text = name_file.read().decode("utf-8") if name_file else ""
elif name_mode == "Manually enter":
    company_names_text = st.text_area("Enter company names (one per line):", height=150)
else:
    company_names_text = ""

# -- Process Button --
if st.button("🚀 Start Extraction"):
    if not keywords_text or not urls_text:
        st.error("Please provide both keywords and URLs.")
    else:
        keywords = extract_keywords(keywords_text)
        urls = [u.strip() for u in urls_text.splitlines() if u.strip()]
        companies = [c.strip() for c in company_names_text.splitlines() if c.strip()] if company_names_text else None

        if companies and len(companies) != len(urls):
            st.warning("⚠️ Number of company names doesn't match number of URLs. Using filenames where necessary.")

        results = []
        all_sentences = set()
        progress_bar = st.progress(0)

        for i, url in enumerate(urls):
            st.write(f"🔍 Processing {i+1}/{len(urls)}: {url}")
            text = read_pdf_content(url)
            name = companies[i] if companies and i < len(companies) else extract_filename(url)

            if text:
                occurrences, sentences = analyze_text_for_keywords(text, keywords)
                if occurrences:
                    results.append({"URL": url, "Name": name, **occurrences})
                else:
                    results.append({"URL": url, "Name": name, "Note": "No keywords found."})
                all_sentences.update(sentences)
            else:
                results.append({"URL": url, "Name": name, "Error": "❌ Failed to read PDF."})

            progress_bar.progress((i + 1) / len(urls))

        # Display & Download
        df = pd.DataFrame(results)
        st.subheader("📊 Keyword Count Results")
        st.dataframe(df)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download Results (CSV)", csv, "keyword_results.csv", "text/csv")

        if all_sentences:
            st.subheader("📝 Extracted Sentences with Keywords")
            full_text = "\n\n".join(all_sentences)
            st.text_area("Sentences:", value=full_text, height=300)
            st.download_button("⬇️ Download Sentences", full_text.encode("utf-8"), "keyword_sentences.txt", "text/plain")
