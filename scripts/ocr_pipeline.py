#!/usr/bin/env python3
"""
ocr_pipeline.py - High-Performance Parallel OCR Pipeline for Scanned Vedic PDFs
Phase 02: Build a thorough, resilient, and highly efficient text extractor.
Supports multi-language OCR (English + Sanskrit/Hindi), image preprocessing,
and page-level progress caching to resume interrupted runs.
"""

import os
import sys
import argparse
import json
import time
import urllib.request
import ssl
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import pdfplumber
from pdf2image import convert_from_path
import pytesseract
from PIL import Image, ImageOps, ImageEnhance
from tqdm import tqdm

# Constants
TESSDATA_BEST_URL = "https://github.com/tesseract-ocr/tessdata_best/raw/main/"
LANGUAGES_TO_DOWNLOAD = ["eng", "san", "hin", "osd"]

TITLE_MAP = {
    "2015.486584.Jaimini-Sutras": "Jaimini_Sutras",
    "Book. Gochar Phaladeepika - Dr. U.S. Pulippani": "Gochar_Phaladeepika_Pulippani",
    "Brihat Parasara Hora Sastra with English Translation Girish Chand Sharma Volume 1": "Brihat_Parasara_Hora_Sastra_Vol_1",
    "Hora Sara RSanthanam Eng": "Hora_Sara",
    "Jyotish-2017-V-P-Goel-Predicting-Through-Jaimini-Astrology-1": "Predicting_Through_Jaimini_Astrology",
    "Mantreswara_s__Phaladeeplka_": "Phaladeepika_Mantreswara",
    "Phaladeepika_english": "Phaladeepika_English_Translation",
    "Predict-Effectively-Throught-Yogini-Dasha-by-VP-Goel-pdf": "Predict_Effectively_Through_Yogini_Dasha",
    "ebharati-pdf-1621242374Sarvartha-Chintamani-JN-Bhasin_compressed": "Sarvartha_Chintamani",
}

def download_traineddata(lang: str, dest_dir: Path):
    """Download the traineddata file from Tesseract's tessdata_best repo."""
    filename = f"{lang}.traineddata"
    url = f"{TESSDATA_BEST_URL}{filename}"
    dest_path = dest_dir / filename
    
    print(f"Downloading {filename} from tessdata_best...")
    # Handle SSL context for python urllib
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    try:
        # Get content length for progress bar
        with urllib.request.urlopen(url, context=ctx) as response:
            meta = response.info()
            file_size = int(meta.get("Content-Length", 0))
            
        print(f"File size: {file_size / (1024*1024):.2f} MB")
        
        # Download with custom chunk tracking
        downloaded = 0
        block_size = 8192
        
        with urllib.request.urlopen(url, context=ctx) as response, open(dest_path, "wb") as out_file:
            with tqdm(total=file_size, unit="B", unit_scale=True, desc=filename) as pbar:
                while True:
                    buffer = response.read(block_size)
                    if not buffer:
                        break
                    downloaded += len(buffer)
                    out_file.write(buffer)
                    pbar.update(len(buffer))
        print(f"Successfully downloaded {filename}")
    except Exception as e:
        print(f"Error downloading {filename}: {e}", file=sys.stderr)
        if dest_path.exists():
            dest_path.unlink()
        raise e

def ensure_tessdata(tessdata_dir: Path, langs: list):
    """Check and download necessary traineddata files."""
    tessdata_dir.mkdir(parents=True, exist_ok=True)
    for lang in langs:
        # In case lang is a combination like "eng+san", split them
        for single_lang in lang.split("+"):
            if not single_lang.strip():
                continue
            dest_path = tessdata_dir / f"{single_lang}.traineddata"
            if not dest_path.exists():
                print(f"Required language file not found: {dest_path.name}")
                download_traineddata(single_lang, tessdata_dir)
    
    # Always ensure osd.traineddata is present
    osd_path = tessdata_dir / "osd.traineddata"
    if not osd_path.exists():
        download_traineddata("osd", tessdata_dir)

