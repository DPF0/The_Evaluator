"""Build docs/entrega_final.pdf from docs/entrega_final.md via WeasyPrint."""
from pathlib import Path
import markdown
from weasyprint import HTML, CSS

BASE = Path(__file__).resolve().parent
MD = BASE / "entrega_final.md"
CSS_FILE = BASE / "style.css"
OUT = BASE / "entrega_final.pdf"


def main() -> None:
    text = MD.read_text(encoding="utf-8")
    body = markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "sane_lists"],
    )
    html = (
        "<!DOCTYPE html><html lang=\"es\"><head>"
        "<meta charset=\"utf-8\">"
        "<title>The Evaluator — Entregable final</title>"
        "</head><body>" + body + "</body></html>"
    )
    HTML(string=html).write_pdf(str(OUT), stylesheets=[CSS(filename=str(CSS_FILE))])
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
