"""Shared title mapping for CoreJyothisha PDF → raw/*.md names."""

from __future__ import annotations

from pathlib import Path

from graph_extract_common import slugify_title

TITLE_MAP: dict[str, str] = {
    "Varaha_Mihira_-_Brihat_Jataka": "Brihat_Jataka",
    "BPHS - 2 RSanthanam": "Brihat_Parasara_Hora_Sastra_Vol_2",
    "Book. Bhrigu Samhita T.M.Rao_text": "Bhrigu_Samhita_TMRao",
    "2015.312156.Jataka-Parijata": "Jataka_Parijata",
    "2015.32366.Mahadevas-Jataka-Tatva_text": "Jataka_Tatva_Mahadeva",
    "saravaliofkalyan01kalyuoft": "Saravali",
    "Vedanga Jyotisa Lagadha -  Kupanna Sastry , K.V.Sarma": "Vedanga_Jyotisa_Lagadha",
    "Laghu Parashari OPVerma": "Laghu_Parashari",
    "Kalidasa_-_Uttara_Kalamrita": "Uttara_Kalamrita",
    "Prasna Marga Part 2 by BV Raman": "Prasna_Marga_Part_2",
    "Panangadu_Nambudhiri_-_Prasna_Marga_(Part_I)": "Prasna_Marga_Part_1",
    "Phala Deepika of Mantreshwar Adhyayas 1-28 with English Translation 1961 KRI 9 - Subramanyam Sastri": "Phaladeepika_Mantreswara_1961",
    "Bhavartha Ratnakara by B V Raman": "Bhavartha_Ratnakara",
    "Graha Laghava Ganesa Daivajna Ed. Balachandra Rao S. Uma S.K. (IJHS Suppliment)": "Graha_Laghava",
    "hora shastra (varahamihira)": "Hora_Shastra_Varahamihira",
    "brihat samhita (chidambara iyer)": "Brihat_Samhita",
    "jataka chandrika (venkatesha pandita)": "Jataka_Chandrika",
    "Deva-Keralam-1-Chandrakala-Nadi": "Deva_Keralam_1",
    "Deva-Keralam-2-Chandrakala-Nadi": "Deva_Keralam_2",
    "Deva-Keralam-3-Chandrakala-Nadi": "Deva_Keralam_3",
}

# Priority order for OCR queue
OCR_PRIORITY = [
    "2015.312156.Jataka-Parijata.pdf",
    "saravaliofkalyan01kalyuoft.pdf",
    "Vedanga Jyotisa Lagadha -  Kupanna Sastry , K.V.Sarma.pdf",
    "Panangadu_Nambudhiri_-_Prasna_Marga_(Part_I).pdf",
]

TEXT_BOOKS_MD = [
    "Brihat_Jataka.md",
    "Brihat_Parasara_Hora_Sastra_Vol_2.md",
    "Bhrigu_Samhita_TMRao.md",
    "Laghu_Parashari.md",
    "Prasna_Marga_Part_2.md",
    "Uttara_Kalamrita.md",
]


def md_name_for_pdf(pdf: Path) -> str:
    stem = pdf.stem
    title = TITLE_MAP.get(stem, slugify_title(stem))
    return f"{title}.md"
