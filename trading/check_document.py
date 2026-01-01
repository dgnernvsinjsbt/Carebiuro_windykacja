#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from docx import Document

input_file = "TM5 Coupa Treasury Automatisierung Arbeitsanweisung.docx"
doc = Document(input_file)

print("ZAWARTOŚĆ DOKUMENTU:")
print("="*80)

for i, para in enumerate(doc.paragraphs, 1):
    if para.text.strip():
        print(f"\n[{i}] {para.text}")

print("\n" + "="*80)
