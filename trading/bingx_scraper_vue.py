#!/usr/bin/env python3
"""
BingX API Documentation Scraper - Vue.js Optimized
Handles Vue.js SPA with proper content detection and detailed extraction.
"""

import asyncio
import json
import csv
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright


class BingXVueScraper:
    """Vue.js-aware BingX API scraper with detailed endpoint extraction."""

    BASE_URL = "https://bingx-api.github.io/docs/"
    OUTPUT_DIR = Path("bingx_docs_output")

    DIRECT_URLS = {
        "USDT-M Perp Futures": "https://bingx-api.github.io/docs/#/en-us/swapV2/",
        "Spot": "https://bingx-api.github.io/docs/#/en-us/spot/",
        "Standard Futures": "https://bingx-api.github.io/docs/#/en-us/cswap/",
        "Copy Trading": "https://bingx-api.github.io/docs/#/en-us/copyTrading/",
    }

    def __init__(self):
        self.OUTPUT_DIR.mkdir(exist_ok=True)
        (self.OUTPUT_DIR / "screenshots").mkdir(exist_ok=True)
        self.global_endpoints = {}

    def log(self, msg: str):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    async def run(self):
        """Main scraping routine with Vue.js handling."""
        self.log("=" * 60)
        self.log("BingX API Scraper - Vue.js Optimized")
        self.log("=" * 60)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, slow_mo=50)  # Headless for CI/Codespaces
            page = await browser.new_page()
            page.set_default_timeout(45000)  # Longer timeout for Vue
            await page.set_viewport_size({"width": 1920, "height": 1080})

            categories = list(self.DIRECT_URLS.keys())
            all_data = {"categories": [], "scraped_at": datetime.now().isoformat()}

            for cat in categories:
                self.log(f"\n{'='*50}")
                self.log(f"Category: {cat}")
                self.log(f"{'='*50}")
                cat_data = await self.scrape_category(page, cat)
                all_data["categories"].append(cat_data)

            await browser.close()

        self.recategorize_endpoints()
        self.save_results(all_data)

    async def scrape_category(self, page, category: str) -> dict:
        """Scrape a category with Vue-aware content detection."""
        cat_data = {"name": category, "endpoints": [], "sections": []}

        try:
            # Navigate to category URL
            url = self.DIRECT_URLS[category]
            self.log(f"  Navigating to: {url}")
            await page.goto(url, wait_until="domcontentloaded")

            # Wait for Vue to initialize and render
            await asyncio.sleep(3)

            # Wait for sidebar to be populated
            await page.wait_for_selector('aside, .sidebar, [class*="sidebar"]', timeout=10000)

            # Take screenshot
            safe_name = category.replace(" ", "_").replace("-", "_")
            await page.screenshot(path=str(self.OUTPUT_DIR / "screenshots" / f"{safe_name}_init.png"))

            # Get all sidebar sections
            sidebar = await page.evaluate("""
                () => {
                    const items = [];
                    const links = document.querySelectorAll('aside a, .sidebar a, [class*="sidebar"] a');
                    links.forEach(el => {
                        const text = el.innerText?.trim();
                        const href = el.getAttribute('href') || '';
                        if (text && text.length > 2 && text.length < 60) {
                            items.push({ text, href });
                        }
                    });
                    return items;
                }
            """)

            self.log(f"  Found {len(sidebar)} sidebar items")

            # Filter to API documentation sections
            skip = ['Introduction', 'Change Log', 'FAQ', 'Frequently Asked Questions', 'quickStart']
            relevant = [s for s in sidebar if s['text'] not in skip and
                       any(x in s['text'].lower() for x in ['api', 'endpoint', 'market', 'trade', 'account', 'socket', 'interface'])]

            self.log(f"  Relevant sections: {[s['text'] for s in relevant]}")
            cat_data["sections"] = [s['text'] for s in relevant]

            # Scrape each section
            for section_info in relevant:
                section = section_info['text']
                self.log(f"    Processing: {section}")
                endpoints = await self.scrape_section_vue(page, category, section, section_info['href'])

                new_count = 0
                for ep in endpoints:
                    path = ep.get('path', '')
                    if path and path not in self.global_endpoints:
                        self.global_endpoints[path] = ep
                        cat_data["endpoints"].append(ep)
                        new_count += 1

                if new_count > 0:
                    self.log(f"      +{new_count} new endpoints")

                await asyncio.sleep(0.5)

            self.log(f"  Category total: {len(cat_data['endpoints'])} endpoints")

        except Exception as e:
            self.log(f"  Error: {e}")
            import traceback
            traceback.print_exc()

        return cat_data

    async def scrape_section_vue(self, page, category: str, section: str, href: str) -> list:
        """Scrape a section with Vue content detection."""

        # Click the sidebar link
        clicked = await page.evaluate("""
            (section) => {
                const links = document.querySelectorAll('aside a, .sidebar a');
                for (const link of links) {
                    if (link.innerText?.trim() === section) {
                        link.click();
                        return true;
                    }
                }
                return false;
            }
        """, section)

        if not clicked:
            self.log(f"      Could not click: {section}")
            return []

        # Wait for Vue to render new content
        await asyncio.sleep(2)

        # Check if content changed from "Change Log"
        page_title = await page.evaluate("""
            () => {
                const title = document.querySelector('h1, .page-content-title, [class*="title"]');
                return title ? title.innerText.trim() : '';
            }
        """)

        if "Change Log" in page_title:
            self.log(f"      Still on Change Log for: {section}")
            # Try waiting longer
            await asyncio.sleep(3)

        # Scroll to load all content
        for i in range(12):
            await page.evaluate(f"window.scrollTo(0, {i * 1000})")
            await asyncio.sleep(0.4)
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(0.5)

        # Extract detailed endpoint information
        endpoints = await page.evaluate("""
            (args) => {
                const [category, section] = args;
                const endpoints = [];
                const seen = new Set();

                // Get main content area
                const contentArea = document.querySelector('main, .main-content, .content, [class*="content-wrap"]');
                if (!contentArea) return [];

                const fullText = contentArea.innerText || '';

                // Look for API endpoint cards/sections
                // Pattern 1: Headers followed by endpoint info
                const headers = contentArea.querySelectorAll('h2, h3, h4, .api-title');
                headers.forEach(header => {
                    const headerText = header.innerText || '';

                    // Check if this looks like an endpoint header
                    if (headerText.match(/\\b(POST|GET|PUT|DELETE|PATCH)\\b/i)) {
                        let method = '';
                        let path = '';

                        // Extract method
                        const methodMatch = headerText.match(/\\b(POST|GET|PUT|DELETE|PATCH)\\b/i);
                        if (methodMatch) method = methodMatch[1].toUpperCase();

                        // Extract path
                        const pathMatch = headerText.match(/(\\/(?:openApi|api)\\/[\\w\\/-{}]+)/);
                        if (pathMatch) path = pathMatch[1];

                        if (path && !seen.has(path)) {
                            seen.add(path);

                            // Get description from following paragraphs
                            let description = '';
                            let nextEl = header.nextElementSibling;
                            let attempts = 0;
                            while (nextEl && attempts < 3) {
                                if (nextEl.tagName === 'P') {
                                    description += nextEl.innerText + ' ';
                                    break;
                                }
                                nextEl = nextEl.nextElementSibling;
                                attempts++;
                            }

                            endpoints.push({
                                method,
                                path,
                                category,
                                section,
                                description: description.trim().substring(0, 200)
                            });
                        }
                    }
                });

                // Pattern 2: Code blocks with endpoints
                const codeBlocks = contentArea.querySelectorAll('pre, code, .code-block');
                codeBlocks.forEach(block => {
                    const text = block.innerText || '';

                    // Match METHOD /path patterns
                    const matches = text.matchAll(/(GET|POST|PUT|DELETE|PATCH)\\s+(\\/(?:openApi|api)\\/[\\w\\/-{}]+)/gi);
                    for (const m of matches) {
                        const path = m[2].split('?')[0];
                        if (!seen.has(path) && path.length > 10) {
                            seen.add(path);
                            endpoints.push({
                                method: m[1].toUpperCase(),
                                path,
                                category,
                                section,
                                description: ''
                            });
                        }
                    }

                    // Also match standalone paths
                    const pathMatches = text.matchAll(/(\\/openApi\\/[\\w]+\\/v[0-9]+\\/[\\w\\/-{}]+)/g);
                    for (const m of pathMatches) {
                        const path = m[1].split('?')[0];
                        if (!seen.has(path) && path.length > 10) {
                            seen.add(path);
                            endpoints.push({
                                method: '',
                                path,
                                category,
                                section,
                                description: ''
                            });
                        }
                    }
                });

                // Pattern 3: Tables with endpoint information
                const tables = contentArea.querySelectorAll('table');
                tables.forEach(table => {
                    const rows = table.querySelectorAll('tr');
                    rows.forEach(row => {
                        const cells = row.querySelectorAll('td, th');
                        let method = '';
                        let path = '';
                        let desc = '';

                        cells.forEach((cell, idx) => {
                            const text = cell.innerText || '';
                            if (text.match(/^(GET|POST|PUT|DELETE|PATCH)$/i)) {
                                method = text.toUpperCase();
                            }
                            if (text.match(/^\\/(?:openApi|api)\\//)) {
                                path = text.split('?')[0];
                            }
                            if (idx > 1 && text.length > 5 && text.length < 150) {
                                desc = text;
                            }
                        });

                        if (path && !seen.has(path)) {
                            seen.add(path);
                            endpoints.push({ method, path, category, section, description: desc });
                        }
                    });
                });

                return endpoints;
            }
        """, [category, section])

        return endpoints

    def recategorize_endpoints(self):
        """Re-categorize endpoints based on path structure."""
        for path, ep in self.global_endpoints.items():
            if '/spot/' in path:
                ep['category'] = 'Spot'
            elif '/swap/' in path:
                ep['category'] = 'USDT-M Perp Futures'
            elif '/cswap/' in path:
                ep['category'] = 'Standard Futures'
            elif '/copyTrading/' in path.lower():
                ep['category'] = 'Copy Trading'
            elif '/account/' in path.lower() or '/capital/' in path.lower():
                ep['category'] = 'Account & Wallet'

    def save_results(self, all_data: dict):
        """Save results to JSON and CSV."""
        endpoints = list(self.global_endpoints.values())

        # Save full JSON
        with open(self.OUTPUT_DIR / "bingx_api_docs_vue.json", 'w') as f:
            json.dump(all_data, f, indent=2)

        # Save CSV
        with open(self.OUTPUT_DIR / "bingx_endpoints_vue.csv", 'w', newline='') as f:
            if endpoints:
                writer = csv.DictWriter(f, fieldnames=['category', 'section', 'method', 'path', 'description'])
                writer.writeheader()
                for ep in endpoints:
                    writer.writerow(ep)

        # Save summary
        by_cat = {}
        by_method = {}
        for ep in endpoints:
            cat = ep.get('category', 'Unknown')
            method = ep.get('method', 'UNKNOWN')
            by_cat[cat] = by_cat.get(cat, 0) + 1
            by_method[method] = by_method.get(method, 0) + 1

        summary = {
            "total_unique_endpoints": len(endpoints),
            "by_method": by_method,
            "by_category": by_cat,
            "scraped_at": all_data["scraped_at"]
        }

        with open(self.OUTPUT_DIR / "bingx_summary_vue.json", 'w') as f:
            json.dump(summary, f, indent=2)

        self.log("\n" + "=" * 60)
        self.log("SCRAPING COMPLETE")
        self.log("=" * 60)
        self.log(f"Total unique endpoints: {len(endpoints)}")
        self.log(f"\nBy category: {by_cat}")
        self.log(f"By method: {by_method}")
        self.log(f"\nOutput: {self.OUTPUT_DIR}")


if __name__ == "__main__":
    scraper = BingXVueScraper()
    asyncio.run(scraper.run())
