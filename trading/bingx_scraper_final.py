#!/usr/bin/env python3
"""
BingX API Documentation Scraper - Final Production Version
Extracts all unique API endpoints with global deduplication.

Usage:
    pip install playwright pandas
    playwright install chromium
    python bingx_scraper_final.py
"""

import asyncio
import json
import csv
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright


class BingXScraperFinal:
    """Final production BingX API scraper with global deduplication."""

    BASE_URL = "https://bingx-api.github.io/docs/"
    V3_API_URL = "https://bingx-api.github.io/docs-v3/#/en/info"
    OUTPUT_DIR = Path("bingx_docs_output")

    # Direct URLs to specific API sections for better scraping
    DIRECT_URLS = {
        "USDT-M Perp Futures": "https://bingx-api.github.io/docs/#/en-us/swapV2/",
        "Spot": "https://bingx-api.github.io/docs/#/en-us/spot/",
        "Standard Futures": "https://bingx-api.github.io/docs/#/en-us/cswap/",
        "Copy Trading": "https://bingx-api.github.io/docs/#/en-us/copyTrading/",
    }

    API_SECTIONS = [
        "interface", "Market Data", "Account Endpoints", "Trades Endpoints",
        "Socket API Reference", "General Info", "Authentication",
        "Wallet deposits", "Account assets", "Standard Contract"
    ]

    def __init__(self):
        self.OUTPUT_DIR.mkdir(exist_ok=True)
        self.global_endpoints = {}  # path -> endpoint (global dedup)

    def log(self, msg: str):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    async def run(self):
        """Main scraping routine."""
        self.log("=" * 60)
        self.log("BingX API Documentation Scraper - Final")
        self.log("=" * 60)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            page.set_default_timeout(30000)
            await page.set_viewport_size({"width": 1920, "height": 1080})

            self.log("Loading documentation site...")
            await page.goto(self.BASE_URL, wait_until="networkidle")
            await asyncio.sleep(2)

            # Create screenshots directory and take screenshot of main page
            (self.OUTPUT_DIR / "screenshots").mkdir(exist_ok=True)
            await page.screenshot(path=str(self.OUTPUT_DIR / "screenshots" / "main_page.png"))

            # Focus on V3 API docs which have proper structure
            self.log("Loading V3 API documentation...")
            await page.goto(self.V3_API_URL, wait_until="networkidle")
            await asyncio.sleep(3)
            await page.screenshot(path=str(self.OUTPUT_DIR / "screenshots" / "v3_api.png"))

            # V3 docs have expandable sections - expand and scrape each
            v3_sections = ["swap", "spot", "cswap", "account-and-wallet", "agent", "copy-trade"]
            for section in v3_sections:
                self.log(f"  Expanding V3 section: {section}")
                endpoints = await self.scrape_v3_section(page, section)
                for ep in endpoints:
                    path = ep.get('path', '')
                    if path and path not in self.global_endpoints:
                        self.global_endpoints[path] = ep
                self.log(f"    Found {len(endpoints)} endpoints")

            self.log(f"  Total V3 endpoints: {len(self.global_endpoints)}")

            # Go back to main docs for additional scraping
            await page.goto(self.BASE_URL, wait_until="networkidle")
            await asyncio.sleep(2)

            categories = ["USDT-M Perp Futures", "Spot", "Standard Futures", "Copy Trading"]
            all_data = {"categories": [], "scraped_at": datetime.now().isoformat()}

            # Do comprehensive scan of each category
            for cat in categories:
                self.log(f"\n{'='*50}")
                self.log(f"Category: {cat}")
                self.log(f"{'='*50}")
                cat_data = await self.scrape_category(page, cat)
                all_data["categories"].append(cat_data)

            await browser.close()

        # Re-categorize endpoints by path structure
        self.recategorize_endpoints()
        self.save_results(all_data)

    async def scrape_v3_section(self, page, section: str) -> list:
        """Scrape a V3 API docs expandable section."""
        all_endpoints = []

        # Click to expand the section
        expanded = await page.evaluate("""
            (section) => {
                // Find and click the section to expand it
                const items = document.querySelectorAll('.sidebar-item, [class*="sidebar"] > div, nav li, aside li');
                for (const item of items) {
                    const text = item.innerText?.trim().toLowerCase();
                    if (text === section || text.includes(section)) {
                        item.click();
                        return true;
                    }
                }
                // Also try by data attributes or other selectors
                const byText = Array.from(document.querySelectorAll('*')).find(
                    el => el.innerText?.trim().toLowerCase() === section
                );
                if (byText) {
                    byText.click();
                    return true;
                }
                return false;
            }
        """, section)

        await asyncio.sleep(1.5)

        # Get all subsections that appeared after expanding
        subsections = await page.evaluate("""
            () => {
                const items = [];
                const seen = new Set();
                document.querySelectorAll('.sidebar-item a, [class*="sidebar"] a, nav a, aside a').forEach(el => {
                    const text = el.innerText?.trim();
                    const href = el.getAttribute('href') || '';
                    if (text && text.length > 2 && text.length < 80 && !seen.has(text)) {
                        seen.add(text);
                        items.push({ text, href });
                    }
                });
                return items;
            }
        """)

        # Click on each subsection and extract endpoints
        for sub in subsections[:20]:  # Limit to avoid too many clicks
            try:
                await page.evaluate("""
                    (subText) => {
                        const links = document.querySelectorAll('a');
                        for (const link of links) {
                            if (link.innerText?.trim() === subText) {
                                link.click();
                                return true;
                            }
                        }
                        return false;
                    }
                """, sub['text'])

                await asyncio.sleep(1)

                # Extract endpoints from current view
                endpoints = await self.extract_all_endpoints(page, section, sub['text'])
                all_endpoints.extend(endpoints)

            except Exception:
                pass

        return all_endpoints

    async def extract_all_endpoints(self, page, category: str, section: str) -> list:
        """Extract all endpoints from current page content."""
        # Scroll to load all content
        for i in range(10):
            await page.evaluate(f"window.scrollTo(0, {i * 800})")
            await asyncio.sleep(0.2)
        await page.evaluate("window.scrollTo(0, 0)")

        return await page.evaluate("""
            (args) => {
                const [category, section] = args;
                const endpoints = [];
                const seen = new Set();
                const content = document.body.innerText;

                // Pattern: METHOD /path
                const patterns = [
                    /(GET|POST|PUT|DELETE|PATCH)\\s+(\\/(?:openApi|api)\\/[\\w\\/-{}]+)/gi,
                    /(\\/openApi\\/[\\w]+\\/v[0-9]+\\/[\\w\\/-{}]+)/g,
                    /(\\/api\\/v[0-9]+\\/[\\w\\/-{}]+)/g
                ];

                for (const pattern of patterns) {
                    const matches = content.matchAll(pattern);
                    for (const m of matches) {
                        let method = '';
                        let path = '';
                        if (m[2]) {
                            method = m[1].toUpperCase();
                            path = m[2];
                        } else {
                            path = m[1];
                        }
                        path = path.split('?')[0];
                        if (!seen.has(path) && path.length > 10) {
                            seen.add(path);
                            endpoints.push({ method, path, category, section });
                        }
                    }
                }

                // Also check code blocks
                document.querySelectorAll('pre, code').forEach(el => {
                    const text = el.innerText || '';
                    const pathMatches = text.matchAll(/(\\/(?:openApi|api)\\/[\\w\\/-{}]+)/g);
                    for (const m of pathMatches) {
                        const path = m[1].split('?')[0];
                        if (!seen.has(path) && path.length > 10) {
                            seen.add(path);
                            const methodMatch = text.match(/(GET|POST|PUT|DELETE)/i);
                            endpoints.push({
                                method: methodMatch ? methodMatch[1].toUpperCase() : '',
                                path, category, section
                            });
                        }
                    }
                });

                return endpoints;
            }
        """, [category, section])

    def recategorize_endpoints(self):
        """Re-categorize endpoints based on their path structure."""
        for path, ep in self.global_endpoints.items():
            if '/spot/' in path:
                ep['category'] = 'Spot'
            elif '/swap/' in path:
                ep['category'] = 'USDT-M Perp Futures'
            elif '/cswap/' in path:
                ep['category'] = 'Standard Futures'
            elif '/copyTrading/' in path.lower():
                ep['category'] = 'Copy Trading'
            # Keep original category if no match

    async def scrape_category(self, page, category: str) -> dict:
        """Scrape a category with all its sections."""
        cat_data = {"name": category, "endpoints": [], "sections": []}

        try:
            # Navigate directly to category URL if available
            if category in self.DIRECT_URLS:
                url = self.DIRECT_URLS[category]
                self.log(f"  Navigating to: {url}")
                await page.goto(url, wait_until="networkidle")
                await asyncio.sleep(2)
            else:
                # Fall back to clicking tab
                clicked = await page.evaluate("""
                    (cat) => {
                        const els = document.querySelectorAll('header a, nav a, [class*="menu"] > *');
                        for (const el of els) {
                            if (el.innerText?.trim().includes(cat)) {
                                el.click();
                                return true;
                            }
                        }
                        return false;
                    }
                """, category)

                if not clicked:
                    self.log(f"  Could not click on {category}")
                    return cat_data

                await asyncio.sleep(2)

            # Take screenshot of category
            safe_name = category.replace(" ", "_").replace("-", "_")
            await page.screenshot(path=str(self.OUTPUT_DIR / "screenshots" / f"{safe_name}.png"))

            # Scroll to load all lazy content
            self.log(f"  Scrolling to load content...")
            for i in range(10):
                await page.evaluate(f"window.scrollTo(0, {i * 1000})")
                await asyncio.sleep(0.3)
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(0.5)

            # Get sidebar links using v2's working selector
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

            # Filter to relevant API sections (exclude non-API sections)
            skip_sections = ['Introduction', 'Change Log', 'FAQ', 'Frequently Asked Questions']
            relevant = [s for s in sidebar if any(k.lower() in s.lower() for k in self.API_SECTIONS)
                       and s not in skip_sections]
            cat_data["sections"] = relevant
            self.log(f"  Sections: {relevant}")

            # Scrape each section by clicking into it
            for section in relevant:
                self.log(f"    Clicking section: {section}")
                endpoints = await self.scrape_section(page, category, section)

                # Add only new endpoints (global dedup)
                new_count = 0
                for ep in endpoints:
                    path = ep.get('path', '')
                    if path and path not in self.global_endpoints:
                        self.global_endpoints[path] = ep
                        cat_data["endpoints"].append(ep)
                        new_count += 1

                if new_count > 0:
                    self.log(f"    {section}: +{new_count} new endpoints")

                await asyncio.sleep(1)

            self.log(f"  Category total: {len(cat_data['endpoints'])} unique endpoints")

        except Exception as e:
            self.log(f"  Error: {e}")

        return cat_data

    async def scrape_section(self, page, category: str, section: str) -> list:
        """Scrape a single section."""
        # Get the href of the section link
        href = await page.evaluate("""
            (section) => {
                const selectors = [
                    'aside a', '[class*="sidebar"] a', '[class*="menu"] a',
                    '.sidebar-item', '.el-menu-item'
                ];
                for (const sel of selectors) {
                    const els = document.querySelectorAll(sel);
                    for (const el of els) {
                        const text = el.innerText?.trim();
                        if (text === section || text.includes(section)) {
                            // Return href for direct navigation
                            const href = el.getAttribute('href');
                            el.click();
                            return href;
                        }
                    }
                }
                return null;
            }
        """, section)

        await asyncio.sleep(2)  # Wait for navigation/scroll

        # Get current URL to track navigation
        current_url = page.url

        # Scroll through the content area to load lazy content
        for i in range(8):
            await page.evaluate(f"window.scrollTo(0, {i * 600})")
            await asyncio.sleep(0.2)
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(0.3)

        # Debug: Save HTML for analysis on first section of each category
        if section in ['Market Data', 'Trades Endpoints']:
            html = await page.content()
            safe_cat = category.replace(" ", "_").replace("-", "_")
            safe_sec = section.replace(" ", "_")
            with open(self.OUTPUT_DIR / f"debug_{safe_cat}_{safe_sec}.html", 'w') as f:
                f.write(html)

        # Extract endpoints with enhanced patterns - focus on main content area
        return await page.evaluate("""
            (args) => {
                const [category, section] = args;
                const endpoints = [];
                const seen = new Set();

                // Try to get content from main content area first
                const contentAreas = document.querySelectorAll(
                    'main, .content, .main-content, [class*="content"], article, .markdown-body'
                );
                let content = '';
                if (contentAreas.length > 0) {
                    contentAreas.forEach(area => content += area.innerText + ' ');
                } else {
                    content = document.body.innerText;
                }

                // Pattern 1: METHOD /path (various formats)
                const methodPatterns = [
                    /(GET|POST|PUT|DELETE|PATCH)\\s+(\\/(?:openApi|api)\\/[\\w\\/-{}]+)/gi,
                    /(GET|POST|PUT|DELETE|PATCH)\\s+(https?:\\/\\/[^\\s]+\\/(?:openApi|api)\\/[\\w\\/-{}]+)/gi
                ];

                for (const pattern of methodPatterns) {
                    const matches = content.matchAll(pattern);
                    for (const m of matches) {
                        let path = m[2];
                        // Extract path from full URL if present
                        if (path.includes('http')) {
                            const urlMatch = path.match(/(\\/(?:openApi|api)\\/[\\w\\/-{}]+)/);
                            if (urlMatch) path = urlMatch[1];
                        }
                        path = path.split('?')[0]; // Remove query params
                        if (!seen.has(path) && path.length > 8) {
                            seen.add(path);
                            endpoints.push({ method: m[1].toUpperCase(), path, category, section });
                        }
                    }
                }

                // Pattern 2: Paths in code blocks and tables
                const elements = document.querySelectorAll('pre, code, td, th, p, li, span');
                elements.forEach(el => {
                    const text = el.innerText || '';
                    // Match API paths
                    const pathPatterns = [
                        /(\\/openApi\\/[\\w]+\\/v[0-9]+\\/[\\w\\/-{}]+)/g,
                        /(\\/api\\/v[0-9]+\\/[\\w\\/-{}]+)/g,
                        /(\\/openApi\\/[\\w\\/-{}]+)/g
                    ];

                    for (const pattern of pathPatterns) {
                        const matches = text.matchAll(pattern);
                        for (const m of matches) {
                            const path = m[1].split('?')[0];
                            if (!seen.has(path) && path.length > 10 && !path.includes('example')) {
                                seen.add(path);
                                // Try to find method in nearby text
                                const methodMatch = text.match(/\\b(GET|POST|PUT|DELETE|PATCH)\\b/i);
                                endpoints.push({
                                    method: methodMatch ? methodMatch[1].toUpperCase() : '',
                                    path, category, section
                                });
                            }
                        }
                    }
                });

                // Pattern 3: Look for paths in href attributes
                document.querySelectorAll('a[href*="openApi"], a[href*="/api/"]').forEach(a => {
                    const href = a.getAttribute('href') || '';
                    const pathMatch = href.match(/(\\/(?:openApi|api)\\/[\\w\\/-{}]+)/);
                    if (pathMatch && !seen.has(pathMatch[1])) {
                        seen.add(pathMatch[1]);
                        endpoints.push({ method: '', path: pathMatch[1], category, section });
                    }
                });

                return endpoints;
            }
        """, [category, section])

    def save_results(self, all_data: dict):
        """Save all results."""
        endpoints = list(self.global_endpoints.values())
        all_data["total_unique_endpoints"] = len(endpoints)

        # JSON
        with open(self.OUTPUT_DIR / "bingx_api_docs.json", 'w') as f:
            json.dump(all_data, f, indent=2, default=str)

        # CSV
        if endpoints:
            with open(self.OUTPUT_DIR / "bingx_all_endpoints.csv", 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['category', 'section', 'method', 'path'], extrasaction='ignore')
                writer.writeheader()
                writer.writerows(endpoints)

        # Summary
        by_method = {}
        by_category = {}
        for ep in endpoints:
            m = ep.get('method', '') or 'UNKNOWN'
            c = ep.get('category', 'Unknown')
            by_method[m] = by_method.get(m, 0) + 1
            by_category[c] = by_category.get(c, 0) + 1

        summary = {
            "total_unique_endpoints": len(endpoints),
            "by_method": by_method,
            "by_category": by_category,
            "scraped_at": datetime.now().isoformat()
        }
        with open(self.OUTPUT_DIR / "bingx_summary.json", 'w') as f:
            json.dump(summary, f, indent=2)

        # Print summary
        print("\n" + "=" * 60)
        print("SCRAPING COMPLETE")
        print("=" * 60)
        print(f"Total unique endpoints: {len(endpoints)}")
        print(f"\nBy category: {by_category}")
        print(f"By method: {by_method}")
        print(f"\nOutput: {self.OUTPUT_DIR.absolute()}")


if __name__ == "__main__":
    asyncio.run(BingXScraperFinal().run())
