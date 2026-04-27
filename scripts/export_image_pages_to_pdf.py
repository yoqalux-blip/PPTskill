from __future__ import annotations

import argparse
from pathlib import Path

import fitz


def _sorted_images(image_dir: Path) -> list[Path]:
    files = [
        path
        for path in image_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    ]
    return sorted(files, key=lambda item: item.name)


def export_image_pages_to_pdf(image_dir: Path, output_pdf: Path) -> Path:
    images = _sorted_images(image_dir)
    if not images:
        raise FileNotFoundError(f"No supported images found in {image_dir}")

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()

    for image_path in images:
        img_doc = fitz.open(image_path)
        rect = img_doc[0].rect
        page = doc.new_page(width=rect.width, height=rect.height)
        page.insert_image(page.rect, filename=str(image_path))
        img_doc.close()

    doc.save(output_pdf)
    doc.close()
    return output_pdf


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export an ordered folder of slide images into a single PDF."
    )
    parser.add_argument("--image-dir", required=True, type=Path)
    parser.add_argument("--output-pdf", required=True, type=Path)
    args = parser.parse_args()

    result = export_image_pages_to_pdf(args.image_dir, args.output_pdf)
    print(result)


if __name__ == "__main__":
    main()
