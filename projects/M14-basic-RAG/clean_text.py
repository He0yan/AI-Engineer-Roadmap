# src/clean_text.py
from pathlib import Path
import json
import re

PROCESSED_DIR = Path("data/processed")

# 中文数字条款号
CN_NUM = "一二三四五六七八九十百零〇两"
RE_CHAPTER = re.compile(rf"^第[{CN_NUM}]+章[\s　]*")
RE_ARTICLE = re.compile(rf"^第[{CN_NUM}]+条[\s　]+")
RE_PAGE = re.compile(r"^[\-—－\s]*\d+[\-—－\s]*$")
RE_PAGE_CN = re.compile(r"^第\s*\d+\s*页$")


def is_noise(text: str, headers: list, footers: list) -> bool:
    if not text:
        return True
    if RE_PAGE.match(text):
        return True
    if RE_PAGE_CN.match(text):
        return True
    if text in headers or text in footers:
        return True
    return False


def clean_one(raw: dict) -> dict:
    headers = set(raw.get("headers", []))
    footers = set(raw.get("footers", []))

    cleaned = []
    for p in raw["paragraphs"]:
        text = p["text"].strip()
        if is_noise(text, headers, footers):
            continue
        cleaned.append(text)

    # 合并条文：以“第X条”为切分点
    articles = []
    current = None
    preamble = []

    for text in cleaned:
        if RE_ARTICLE.match(text):
            if current:
                articles.append(current)
            # 取条款号，例如“第三条”
            article_number = RE_ARTICLE.match(text).group(0).strip()
            current = {
                "article_number": article_number,
                "text": text,
            }
        elif RE_CHAPTER.match(text):
            # 章节标题单独保留，作为上下文
            if current:
                articles.append(current)
                current = None
            preamble.append({"type": "chapter", "text": text})
        else:
            if current:
                current["text"] += "\n" + text
            else:
                preamble.append({"type": "text", "text": text})

    if current:
        articles.append(current)

    return {
        "source_file": raw["source_file"],
        "preamble": preamble,
        "article_count": len(articles),
        "articles": articles,
    }




def clean_one_pdf(raw: dict) -> dict:

    cleaned = []
    for page in raw["pages"]:
        cleaned+=(page["lines"])

    # 合并条文：以“第X条”为切分点
    articles = []
    current = None
    preamble = []

    for text in cleaned:
        if RE_PAGE.match(text):
            continue
        if RE_ARTICLE.match(text):
            if current:
                articles.append(current)
            # 取条款号，例如“第三条”
            article_number = RE_ARTICLE.match(text).group(0).strip()
            current = {
                "article_number": article_number,
                "text": text.strip(),
            }
        elif RE_CHAPTER.match(text):
            # 章节标题单独保留，作为上下文
            if current:
                articles.append(current)
                current = None
            preamble.append({"type": "chapter", "text": text.strip()})
        else:
            if current:
                current["text"] += "\n" + text.strip()
            else:
                preamble.append({"type": "text", "text": text.strip()})

    if current:
        articles.append(current)

    return {
        "source_file": raw["source_file"],
        "preamble": preamble,
        "article_count": len(articles),
        "articles": articles,
    }


def main():

    for path in sorted(PROCESSED_DIR.glob("*.raw.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        cleaned = clean_one(raw)

        out_json = PROCESSED_DIR / f"{path.stem.replace('.raw', '')}.clean.json"
        out_json.write_text(
            json.dumps(cleaned, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        out_txt = PROCESSED_DIR / f"{path.stem.replace('.raw', '')}.clean.txt"
        lines = []
        for item in cleaned["preamble"]:
            lines.append(item["text"])
        for art in cleaned["articles"]:
            lines.append("")
            lines.append(art["text"])
        out_txt.write_text("\n".join(lines), encoding="utf-8")

        print(f"[OK] {path.name} -> 条文数={cleaned['article_count']}")




if __name__ == "__main__":
    main()


