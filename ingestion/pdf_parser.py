"""
pdf_parser.py — Extracts text from PDFs (Page-Level Hybrid OCR)
===============================================================
"""

from pathlib import Path
from typing import List, Dict, Any, Union
import pymupdf4llm


def parse_pdf(file_path: Path) -> Union[str, List[Dict[str, Any]]]:
    """
    Extracts text from a PDF file using a Page-Level Hybrid approach.
    For each page, it tries to extract digital text using pymupdf4llm. 
    If a specific page yields very little text (e.g. it is a photograph or scan),
    it routes just that page to local RapidOCR.
    Returns a list of dictionaries with 'text' and 'page_number'.
    """
    str_path = str(file_path.absolute())
    
    try:
        import fitz
        doc = fitz.open(str_path)
    except Exception as e:
        print(f"  Failed to open PDF {file_path.name}: {e}")
        return []

    # 1. First Pass: Digital Extraction via pymupdf4llm
    try:
        md_pages = pymupdf4llm.to_markdown(str_path, page_chunks=True)
    except Exception as e:
        print(f"  pymupdf4llm failed for {file_path.name}: {e}")
        doc.close()
        return []

    # Lazy load local OCR only if needed
    local_ocr = None

    final_pages = []
    
    # 2. Second Pass: Page-Level Evaluation & OCR Fallback
    print(f"  Evaluating {len(md_pages)} pages in {file_path.name}...")
    for i, page_data in enumerate(md_pages):
        page_num = i
        text = page_data.get("text", "")
        
        # Determine if we actually need OCR. 
        # A digital page might just have 15 characters (e.g. "Chapter 1").
        # We should ONLY run OCR if the page has almost no text AND contains an image.
        needs_ocr = False
        if len(text.strip()) < 10:
            try:
                page_obj = doc[page_num]
                if len(page_obj.get_images(full=True)) > 0:
                    needs_ocr = True
            except Exception:
                pass

        if needs_ocr:
            if local_ocr is None:
                print(f"    Page {page_num + 1} appears to be a scanned image. Initializing local OCR engine...")
                try:
                    from rapidocr import RapidOCR
                    local_ocr = RapidOCR()
                except Exception as e:
                    print(f"    Warning: Local OCR initialization failed: {e}")
                    
            if local_ocr:
                print(f"    Page {page_num + 1} appears to be a scanned image. Routing to local OCR...")
                try:
                    page_obj = doc[page_num]
                    pix = page_obj.get_pixmap(dpi=150)
                    img_bytes = pix.tobytes("png")
                    
                    result = local_ocr(img_bytes)
                    if result.txts:
                        text = "\n".join(result.txts)
                        print(f"    Page {page_num + 1}: extracted {len(result.txts)} blocks via local OCR!")
                    else:
                        print(f"    Page {page_num + 1}: no text detected in image.")
                except Exception as e:
                    print(f"    Page {page_num + 1}: Local OCR failed ({e})")
            else:
                print(f"    Page {page_num + 1}: appears to be an image, but OCR engine is unavailable.")
        
        final_pages.append({
            "text": text,
            # Fallback to loop index + 1 if page metadata is missing
            "page_number": page_data.get("metadata", {}).get("page", page_num + 1)
        })
        
    doc.close()
    
    # Check if we actually extracted anything across all pages
    total_text = "".join(p["text"] for p in final_pages)
    if not total_text.strip():
        print(f"  Warning: Failed to extract any text from {file_path.name}")
        return ""
        
    return final_pages
