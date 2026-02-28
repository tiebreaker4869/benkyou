import os
import fitz  # pymupdf


def pdf_to_images(pdf_path: str, output_dir: str, dpi: int = 150) -> list[str]:
    """render PDF to image pages and return list of path"""
    os.makedirs(output_dir, exist_ok=True)

    doc = fitz.open(pdf_path)
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    paths = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=mat)
        filename = f"page_{page_num + 1:03d}.png"
        out_path = os.path.join(output_dir, filename)
        pix.save(out_path)
        paths.append(out_path)

    doc.close()
    return paths
