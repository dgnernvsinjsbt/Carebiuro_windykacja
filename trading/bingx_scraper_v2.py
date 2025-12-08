#!/usr/bin/env python3
"""
BingX API Documentation Scraper v2
Optimized version with direct section navigation.

Usage:
    pip install playwright pandas
    playwright install chromium
    python bingx_scraper_v2.py
"""

import asyncio
import json
import csv
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from playwright.async_api import async_playwright, Page


class BingXScraper:
    """Optimized BingX API scraper."""

    BASE_URL = "https://bingx-api.github.io/docs/"
    OUTPUT_DIR = Path("bingx_docs_output")

    # Known sidebar sections that contain API endpoints
    API_SECTIONS = [
        "interface",
        "Market Data",
        "Account Endpoints",
        "Trades Endpoints",
        "Socket API Reference",
        "General Info",
        "Authentication"
    ]

    def __init__(self):
        self.OUTPUT_DIR.mkdir(exist_ok=True)
        self.all_endpoints = []
        self.all_data = {"categories": [], "scraped_at": datetime.now().isoformat()}

    def log(self, msg: str):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    async def run(self):
        """Main scraping routine."""
        self.log("Starting BingX API scraper v2...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            page.set_default_timeout(30000)
            await page.set_viewport_size({"width": 1920, "height": 1080})

            # Navigate to main page
            self.log("Loading documentation site...")
            await page.goto(self.BASE_URL, wait_until="networkidle")
            await asyncio.sleep(2)

            # Get top tabs
            top_tabs = await page.evaluate("""
                () => {
                    const tabs = [];
                    document.querySelectorAll('header a, nav a, [class*="menu"] > *').forEach(el => {
                        const text = el.innerText?.trim();
                        if (text && text.length > 3 && text.length < 30 &&
                            !text.includes('Subscribe') && !text.includes('English')) {
                            tabs.push(text);
                        }
                    });
                    return [...new Set(tabs)];
                }
            """)

            self.log(f"Found top tabs: {top_tabs[:8]}")

            # Target categories
            categories = ["USDT-M Perp Futures", "Spot", "Standard Futures", "Copy Trading"]

            for cat in categories:
                self.log(f"\n=== Processing: {cat} ===")
                cat_data = await self.scrape_category(page, cat)
                self.all_data["categories"].append(cat_data)

            await browser.close()

        # Save results
        self.save_results()
        self.print_summary()

    async def scrape_category(self, page: Page, category: str) -> Dict:
        """Scrape a single category."""
        cat_data = {
            "name": category,
            "sections": [],
            "total_endpoints": 0
        }

        try:
            # Click category tab
            clicked = await page.evaluate(f"""
                (cat) => {{
                    const els = document.querySelectorAll('header a, nav a, [class*="menu"] > *');
                    for (const el of els) {{
                        if (el.innerText?.trim().includes(cat)) {{
                            el.click();
                            return true;
                        }}
                    }}
                    return false;
                }}
            """, category)

            if not clicked:
                self.log(f"  Could not click on {category}")
                return cat_data

            await asyncio.sleep(2)

            # Get sidebar sections
            sidebar = await page.evaluate("""
                () => {
                    const items = [];
                    document.querySelectorAll('aside a, [class*="sidebar"] a, [class*="menu-item"]').forEach(el => {
                        const text = el.innerText?.trim();
                        if (text && text.length > 2 && text.length < 50) {
                            items.push(text);
                        }
                    });
                    return [...new Set(items)];
                }
            """)

            self.log(f"  Sidebar sections: {sidebar}")

            # Scrape each relevant section
            for section in sidebar:
                if any(api_section.lower() in section.lower() for api_section in self.API_SECTIONS):
                    section_data = await self.scrape_section(page, section, category)
                    cat_data["sections"].append(section_data)
                    cat_data["total_endpoints"] += len(section_data.get("endpoints", []))

        except Exception as e:
            self.log(f"  Error in {category}: {e}")

        return cat_data

    async def scrape_section(self, page: Page, section: str, category: str) -> Dict:
        """Scrape a single section."""
        section_data = {
            "name": section,
            "category": category,
            "endpoints": []
        }

        try:
            # Click section
            await page.evaluate(f"""
                (section) => {{
                    const els = document.querySelectorAll('aside a, [class*="sidebar"] a');
                    for (const el of els) {{
                        if (el.innerText?.trim() === section) {{
                            el.click();
                            return true;
                        }}
                    }}
                    return false;
                }}
            """, section)

            await asyncio.sleep(1.5)

            # Scroll to load all content
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(0.5)
            await page.evaluate("window.scrollTo(0, 0)")

            # Extract endpoints
            endpoints = await page.evaluate("""
                () => {
                    const endpoints = [];
                    const content = document.body.innerText;

                    // Find API paths and methods
                    const patterns = [
                        /(GET|POST|PUT|DELETE)\\s+(\\/openApi\\/[\\w\\/-{}]+)/gi,
                        /(GET|POST|PUT|DELETE)\\s+(\\/api\\/[\\w\\/-{}]+)/gi,
                        /https?:\\/\\/[\\w.-]+(\\/openApi\\/[\\w\\/-{}?]+)/gi
                    ];

                    const seen = new Set();
                    patterns.forEach(pattern => {
                        let match;
                        const text = content;
                        while ((match = pattern.exec(text)) !== null) {
                            const method = match[1]?.toUpperCase() || '';
                            const path = match[2] || match[1];
                            const key = `${method}:${path}`;
                            if (!seen.has(key) && path.startsWith('/')) {
                                seen.add(key);
                                endpoints.push({ method, path });
                            }
                        }
                    });

                    // Also extract from tables
                    document.querySelectorAll('table').forEach(table => {
                        const text = table.innerText;
                        if (text.includes('/openApi') || text.includes('/api/')) {
                            const rows = table.querySelectorAll('tr');
                            rows.forEach(row => {
                                const cells = Array.from(row.querySelectorAll('td, th'));
                                cells.forEach(cell => {
                                    const cellText = cell.innerText;
                                    const pathMatch = cellText.match(/(\\/openApi\\/[\\w\\/-{}]+|\\/api\\/[\\w\\/-{}]+)/);
                                    if (pathMatch && !seen.has(pathMatch[1])) {
                                        seen.add(pathMatch[1]);
                                        endpoints.push({ method: '', path: pathMatch[1] });
                                    }
                                });
                            });
                        }
                    });

                    // Extract endpoint details from headings
                    document.querySelectorAll('h1, h2, h3, h4').forEach(heading => {
                        const text = heading.innerText || '';
                        const methodMatch = text.match(/\\b(GET|POST|PUT|DELETE)\\b/i);
                        const pathMatch = text.match(/(\\/[\\w\\/-{}]+)/);

                        if ((methodMatch || pathMatch) && !seen.has(text)) {
                            // Get following content
                            let description = '';
                            let params = [];
                            let sibling = heading.nextElementSibling;

                            while (sibling && !sibling.matches('h1, h2, h3')) {
                                if (sibling.matches('p') && !description) {
                                    description = sibling.innerText?.substring(0, 500) || '';
                                }
                                if (sibling.matches('table')) {
                                    const rows = sibling.querySelectorAll('tbody tr');
                                    rows.forEach(row => {
                                        const cells = Array.from(row.querySelectorAll('td')).map(c => c.innerText?.trim());
                                        if (cells.length >= 2) {
                                            params.push({
                                                name: cells[0] || '',
                                                type: cells[1] || '',
                                                required: cells[2] || '',
                                                desc: cells[3] || cells[2] || ''
                                            });
                                        }
                                    });
                                }
                                sibling = sibling.nextElementSibling;
                            }

                            const ep = {
                                title: text.trim(),
                                method: methodMatch ? methodMatch[1].toUpperCase() : '',
                                path: pathMatch ? pathMatch[1] : '',
                                description: description,
                                parameters: params
                            };

                            if (ep.method || ep.path) {
                                endpoints.push(ep);
                            }
                        }
                    });

                    return endpoints;
                }
            """)

            # Deduplicate
            seen = set()
            unique = []
            for ep in endpoints:
                key = f"{ep.get('method', '')}:{ep.get('path', '')}"
                if key not in seen and ep.get('path'):
                    seen.add(key)
                    ep['category'] = category
                    ep['section'] = section
                    unique.append(ep)
                    self.all_endpoints.append(ep)

            section_data["endpoints"] = unique
            self.log(f"    {section}: {len(unique)} endpoints")

        except Exception as e:
            self.log(f"    Error in {section}: {e}")

        return section_data

    def save_results(self):
        """Save all results to files."""
        # Main JSON
        with open(self.OUTPUT_DIR / "bingx_api_docs.json", 'w') as f:
            json.dump(self.all_data, f, indent=2, default=str)
        self.log(f"\nSaved: {self.OUTPUT_DIR}/bingx_api_docs.json")

        # CSV
        if self.all_endpoints:
            with open(self.OUTPUT_DIR / "bingx_all_endpoints.csv", 'w', newline='') as f:
                fields = ['category', 'section', 'method', 'path', 'title', 'description']
                writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(self.all_endpoints)
            self.log(f"Saved: {self.OUTPUT_DIR}/bingx_all_endpoints.csv")

        # Summary
        summary = {
            "total_categories": len(self.all_data["categories"]),
            "total_endpoints": len(self.all_endpoints),
            "by_category": {},
            "by_method": {}
        }

        for ep in self.all_endpoints:
            cat = ep.get('category', 'Unknown')
            method = ep.get('method', 'UNKNOWN') or 'UNKNOWN'
            summary["by_category"][cat] = summary["by_category"].get(cat, 0) + 1
            summary["by_method"][method] = summary["by_method"].get(method, 0) + 1

        with open(self.OUTPUT_DIR / "bingx_summary.json", 'w') as f:
            json.dump(summary, f, indent=2)
        self.log(f"Saved: {self.OUTPUT_DIR}/bingx_summary.json")

    def print_summary(self):
        """Print final summary."""
        print("\n" + "=" * 60)
        print("SCRAPING COMPLETE")
        print("=" * 60)
        print(f"Total endpoints found: {len(self.all_endpoints)}")

        by_cat = {}
        by_method = {}
        for ep in self.all_endpoints:
            cat = ep.get('category', 'Unknown')
            method = ep.get('method', 'UNKNOWN') or 'UNKNOWN'
            by_cat[cat] = by_cat.get(cat, 0) + 1
            by_method[method] = by_method.get(method, 0) + 1

        print(f"\nBy category: {by_cat}")
        print(f"By method: {by_method}")
        print(f"\nOutput: {self.OUTPUT_DIR.absolute()}")


if __name__ == "__main__":
    scraper = BingXScraper()
    asyncio.run(scraper.run())
