"""
Download CUMCM 2023-2024 official exhibition papers from dxs.moe.gov.cn.

The official exhibition pages expose each paper as a detail page with page images.
This script:
1. Collects all detail links from the rendered 2023/2024 exhibition list pages
2. Extracts page image URLs from each detail page
3. Downloads the images and compiles them into a single PDF per paper
4. Writes a download report into the target papers directory

Dependencies:
    - playwright
    - requests
    - pillow

Playwright is already available in this environment. If the browser binaries
are missing, run:
    python -m playwright install chromium
"""

from __future__ import annotations

import asyncio
import io
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import requests
from bs4 import BeautifulSoup


BASE_DIR = Path(r"D:\desktop\数学建模skill")
PAPERS_DIR = BASE_DIR / "references" / "papers"

LIST_PAGES = {
    "2023": "https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmlw/2023qgdxssxjmjslwzs/",
    "2024": "https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmlw/2024qgdxssxjmjslwzs/",
}


@dataclass
class PaperMeta:
    year: str
    title: str
    code: str
    url: str


def slugify_filename(name: str) -> str:
    name = re.sub(r"[^\w\-\.\u4e00-\u9fff]+", "_", name.strip())
    name = re.sub(r"_+", "_", name).strip("._")
    return name[:180] if len(name) > 180 else name


def extract_code(title: str) -> str:
    m = re.search(r"（([A-Z]\d+)）", title)
    if m:
        return m.group(1)
    m = re.search(r"\(([A-Z]\d+)\)", title)
    if m:
        return m.group(1)
    m = re.search(r"([A-Z]\d+)", title)
    return m.group(1) if m else "UNKNOWN"


def make_output_name(meta: PaperMeta) -> str:
    # Clear, stable ASCII naming. The official titles do not include school names.
    return f"{meta.year}-{meta.code}.pdf"


def requests_get(url: str, *, timeout: int = 40, retries: int = 3) -> requests.Response:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://dxs.moe.gov.cn/zx/hd/sxjm/sxjmlw/",
    }
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            return resp
        except Exception as exc:
            last_exc = exc
            time.sleep(1.0 * attempt)
    raise last_exc  # type: ignore[misc]


async def collect_list_links() -> list[PaperMeta]:
    from playwright.async_api import async_playwright

    metas: list[PaperMeta] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            for year, url in LIST_PAGES.items():
                page = await browser.new_page(viewport={"width": 1600, "height": 1200})
                await page.goto(url, wait_until="networkidle", timeout=90000)
                items = await page.eval_on_selector_all(
                    "a[href]",
                    """
                    els => els.map(a => ({
                        text: (a.innerText || a.textContent || '').trim(),
                        href: a.href
                    })).filter(x =>
                        x.href.includes('/zx/a/') &&
                        x.text.includes('全国大学生数学建模竞赛') &&
                        x.text.includes('题论文展示')
                    )
                    """,
                )
                dedup: dict[str, str] = {}
                for item in items:
                    dedup[item["href"]] = item["text"]
                for href, title in sorted(dedup.items()):
                    metas.append(PaperMeta(year=year, title=title, code=extract_code(title), url=href))
                await page.close()
        finally:
            await browser.close()

    # Stable order: year, question, code
    metas.sort(key=lambda m: (m.year, m.code, m.url))
    return metas


def extract_image_urls(detail_html: str) -> tuple[str, list[str]]:
    soup = BeautifulSoup(detail_html, "html.parser")
    title = ""
    title_el = soup.select_one(".detail-tit")
    if title_el:
        title = " ".join(title_el.get_text(" ", strip=True).split())
    if not title:
        title = "UNKNOWN"

    urls: list[str] = []
    for img in soup.select("div.detail-content img[src]"):
        src = img.get("src", "").strip()
        if src and src not in urls:
            urls.append(src)
    return title, urls


def download_image(url: str) -> bytes:
    resp = requests_get(url, timeout=60, retries=4)
    return resp.content


def save_images_to_pdf(image_blobs: Iterable[bytes], out_path: Path) -> None:
    from PIL import Image

    pil_images = []
    for blob in image_blobs:
        with Image.open(io.BytesIO(blob)) as im:
            pil_images.append(im.convert("RGB"))

    if not pil_images:
        raise ValueError("no images to save")

    first, rest = pil_images[0], pil_images[1:]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    first.save(out_path, save_all=True, append_images=rest)