def preprocess_image(img: Image.Image, contrast: float = 2.0, sharpness: float = 1.0, denoise: bool = False) -> Image.Image:
    """Preprocess image to maximize Tesseract OCR accuracy."""
    # Convert to Grayscale
    img_gray = ImageOps.grayscale(img)
    
    # Apply median filter to remove speckle noise if requested
    if denoise:
        from PIL import ImageFilter
        img_gray = img_gray.filter(ImageFilter.MedianFilter(size=3))
        
    # Enhance Sharpness
    if sharpness != 1.0:
        sharpness_enhancer = ImageEnhance.Sharpness(img_gray)
        img_gray = sharpness_enhancer.enhance(sharpness)
        
    # Enhance Contrast
    if contrast != 1.0:
        contrast_enhancer = ImageEnhance.Contrast(img_gray)
        img_gray = contrast_enhancer.enhance(contrast)
        
    return img_gray

def ocr_single_page(pdf_path: str, page_num: int, tessdata_dir: str, lang: str, contrast: float = 2.0, sharpness: float = 1.0, denoise: bool = False) -> str:
    """Render a single PDF page to an image, preprocess, and run OCR."""
    # Set the Tessdata Prefix environment variable in the child process
    os.environ["TESSDATA_PREFIX"] = tessdata_dir
    
    # Render PDF page to image (page_num is 0-indexed, pdf2image uses 1-indexed first/last page)
    images = convert_from_path(
        pdf_path,
        dpi=300,
        first_page=page_num + 1,
        last_page=page_num + 1,
        thread_count=1
    )
    
    if not images:
        raise ValueError(f"Failed to render page {page_num + 1}")
    
    img = images[0]
    processed_img = preprocess_image(img, contrast, sharpness, denoise)
    
    # Tesseract configuration
    config = f'--tessdata-dir "{tessdata_dir}" --psm 3'
    
    # Run Tesseract OCR
    text = pytesseract.image_to_string(processed_img, lang=lang, config=config)
    return text

