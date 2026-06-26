#!/usr/bin/env python3
"""Extract text from all three PDFs and save to text files."""
import os
from pypdf import PdfReader

PDFS = [
    ('Mantreswara_s__Phaladeeplka_.pdf',
     '/Users/ganesha/Projects/04-UX-Practice/Panchang/Gyan/Mantreswara_s__Phaladeeplka_.pdf'),
    ('Phaladeepika_english.pdf',
     '/Users/ganesha/Projects/04-UX-Practice/Panchang/Gyan/Phaladeepika_english.pdf'),
    ('ebharati-pdf-1621242374Sarvartha-Chintamani-JN-Bhasin_compressed.pdf',
     '/Users/ganesha/Projects/04-UX-Practice/Panchang/Gyan/ebharati-pdf-1621242374Sarvartha-Chintamani-JN-Bhasin_compressed.pdf'),
]

OUT_DIR = '/Users/ganesha/Projects/04-UX-Practice/Panchang/panchanga_muhurtha/extracted_texts'

for label, path in PDFS:
    out_path = os.path.join(OUT_DIR, label.replace('.pdf', '.txt'))
    print(f'Extracting: {label}')
    reader = PdfReader(path)
    total = len(reader.pages)
    with open(out_path, 'w', encoding='utf-8') as f:
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                f.write(f'\n=== PAGE {i+1} ===\n')
                f.write(text)
                f.write('\n')
            else:
                f.write(f'\n=== PAGE {i+1} ===\n[NO EXTRACTABLE TEXT]\n')
            if (i + 1) % 50 == 0:
                print(f'  {label}: {i+1}/{total} pages')
    print(f'  {label}: COMPLETE ({total} pages)')
    print(f'  Output: {out_path}')
