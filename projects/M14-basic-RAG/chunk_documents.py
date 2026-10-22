# src/chunk_documents.py
from pathlib import Path
import json
import re

RAW_DIR = Path("data/processed")
OUT_DIR = Path("data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)

CN_NUM = "一二三四五六七八九十百零〇两"
RE_CHAPTER = re.compile(rf"^第[{CN_NUM}]+章[\s　]*")
RE_ARTICLE = re.compile(rf"^第([{CN_NUM}]+)条[\s　]+")
RE_PAGE = re.compile(r"^[\-—－\s]*\d+[\-—－\s]*$")
RE_PAGE_CN = re.compile(r"^第\s*\d+\s*页$")

# 句末标点：用于判断 PDF 行是否已经完整
RE_ENDS_WITH_PUNCT = re.compile(r"[。；;！？：:”’）」』】]$")

MAX_CHARS = 500

DOC_META = {
    "中华人民共和国劳动合同法": {
        "document_title": "中华人民共和国劳动合同法",
        "source_url": "",
        "version": "待核验",
        "verification_date": "待核验",
    },
    "中华人民共和国劳动合同法实施条例": {
        "document_title": "中华人民共和国劳动合同法实施条例",
        "source_url": "",
        "version": "待核验",
        "verification_date": "待核验",
    },
    "中华人民共和国劳动法": {
        "document_title": "中华人民共和国劳动法",
        "source_url": "",
        "version": "待核验",
        "verification_date": "待核验",
    },
    "中华人民共和国社会保险法": {
        "document_title": "中华人民共和国社会保险法",
        "source_url": "",
        "version": "待核验",
        "verification_date": "待核验",
    },
}

CN_MAP = {c: i for i, c in enumerate("零一二三四五六七八九", start=0)}
CN_MAP.update({"两": 2, "〇": 0})


def cn_to_int(s: str) -> int:
    """中文数字转整数，支持“三”“十”“十五”“二十”“二十一”“一百零二”等。"""
    if not s:
        return 0

    total = 0
    number = 0
    for ch in s:
        if ch == "十":
            total += (number if number > 0 else 1) * 10
            number = 0
        elif ch == "百":
            total += (number if number > 0 else 1) * 100
            number = 0
        elif ch == "千":
            total += (number if number > 0 else 1) * 1000
            number = 0
        else:
            number = CN_MAP.get(ch, 0)
    return total + number

def is_noise(text: str, headers: set, footers: set) -> bool:
    if not text:
        return True
    if RE_PAGE.match(text):
        return True
    if RE_PAGE_CN.match(text):
        return True
    if text in headers or text in footers:
        return True
    return False


def merge_pdf_lines(paragraphs: list) -> list:
    """把 PDF 的逐行文本合并成段落。

    规则：
    - 跳过页码行；
    - 当前行是“第X条”或“第X章”开头 → 另起一段；
    - 上一段是章节标题 → 当前行另起一段（避免正文被吸进标题）；
    - 上一段不以句末标点结尾 → 合并到上一段（PDF 的排版换行）；
    - 否则另起一段。
    """
    merged = []
    for p in paragraphs:
        text = p["text"].strip()
        if not text or RE_PAGE.match(text) or RE_PAGE_CN.match(text):
            continue

        is_new_article = bool(RE_ARTICLE.match(text))
        is_new_chapter = bool(RE_CHAPTER.match(text))

        if not merged:
            merged.append({**p, "text": text})
            continue

        prev = merged[-1]
        prev_text = prev["text"]

        if is_new_article or is_new_chapter:
            merged.append({**p, "text": text})
        elif RE_CHAPTER.match(prev_text):
            # 上一段是章节标题，正文必须另起
            merged.append({**p, "text": text})
        elif not RE_ENDS_WITH_PUNCT.search(prev_text):
            # 上一行没有句末标点，说明是排版换行，拼回去
            prev["text"] = prev_text + text
        else:
            merged.append({**p, "text": text})

    return merged


def split_long_article(text: str, article_number: str, max_chars: int) -> list:
    if len(text) <= max_chars:
        return [text]

    parts = re.split(r"(?<=[。；;！？\n])", text)
    parts = [p.strip() for p in parts if p.strip()]

    chunks, buf = [], ""
    for part in parts:
        if len(buf) + len(part) <= max_chars:
            buf += part
        else:
            if buf:
                chunks.append(buf)
            buf = part
    if buf:
        chunks.append(buf)

    prefixed = []
    for c in chunks:
        if c.startswith(article_number):
            prefixed.append(c)
        else:
            prefixed.append(f"{article_number}（续） {c}")
    return prefixed


def build_chunks(raw: dict, meta: dict) -> list:
    headers = set(raw.get("headers", []))
    footers = set(raw.get("footers", []))
    source_file = raw["source_file"]
    source_type = raw.get("source_type", "docx")
    stem = Path(source_file).stem

    # PDF 先做行合并，docx 的段落已经是段落级
    paragraphs = raw["paragraphs"]
    if source_type == "pdf":
        paragraphs = merge_pdf_lines(paragraphs)

    current_chapter = ""
    current_article = None
    articles = []

    for p in paragraphs:
        text = p["text"].strip()
        if is_noise(text, headers, footers):
            continue

        if RE_CHAPTER.match(text):
            if current_article:
                articles.append(current_article)
                current_article = None
            current_chapter = text
            continue

        m = RE_ARTICLE.match(text)
        if m:
            if current_article:
                articles.append(current_article)
            current_article = {
                "article_number": text[:m.end()].strip(),
                "article_index": cn_to_int(m.group(1)),
                "chapter": current_chapter,
                "text": text,
            }
        else:
            if current_article:
                current_article["text"] += "\n" + text

    if current_article:
        articles.append(current_article)

    chunks = []
    for art in articles:
        sub_texts = split_long_article(art["text"], art["article_number"], MAX_CHARS)
        for i, sub in enumerate(sub_texts):
            chunks.append({
                "chunk_id": f"{stem}-art-{art['article_index']:03d}-{i}",
                "document_title": meta["document_title"],
                "chapter": art["chapter"],
                "article_number": art["article_number"],
                "article_index": art["article_index"],
                "chunk_index": i,
                "text": sub,
                "source_url": meta["source_url"],
                "version": meta["version"],
                "verification_date": meta["verification_date"],
                "source_file": source_file,
                "source_type": source_type,
                "char_count": len(sub),
            })
    return chunks


def main():
    all_chunks = []
    for path in sorted(RAW_DIR.glob("*.raw.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        stem = Path(raw["source_file"]).stem
        meta = DOC_META.get(stem)
        if not meta:
            print(f"[WARN] 未在 DOC_META 中找到 {stem}，跳过。请先补充元数据。")
            continue

        chunks = build_chunks(raw, meta)
        out_path = OUT_DIR / f"{stem}.chunks.json"
        out_path.write_text(
            json.dumps(chunks, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        all_chunks.extend(chunks)
        print(f"[OK] {stem} ({raw.get('source_type', 'docx')}): "
              f"{len(chunks)} 个 Chunk -> {out_path}")

    merged = OUT_DIR / "all_chunks.json"
    merged.write_text(
        json.dumps(all_chunks, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[OK] 总 Chunk 数: {len(all_chunks)} -> {merged}")


if __name__ == "__main__":
    main()