import json
import re
from pathlib import Path

PATTERN = re.compile(r"^(?P<title>.+?)_(?P<date>\d{8})$")

data = {}
for p in sorted(Path("./data/processed").glob("*.raw.json")):
    name = p.name.removesuffix(".raw.json")

    m = PATTERN.match(name)
    if m:
        document_title = m.group("title")
        version = m.group("date")
    else:
        document_title = name
        version = "待核验"

    data[name] = {
        "document_title": document_title,
        "source_url": "",
        "version": version,
        "verification_date": "待核验",
    }

json_str = json.dumps(data, ensure_ascii=False, indent=4)
print(json_str)

with open("metadata.json", "w", encoding="utf-8") as f:
    f.write(json_str)