def page_worker(task):
    """Worker process task wrapper."""
    pdf_path, page_num, tessdata_dir, lang, cache_file_path, contrast, sharpness, denoise = task
    
    start_time = time.time()
    try:
        text = ocr_single_page(pdf_path, page_num, tessdata_dir, lang, contrast, sharpness, denoise)
        elapsed = time.time() - start_time
        
        # Save to page cache
        cache_data = {
            "page_num": page_num + 1,
            "method": "ocr",
            "text": text,
            "elapsed_seconds": elapsed,
            "success": True
        }
        
        with open(cache_file_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
        return {"page_num": page_num + 1, "success": True, "method": "ocr", "elapsed": elapsed}
    except Exception as e:
        elapsed = time.time() - start_time
        return {"page_num": page_num + 1, "success": False, "error": str(e), "elapsed": elapsed}

def process_pdf(pdf_path: Path, output_dir: Path, cache_dir: Path, tessdata_dir: Path, lang: str, allow_bypass: bool, max_workers: int, max_pages: int = None, contrast: float = 2.0, sharpness: float = 1.0, denoise: bool = False):
    """Process a single PDF using the hybrid parallel pipeline."""
    pdf_name = pdf_path.stem
    
    # Determine the clean title
    clean_title = TITLE_MAP.get(pdf_name, pdf_name)
    if clean_title == pdf_name:
        import re
        clean_title = re.sub(r'[^a-zA-Z0-9\s_\-]', '', pdf_name)
        clean_title = re.sub(r'[\s_\-]+', '_', clean_title).strip('_')
        
    pdf_output_path = output_dir / f"{clean_title}.md"
    pdf_cache_dir = cache_dir / pdf_name
    pdf_cache_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\nProcessing PDF: {pdf_path.name}")
    print(f"Cache Directory: {pdf_cache_dir}")
    print(f"Output File: {pdf_output_path}")
    
    # 1. Get total pages
    total_pages = 0
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            if max_pages and total_pages > max_pages:
                total_pages = max_pages
            print(f"Total pages: {total_pages}")
            
            # Perform quick hybrid check across all pages ONLY if allow_bypass is True
            if allow_bypass:
                digital_pages_extracted = 0
                for idx, page in enumerate(pdf.pages):
                    if idx >= total_pages:
                        break
                    cache_file = pdf_cache_dir / f"page_{idx + 1}.json"
                    
                    if cache_file.exists():
                        continue
                        
                    # Extract text digitally
                    digital_text = page.extract_text()
                    # If there is substantial digital text, bypass OCR
                    if digital_text and len(digital_text.strip()) > 50:
                        cache_data = {
                            "page_num": idx + 1,
                            "method": "digital",
                            "text": digital_text,
                            "elapsed_seconds": 0.05,
                            "success": True
                        }
                        with open(cache_file, "w", encoding="utf-8") as f:
                            json.dump(cache_data, f, ensure_ascii=False, indent=2)
                        digital_pages_extracted += 1
                
                if digital_pages_extracted > 0:
                    print(f"Extracted {digital_pages_extracted} pages digitally (hybrid bypass).")
    except Exception as e:
        print(f"Warning: Could not open PDF with pdfplumber: {e}. Falling back to pypdf.", file=sys.stderr)
        # We will determine total pages using pypdf reader if pdfplumber fails
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        if max_pages and total_pages > max_pages:
            total_pages = max_pages

    # 2. Check cache status for OCR pages
    missing_pages = []
    cached_pages_count = 0
    for idx in range(total_pages):
        cache_file = pdf_cache_dir / f"page_{idx + 1}.json"
        if cache_file.exists():
            # Verify if cached file is valid and successful
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("success", False):
                    cached_pages_count += 1
                    continue
            except:
                pass
        missing_pages.append(idx)
        
    print(f"Progress status: {cached_pages_count} / {total_pages} pages already completed.")
    
    if not missing_pages:
        print("All pages already processed.")
    else:
        print(f"Queueing {len(missing_pages)} pages for OCR processing using {max_workers} worker threads/processes...")
        
        # Configure Tesseract to limit its internal OpenMP threads to prevent CPU thrashing
        os.environ["OMP_THREAD_LIMIT"] = "1"
        
        tasks = []
        for page_num in missing_pages:
            cache_file_path = pdf_cache_dir / f"page_{page_num + 1}.json"
            tasks.append((str(pdf_path), page_num, str(tessdata_dir), lang, cache_file_path, contrast, sharpness, denoise))
            
        # Run multiprocessing executor
        success_count = 0
        fail_count = 0
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(page_worker, task): task[1] for task in tasks}
            
            with tqdm(total=len(tasks), desc="OCR Progress", unit="page") as pbar:
                for future in as_completed(futures):
                    page_num_1indexed = futures[future] + 1
                    try:
                        res = future.result()
                        if res.get("success", False):
                            success_count += 1
                        else:
                            fail_count += 1
                            print(f"\nPage {page_num_1indexed} failed: {res.get('error')}", file=sys.stderr)
                    except Exception as e:
                        fail_count += 1
                        print(f"\nPage {page_num_1indexed} generated an exception: {e}", file=sys.stderr)
                    pbar.update(1)
                    
        print(f"OCR session finished: {success_count} succeeded, {fail_count} failed.")
        
    # 3. Consolidate pages into final output text
    print("Consolidating pages into Markdown format...")
    valid_pages = 0
    with open(pdf_output_path, "w", encoding="utf-8") as out_file:
        out_file.write(f"# {clean_title.replace('_', ' ')}\n\n")
        for idx in range(total_pages):
            cache_file = pdf_cache_dir / f"page_{idx + 1}.json"
            if cache_file.exists():
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if data.get("success", False):
                        out_file.write(f"## Page {idx + 1}\n\n")
                        out_file.write(data.get("text", "").strip())
                        out_file.write("\n\n---\n\n")
                        valid_pages += 1
                        continue
                except:
                    pass
            # If a page is missing/failed, write a placeholder
            out_file.write(f"## Page {idx + 1}\n\n[FAILED TO EXTRACT TEXT]\n\n---\n\n")
            
    print(f"Compilation complete: {valid_pages} / {total_pages} pages successfully compiled.")
    print(f"Output saved to: {pdf_output_path}")

