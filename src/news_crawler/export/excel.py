from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

from news_crawler.i18n import t
from news_crawler.models import ArticleResult


def export_to_excel(
    articles: list[ArticleResult],
    output_dir: Path,
    ui_lang: str = "en",
) -> Path:
    """Write localized columns to an xlsx file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"news_results_{timestamp}.xlsx"

    wb = Workbook()
    ws = wb.active
    ws.title = "News Results"

    headers = [
        t(ui_lang, "excel_no"),
        t(ui_lang, "excel_date"),
        t(ui_lang, "excel_media"),
        t(ui_lang, "excel_title"),
        t(ui_lang, "excel_url"),
        t(ui_lang, "excel_market"),
    ]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for index, article in enumerate(articles, start=1):
        market_label = t(ui_lang, f"market_{article.market}") if article.market else ""
        ws.append(
            [
                index,
                article.published_at,
                article.media,
                article.title,
                article.url,
                market_label,
            ]
        )

    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        ws.column_dimensions[column].width = min(max_length + 2, 80)

    wb.save(path)
    return path
