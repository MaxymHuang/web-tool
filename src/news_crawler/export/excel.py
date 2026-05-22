from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

from news_crawler.models import ArticleResult


def export_to_excel(articles: list[ArticleResult], output_dir: Path) -> Path:
    """Write No. | メディア | 揭載タイトル | URL to an xlsx file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"news_results_{timestamp}.xlsx"

    wb = Workbook()
    ws = wb.active
    ws.title = "News Results"

    headers = ["No.", "メディア", "揭載タイトル", "URL"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for index, article in enumerate(articles, start=1):
        ws.append([index, article.media, article.title, article.url])

    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        ws.column_dimensions[column].width = min(max_length + 2, 80)

    wb.save(path)
    return path