def main():
    parser = argparse.ArgumentParser(description="Parallel Vedic PDF OCR Pipeline")
    parser.add_argument("--input-dir", type=str, default="/Users/ganesha/Projects/04-UX-Practice/Panchang/Gyan",
                        help="Directory containing source PDFs")
    parser.add_argument("--output-dir", type=str, default="/Users/ganesha/Projects/04-UX-Practice/Panchang/Gyan/extracted_markdown",
                        help="Directory to save output markdown files")
    parser.add_argument("--lang", type=str, default="eng",
                        help="Tesseract languages (default: eng for English+IAST books)")
    parser.add_argument("--allow-bypass", action="store_true",
                        help="Allow digital text extraction bypass (not recommended for scanned files)")
    parser.add_argument("--workers", type=int, default=None,
                        help="Number of concurrent worker processes (default: number of CPUs)")
    parser.add_argument("--only-file", type=str, default=None,
                        help="Process only a single PDF filename (e.g., 'Phaladeepika_english.pdf')")
    parser.add_argument("--max-pages", type=int, default=None,
                        help="Limit the number of pages processed per PDF (for testing)")
    parser.add_argument("--contrast", type=float, default=2.0,
                        help="Contrast enhancement factor (default: 2.0)")
    parser.add_argument("--sharpness", type=float, default=1.0,
                        help="Sharpness enhancement factor (default: 1.0)")
    parser.add_argument("--denoise", action="store_true",
                        help="Apply 3x3 median filter to denoise scans")
    
    args = parser.parse_args()
    
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    # Maintain cache in extracted_texts/.ocr_cache to preserve previous progress
    cache_dir = output_dir.parent / "extracted_texts" / ".ocr_cache"
    tessdata_dir = output_dir.parent / "tessdata"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    tessdata_dir.mkdir(parents=True, exist_ok=True)
    
    print("=== Vedic Astrology Parallel OCR Pipeline ===")
    print(f"Input Directory:  {input_dir}")
    print(f"Output Directory: {output_dir}")
    print(f"Tessdata Directory: {tessdata_dir}")
    print(f"Language:         {args.lang}")
    
    # Step 1: Ensure Tesseract language files are present
    try:
        ensure_tessdata(tessdata_dir, [args.lang])
    except Exception as e:
        print(f"Critical error preparing Tesseract language files: {e}", file=sys.stderr)
        print("Please check your network connection or manually copy traineddata files to the tessdata folder.", file=sys.stderr)
        sys.exit(1)
        
    # Step 2: Locate PDFs to process
    if args.only_file:
        pdf_files = [input_dir / args.only_file]
        if not pdf_files[0].exists():
            print(f"Error: Specified file not found: {pdf_files[0]}", file=sys.stderr)
            sys.exit(1)
    else:
        pdf_files = sorted(list(input_dir.glob("*.pdf")))
        
    if not pdf_files:
        print("No PDF files found to process.")
        sys.exit(0)
        
    print(f"Found {len(pdf_files)} PDF file(s) to process.")
    
    # Process each PDF
    start_time = time.time()
    for pdf_file in pdf_files:
        if not pdf_file.exists():
            print(f"Skipping missing file: {pdf_file}")
            continue
        try:
            process_pdf(
                pdf_path=pdf_file,
                output_dir=output_dir,
                cache_dir=cache_dir,
                tessdata_dir=tessdata_dir,
                lang=args.lang,
                allow_bypass=args.allow_bypass,
                max_workers=args.workers,
                max_pages=args.max_pages,
                contrast=args.contrast,
                sharpness=args.sharpness,
                denoise=args.denoise
            )
        except Exception as e:
            print(f"Failed to process PDF {pdf_file.name}: {e}", file=sys.stderr)
            
    total_elapsed = time.time() - start_time
    print(f"\nAll tasks completed in {total_elapsed:.2f} seconds.")

if __name__ == "__main__":
    main()