def process_paper(meta: PaperMeta) -> dict:
    html = requests_get(meta.url, timeout=60, retries=3).text
    page_title, image_urls = extract_image_urls(html)
    if not image_urls:
        return {
            "meta": meta,
            "title": page_title,
            "ok": False,
            "reason": "no page images found",
            "images": 0,
        }

    out_name = make_output_name(meta)
    out_path = PAPERS_DIR / out_name
    blob_by_url = {}
    with ThreadPoolExecutor(max_workers=min(8, max(2, len(image_urls)))) as pool:
        futures = {pool.submit(download_image, u): u for u in image_urls}
        for fut in as_completed(futures):
            url = futures[fut]
            try:
                blob_by_url[url] = fut.result()
            except Exception as exc:
                return {
                    "meta": meta,
                    "title": page_title,
                    "ok": False,
                    "reason": f"image download failed: {url} -> {exc}",
                    "images": len(blob_by_url),
                }
    ordered_blobs = [blob_by_url[u] for u in image_urls]

    save_images_to_pdf(ordered_blobs, out_path)
    return {
        "meta": meta,
        "title": page_title,
        "ok": True,
        "path": out_path,
        "images": len(image_urls),
    }


def write_report(results: list[dict], failed: list[dict]) -> Path:
    total = len([r for r in results if r.get("ok")])
    by_year: dict[str, int] = {}
    for r in results:
        if r.get("ok"):
            year = r["meta"].year
            by_year[year] = by_year.get(year, 0) + 1

    report_lines = [
        "# CUMCM PDF Download Report",
        "",
        f"- Successful PDFs: {total}",
        f"- Source 2023 official exhibition pages: {by_year.get('2023', 0)}",
        f"- Source 2024 official exhibition pages: {by_year.get('2024', 0)}",
        "",
        "## Successful Downloads",
    ]
    for r in results:
        if r.get("ok"):
            report_lines.append(
                f"- {r['meta'].year} {r['meta'].code}: {r['title']} -> {r['path'].name} "
                f"({r['images']} pages)"
            )

    report_lines += ["", "## Failed Attempts"]
    if failed:
        for r in failed:
            report_lines.append(
                f"- {r['meta'].year} {r['meta'].code}: {r['title']} -> {r['reason']}"
            )
    else:
        report_lines.append("- None")

    report_lines += [
        "",
        "## Notes",
        "- The official list pages are rendered in a browser; the downloader uses Playwright to collect links.",
        "- Detail pages expose page images rather than direct PDF attachments, so the script rebuilds PDFs from the images.",
        "- The `front/contents` API probe returned either 404 or empty results for these exhibition pages, so it was not used.",
    ]

    report = PAPERS_DIR / "_DOWNLOAD_REPORT.md"
    report.write_text("\n".join(report_lines), encoding="utf-8")
    return report


def main() -> int:
    PAPERS_DIR.mkdir(parents=True, exist_ok=True)

    metas = asyncio.run(collect_list_links())
    print(f"Collected {len(metas)} official paper links")
    if not metas:
        print("No official papers found")
        return 1

    results: list[dict] = []
    failed: list[dict] = []

    for idx, meta in enumerate(metas, 1):
        out_name = make_output_name(meta)
        out_path = PAPERS_DIR / out_name
        if out_path.exists() and out_path.stat().st_size > 0:
            results.append({
                "meta": meta,
                "title": meta.title,
                "ok": True,
                "path": out_path,
                "images": 0,
                "skipped": True,
            })
            print(f"[{idx}/{len(metas)}] skip {out_name}")
            continue

        print(f"[{idx}/{len(metas)}] downloading {meta.year} {meta.code}")
        try:
            res = process_paper(meta)
            if res.get("ok"):
                results.append(res)
                print(f"  saved {res['path'].name} ({res['images']} pages)")
            else:
                failed.append(res)
                print(f"  failed: {res['reason']}")
        except Exception as exc:
            failed.append({"meta": meta, "title": meta.title, "ok": False, "reason": str(exc)})
            print(f"  failed: {exc}")

    report = write_report(results, failed)

    pdf_count = sum(1 for _ in PAPERS_DIR.glob("*.pdf"))
    print(f"PDF count in target dir: {pdf_count}")
    print(f"Report written to: {report}")
    print(f"Successful downloads: {sum(1 for r in results if r.get('ok'))}")
    print(f"Failed downloads: {len(failed)}")
    return 0 if results else 1


if __name__ == "__main__":
    raise SystemExit(main())
