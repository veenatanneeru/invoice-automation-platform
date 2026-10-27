cat > scripts/diagnose.py << 'EOF'
"""Show what an extractor returns for one text invoice and one scanned invoice."""
import json
from pathlib import Path

from app.extraction import local

labels = json.loads(Path("data/labels/labels_hard.json").read_text())
for want_scanned in (False, True):
    lab = next(l for l in labels if l["scanned"] == want_scanned)
    path = Path("data/raw_hard") / lab["file"]
    print("=====", lab["file"], "scanned" if want_scanned else "text PDF")
    print("GOT:     ", local.extract_with_ollama(path).model_dump())
    print("EXPECTED:", lab["fields"])
EOF