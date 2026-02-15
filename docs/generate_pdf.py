import re
import textwrap
from pathlib import Path


def normalize_markdown(md_text: str) -> list[str]:
    lines: list[str] = []
    for raw in md_text.splitlines():
        line = raw.rstrip()
        if not line:
            lines.append("")
            continue

        if line.startswith("#"):
            title = re.sub(r"^#+\s*", "", line).strip()
            lines.append("")
            lines.append(title.upper())
            lines.append("-" * min(len(title), 100))
            lines.append("")
            continue

        wrapped = textwrap.wrap(
            line,
            width=100,
            break_long_words=False,
            replace_whitespace=False,
            drop_whitespace=False,
        )
        if wrapped:
            lines.extend([w.rstrip() for w in wrapped])
        else:
            lines.append("")
    return lines


def paginate(lines: list[str], max_lines_per_page: int = 52) -> list[list[str]]:
    pages: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        current.append(line)
        if len(current) >= max_lines_per_page:
            pages.append(current)
            current = []
    if current:
        pages.append(current)
    return pages


def pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_pdf_text_stream(page_lines: list[str], page_num: int, total_pages: int) -> bytes:
    y_start = 770
    x = 45
    line_height = 14

    out = []
    out.append("BT")
    out.append("/F1 10 Tf")
    out.append(f"{x} {y_start} Td")

    header = f"CMS AI Search - Elasticsearch Architecture Deep Dive (Page {page_num}/{total_pages})"
    out.append(f"({pdf_escape(header)}) Tj")
    out.append("T*")
    out.append("(================================================================================) Tj")
    out.append("T*")

    for line in page_lines:
        out.append(f"({pdf_escape(line)}) Tj")
        out.append("T*")

    out.append("ET")
    stream = "\n".join(out).encode("latin-1", errors="replace")
    return stream


def write_simple_pdf(output_path: Path, pages: list[list[str]]) -> None:
    objects: list[bytes] = []

    # 1: Catalog, 2: Pages, 3.. page objects + content objects, last: font
    num_pages = len(pages)
    first_page_obj = 3
    first_content_obj = first_page_obj + num_pages
    font_obj = first_content_obj + num_pages

    # Catalog
    objects.append(f"<< /Type /Catalog /Pages 2 0 R >>".encode("latin-1"))

    # Pages (kids list patched after page objects known)
    kids_refs = " ".join([f"{first_page_obj + i} 0 R" for i in range(num_pages)])
    objects.append(
        f"<< /Type /Pages /Kids [{kids_refs}] /Count {num_pages} >>".encode("latin-1")
    )

    # Page objects
    for i in range(num_pages):
        content_ref = f"{first_content_obj + i} 0 R"
        page_obj = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_obj} 0 R >> >> "
            f"/Contents {content_ref} >>"
        )
        objects.append(page_obj.encode("latin-1"))

    # Content stream objects
    for i, page_lines in enumerate(pages, start=1):
        stream = build_pdf_text_stream(page_lines, i, num_pages)
        content_obj = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1")
            + stream
            + b"\nendstream"
        )
        objects.append(content_obj)

    # Font object
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    # Write file with xref
    pdf = bytearray()
    pdf.extend(b"%PDF-1.4\n")
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{idx} 0 obj\n".encode("latin-1"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    pdf.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        pdf.extend(f"{off:010d} 00000 n \n".encode("latin-1"))

    pdf.extend(
        (
            "trailer\n"
            f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            "startxref\n"
            f"{xref_start}\n"
            "%%EOF\n"
        ).encode("latin-1")
    )

    output_path.write_bytes(pdf)


def main() -> None:
    base = Path(__file__).resolve().parent
    source = base / "elasticsearch-architecture-deep-dive.md"
    output = base / "elasticsearch-architecture-deep-dive.pdf"

    md_text = source.read_text(encoding="utf-8")
    normalized = normalize_markdown(md_text)
    pages = paginate(normalized, max_lines_per_page=52)
    write_simple_pdf(output, pages)
    print(f"Generated PDF: {output}")
    print(f"Pages: {len(pages)}")


if __name__ == "__main__":
    main()
