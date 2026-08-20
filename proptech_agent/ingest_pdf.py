"""
ingest_pdf.py — extracts LEGAL_CORPUS from the real zoning PDF.

Run this ONCE (or whenever the source PDF changes):
    python ingest_pdf.py

It writes data/legal_corpus.json. That file is a GENERATED ARTIFACT, not
something to hand-edit — the PDF is the source of truth, this script is
how you regenerate the searchable index from it.

How it works:
1. Extract text page-by-page with pdfplumber (so we know which page each
   article starts on).
2. Split on article headers ("მუხლი <N>.") to get one chunk per article —
   chunked by article, not by sentence, so a clause never gets separated
   from the exceptions/conditions attached to it.
3. Tag each chunk with topic keywords found in its own text, for the
   RAG agent's keyword search tool.
"""
import json
import re
import pdfplumber

SOURCE_PDF = "data/source_documents/დანართი_2_ზონირების_რეგლამენტი.pdf"
OUTPUT_JSON = "data/legal_corpus.json"
SOURCE_DOCUMENT_NAME = (
    "ქალაქ ბათუმის მუნიციპალიტეტის განაშენიანების გეგმის განაშენიანების "
    "მართვის რეგლამენტი (დანართი 2)"
)

ARTICLE_HEADER = re.compile(r"მუხლი\s+(\d+)\.\s*(.+)")

# keyword -> tag, checked against each article's own text (Georgian terms,
# since the source document is Georgian)
TOPIC_KEYWORDS = {
    "კოეფიციენტი": "coefficients",
    "სიმაღლ": "height",
    "სართულ": "floors",
    "ავტოსადგომ": "parking",
    "დამცავი ზონ": "heritage",
    "არქეოლოგიურ": "heritage",
    "ლანდშაფტ": "landscape",
    "გამწვანებ": "green space",
    "საწარმოო": "industrial",
    "სპეციალური ზონა": "special zone",
    "საცხოვრებელი ზონა": "residential zone",
    "სატრანსპორტო": "transport",
    "წინასაპროექტო კვლევა": "pre-project study",
    "ტოპოგრაფიულ": "topographic study",
    "საინჟინრო-გეოლოგიურ": "geological study",
}


def extract_pages(pdf_path: str) -> list[str]:
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    return pages


def tag_article(title: str, body: str) -> list[str]:
    haystack = title + " " + body
    return [tag for kw, tag in TOPIC_KEYWORDS.items() if kw in haystack] or ["general provisions"]


def build_corpus(pages: list[str]) -> list[dict]:
    corpus = []
    # concatenate with a page-index marker so we can recover page numbers
    full_text = ""
    page_boundaries = []  # (char_offset, page_number)
    for i, page_text in enumerate(pages, start=1):
        page_boundaries.append((len(full_text), i))
        full_text += page_text + "\n"

    matches = list(ARTICLE_HEADER.finditer(full_text))
    for idx, m in enumerate(matches):
        article_num = m.group(1)
        title = m.group(2).strip()
        start = m.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(full_text)
        body = full_text[m.end():end].strip()

        # find which page this article starts on
        page_num = 1
        for offset, pnum in page_boundaries:
            if offset <= start:
                page_num = pnum
            else:
                break

        corpus.append({
            "clause_id": f"BAT-{article_num}",
            "source_document": SOURCE_DOCUMENT_NAME,
            "article": f"მუხლი {article_num}",
            "page": page_num,
            "title": title,
            "text": body,
            "topic_tags": tag_article(title, body),
        })
    return corpus


if __name__ == "__main__":
    pages = extract_pages(SOURCE_PDF)
    corpus = build_corpus(pages)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(corpus, f, ensure_ascii=False, indent=2)

    print(f"Extracted {len(corpus)} articles from {len(pages)} pages -> {OUTPUT_JSON}")
    for c in corpus[:3]:
        print(f"  {c['clause_id']} (p.{c['page']}): {c['title'][:60]}... tags={c['topic_tags']}")
