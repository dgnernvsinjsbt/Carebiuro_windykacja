#!/usr/bin/env python3
"""
BingX API Documentation Scraper
Production-ready Playwright script to crawl and extract API docs from BingX SPA.

Usage:
    pip install playwright pandas
    playwright install chromium
    python bingx_scraper.py [--debug] [--headed]
"""

import asyncio
import json
import csv
import re
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeout


class BingXAPIScraper:
    """Scraper for BingX API documentation SPA."""

    BASE_URL = "https://bingx-api.github.io/docs/"
    OUTPUT_DIR = Path("bingx_docs_output")
    SCREENSHOT_DIR = OUTPUT_DIR / "screenshots"

    # Rate limiting
    PAGE_DELAY = 2.0  # seconds between pages
    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 5.0

    # Timeouts
    NAVIGATION_TIMEOUT = 30000  # 30s
    SELECTOR_TIMEOUT = 10000   # 10s

    def __init__(self, debug: bool = False, headed: bool = False):
        self.debug = debug
        self.headed = headed
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.all_endpoints = []
        self.categories = {}
        self.errors = []

        # Create output directories
        self.OUTPUT_DIR.mkdir(exist_ok=True)
        self.SCREENSHOT_DIR.mkdir(exist_ok=True)

    def log(self, message: str, level: str = "INFO"):
        """Log messages with timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    async def init_browser(self):
        """Initialize Playwright browser."""
        self.log("Initializing browser...")
        playwright = await async_playwright().start()

        self.browser = await playwright.chromium.launch(
            headless=not self.headed,
            slow_mo=100 if self.debug else 0
        )

        self.page = await self.browser.new_page()
        self.page.set_default_timeout(self.NAVIGATION_TIMEOUT)

        # Set viewport
        await self.page.set_viewport_size({"width": 1920, "height": 1080})

        self.log("Browser initialized successfully")

    async def close_browser(self):
        """Close browser and cleanup."""
        if self.browser:
            await self.browser.close()
            self.log("Browser closed")

    async def navigate_with_retry(self, url: str) -> bool:
        """Navigate to URL with retry logic."""
        for attempt in range(self.RETRY_ATTEMPTS):
            try:
                self.log(f"Navigating to: {url} (attempt {attempt + 1})")
                await self.page.goto(url, wait_until="networkidle", timeout=self.NAVIGATION_TIMEOUT)
                await asyncio.sleep(1.5)  # Extra wait for SPA rendering
                return True
            except PlaywrightTimeout:
                self.log(f"Timeout on attempt {attempt + 1}", "WARN")
                if attempt < self.RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(self.RETRY_DELAY)
            except Exception as e:
                self.log(f"Error navigating: {e}", "ERROR")
                if attempt < self.RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(self.RETRY_DELAY)

        return False

    async def get_top_nav_tabs(self) -> List[Dict]:
        """Get all top navigation tabs (product categories)."""
        self.log("Getting top navigation tabs...")

        tabs = await self.page.evaluate("""
            () => {
                const tabs = [];
                // Look for top nav items
                document.querySelectorAll('.el-menu-item, .el-tabs__item, nav a, header a, [role="tab"]').forEach(el => {
                    const text = el.innerText?.trim();
                    const href = el.getAttribute('href') || '';
                    if (text && text.length > 0 && text.length < 50) {
                        tabs.push({ text, href, tag: el.tagName });
                    }
                });
                return tabs;
            }
        """)

        self.log(f"Found {len(tabs)} top nav tabs")
        return tabs

    async def get_sidebar_links(self) -> List[Dict]:
        """Get all sidebar navigation links."""
        self.log("Getting sidebar links...")

        links = await self.page.evaluate("""
            () => {
                const links = [];
                const seen = new Set();

                // Multiple selectors for sidebar
                const selectors = [
                    '.sidebar-item',
                    '.sidebar a',
                    '.el-menu-item',
                    '.sidebar-link',
                    '[class*="sidebar"] a',
                    '[class*="menu"] a',
                    'aside a',
                    'nav.sidebar a'
                ];

                selectors.forEach(selector => {
                    document.querySelectorAll(selector).forEach(el => {
                        const text = el.innerText?.trim();
                        if (text && !seen.has(text) && text.length < 100) {
                            seen.add(text);
                            links.push({
                                text: text,
                                href: el.getAttribute('href') || '',
                                className: el.className || ''
                            });
                        }
                    });
                });

                return links;
            }
        """)

        self.log(f"Found {len(links)} sidebar links")
        return links

    async def click_sidebar_item(self, text: str) -> bool:
        """Click a sidebar item by its text."""
        try:
            # Try multiple approaches to click
            clicked = await self.page.evaluate(f"""
                (targetText) => {{
                    const elements = document.querySelectorAll('aside a, .sidebar a, .sidebar-item, [class*="sidebar"] a, [class*="menu"] a');
                    for (const el of elements) {{
                        if (el.innerText?.trim() === targetText) {{
                            el.click();
                            return true;
                        }}
                    }}
                    return false;
                }}
            """, text)

            if clicked:
                await asyncio.sleep(1.5)  # Wait for content to load
                return True

            # Fallback: try using Playwright's click
            locator = self.page.get_by_text(text, exact=True)
            if await locator.count() > 0:
                await locator.first.click()
                await asyncio.sleep(1.5)
                return True

        except Exception as e:
            self.log(f"Error clicking sidebar item '{text}': {e}", "WARN")

        return False

    async def click_top_tab(self, text: str) -> bool:
        """Click a top navigation tab by its text."""
        try:
            clicked = await self.page.evaluate(f"""
                (targetText) => {{
                    const elements = document.querySelectorAll('.el-menu-item, .el-tabs__item, nav a, header a, [role="tab"]');
                    for (const el of elements) {{
                        if (el.innerText?.trim().includes(targetText)) {{
                            el.click();
                            return true;
                        }}
                    }}
                    return false;
                }}
            """, text)

            if clicked:
                await asyncio.sleep(2)  # Wait for content to load
                return True

        except Exception as e:
            self.log(f"Error clicking top tab '{text}': {e}", "WARN")

        return False

    async def extract_page_content(self) -> Dict:
        """Extract all content from current page including endpoints."""
        content = await self.page.evaluate("""
            () => {
                const result = {
                    title: '',
                    description: '',
                    endpoints: [],
                    tables: [],
                    codeBlocks: [],
                    rawText: ''
                };

                // Get page title
                const h1 = document.querySelector('h1, .page-title, article h1');
                if (h1) result.title = h1.innerText?.trim() || '';

                // Get main content area
                const content = document.querySelector('article, .content, .markdown-body, main, .page-content');
                if (content) {
                    result.rawText = content.innerText?.substring(0, 50000) || '';
                }

                // Extract all headings with their content
                const headings = document.querySelectorAll('h1, h2, h3, h4');
                headings.forEach(heading => {
                    const text = heading.innerText || '';

                    // Check if this looks like an endpoint
                    const methodMatch = text.match(/\\b(GET|POST|PUT|DELETE|PATCH)\\b/i);
                    const pathMatch = text.match(/(\\/[\\w\\/-{}]+)/);

                    if (methodMatch || pathMatch || text.toLowerCase().includes('endpoint')) {
                        const endpoint = {
                            title: text.trim(),
                            method: methodMatch ? methodMatch[1].toUpperCase() : '',
                            path: pathMatch ? pathMatch[1] : '',
                            description: '',
                            parameters: [],
                            requestExample: null,
                            responseExample: null
                        };

                        // Look for content after this heading
                        let sibling = heading.nextElementSibling;
                        let tableFound = false;

                        while (sibling && !sibling.matches('h1, h2, h3')) {
                            // Get description
                            if (sibling.matches('p') && !endpoint.description) {
                                endpoint.description = sibling.innerText?.trim() || '';
                            }

                            // Get tables (parameters)
                            if (sibling.matches('table') && !tableFound) {
                                const rows = sibling.querySelectorAll('tr');
                                const headers = Array.from(sibling.querySelectorAll('th'))
                                    .map(th => th.innerText?.toLowerCase().trim() || '');

                                rows.forEach((row, idx) => {
                                    if (idx === 0 && row.querySelector('th')) return; // Skip header

                                    const cells = Array.from(row.querySelectorAll('td'))
                                        .map(td => td.innerText?.trim() || '');

                                    if (cells.length >= 2) {
                                        const param = {
                                            name: cells[0] || '',
                                            type: cells[1] || '',
                                            required: cells.length > 2 ? cells[2] : '',
                                            description: cells.length > 3 ? cells[3] : (cells.length > 2 ? cells[2] : '')
                                        };

                                        // Try to map by headers
                                        headers.forEach((h, i) => {
                                            if (h.includes('required') || h.includes('mandatory')) {
                                                param.required = cells[i] || '';
                                            }
                                            if (h.includes('desc')) {
                                                param.description = cells[i] || '';
                                            }
                                            if (h.includes('example')) {
                                                param.example = cells[i] || '';
                                            }
                                        });

                                        endpoint.parameters.push(param);
                                    }
                                });
                                tableFound = true;
                            }

                            // Get code blocks
                            if (sibling.matches('pre, code, .highlight')) {
                                const code = sibling.innerText?.trim() || '';
                                if (code.startsWith('{') || code.startsWith('[')) {
                                    try {
                                        const parsed = JSON.parse(code);
                                        if (!endpoint.responseExample) {
                                            endpoint.responseExample = parsed;
                                        }
                                    } catch {
                                        if (!endpoint.responseExample) {
                                            endpoint.responseExample = code.substring(0, 5000);
                                        }
                                    }
                                } else if (code.includes('curl') || code.includes('http')) {
                                    endpoint.requestExample = code.substring(0, 2000);
                                }
                            }

                            sibling = sibling.nextElementSibling;
                        }

                        if (endpoint.method || endpoint.path || endpoint.parameters.length > 0) {
                            result.endpoints.push(endpoint);
                        }
                    }
                });

                // Also look for API paths in the content
                const apiPaths = result.rawText.match(/\\/api\\/v[0-9]+\\/[\\w\\/-]+|\\/(openApi|api)\\/[\\w\\/-]+/g) || [];
                result.pathsFound = [...new Set(apiPaths)];

                // Extract all tables
                document.querySelectorAll('table').forEach(table => {
                    const headers = Array.from(table.querySelectorAll('th')).map(th => th.innerText?.trim());
                    const rows = [];
                    table.querySelectorAll('tbody tr').forEach(tr => {
                        const cells = Array.from(tr.querySelectorAll('td')).map(td => td.innerText?.trim());
                        if (cells.length > 0) rows.push(cells);
                    });
                    if (headers.length > 0 || rows.length > 0) {
                        result.tables.push({ headers, rows });
                    }
                });

                // Extract all code blocks
                document.querySelectorAll('pre, code.hljs').forEach(block => {
                    const text = block.innerText?.trim();
                    if (text && text.length > 10 && text.length < 10000) {
                        result.codeBlocks.push(text);
                    }
                });

                return result;
            }
        """)

        return content

    async def extract_endpoints_enhanced(self) -> List[Dict]:
        """Enhanced endpoint extraction with multiple strategies."""
        endpoints = []

        # Strategy 1: Look for endpoint patterns in all text
        raw_endpoints = await self.page.evaluate("""
            () => {
                const endpoints = [];
                const content = document.body.innerText;

                // Find GET/POST patterns
                const methodPattern = /(GET|POST|PUT|DELETE|PATCH)\\s+(\\/[\\w\\/-{}?=&]+)/gi;
                let match;
                while ((match = methodPattern.exec(content)) !== null) {
                    endpoints.push({
                        method: match[1].toUpperCase(),
                        path: match[2],
                        source: 'pattern'
                    });
                }

                // Find API URL patterns
                const urlPattern = /https?:\\/\\/[\\w.-]+(\\/api\\/[\\w\\/-{}?=&]+)/gi;
                while ((match = urlPattern.exec(content)) !== null) {
                    endpoints.push({
                        method: '',
                        path: match[1],
                        source: 'url'
                    });
                }

                // Find from code blocks
                document.querySelectorAll('pre, code').forEach(block => {
                    const text = block.innerText;
                    const pathMatch = text.match(/["'](\\/api\\/[\\w\\/-{}]+)["']/);
                    if (pathMatch) {
                        const methodMatch = text.match(/(GET|POST|PUT|DELETE)/i);
                        endpoints.push({
                            method: methodMatch ? methodMatch[1].toUpperCase() : '',
                            path: pathMatch[1],
                            source: 'code'
                        });
                    }
                });

                return endpoints;
            }
        """)

        # Deduplicate
        seen = set()
        for ep in raw_endpoints:
            key = f"{ep['method']}:{ep['path']}"
            if key not in seen and ep['path']:
                seen.add(key)
                endpoints.append(ep)

        return endpoints

    async def take_screenshot(self, name: str):
        """Take a screenshot of the current page."""
        try:
            safe_name = re.sub(r'[^\w\-]', '_', name)[:50]
            filename = self.SCREENSHOT_DIR / f"{safe_name}_{datetime.now().strftime('%H%M%S')}.png"
            await self.page.screenshot(path=str(filename), full_page=True)
            self.log(f"Screenshot saved: {filename}")
            return str(filename)
        except Exception as e:
            self.log(f"Error taking screenshot: {e}", "WARN")
            return None

    async def scrape_section(self, section_name: str) -> Dict:
        """Scrape a single section of the documentation."""
        section_data = {
            "name": section_name,
            "scraped_at": datetime.now().isoformat(),
            "content": None,
            "endpoints": [],
            "raw_endpoints": []
        }

        try:
            # Click on the section
            if await self.click_sidebar_item(section_name):
                await asyncio.sleep(1.5)

                # Extract content
                content = await self.extract_page_content()
                section_data["content"] = content
                section_data["endpoints"] = content.get("endpoints", [])

                # Also get raw endpoint patterns
                raw_endpoints = await self.extract_endpoints_enhanced()
                section_data["raw_endpoints"] = raw_endpoints

                # Take screenshot
                await self.take_screenshot(section_name)

                total_endpoints = len(section_data["endpoints"]) + len(section_data["raw_endpoints"])
                self.log(f"  Scraped '{section_name}': {total_endpoints} endpoints found")

        except Exception as e:
            self.log(f"Error scraping section '{section_name}': {e}", "ERROR")
            self.errors.append(f"{section_name}: {str(e)}")

        return section_data

    async def scrape_product_category(self, category_name: str) -> Dict:
        """Scrape an entire product category (top nav tab)."""
        category_data = {
            "name": category_name,
            "scraped_at": datetime.now().isoformat(),
            "sections": [],
            "total_endpoints": 0
        }

        try:
            # Click on the category tab
            self.log(f"\nScraping category: {category_name}")
            if await self.click_top_tab(category_name):
                await asyncio.sleep(2)

                # Take category screenshot
                await self.take_screenshot(f"category_{category_name}")

                # Get sidebar sections for this category
                sidebar_links = await self.get_sidebar_links()

                # Filter to relevant sections (skip common items)
                skip_items = {'Change Log', 'Introduction', 'Subscribe', ''}
                relevant_sections = [
                    link for link in sidebar_links
                    if link['text'] not in skip_items and len(link['text']) > 2
                ]

                self.log(f"  Found {len(relevant_sections)} sections in {category_name}")

                for link in relevant_sections:
                    section_data = await self.scrape_section(link['text'])
                    category_data["sections"].append(section_data)

                    # Count endpoints
                    category_data["total_endpoints"] += len(section_data.get("endpoints", []))
                    category_data["total_endpoints"] += len(section_data.get("raw_endpoints", []))

                    # Rate limiting
                    await asyncio.sleep(self.PAGE_DELAY)

        except Exception as e:
            self.log(f"Error scraping category '{category_name}': {e}", "ERROR")
            self.errors.append(f"{category_name}: {str(e)}")

        return category_data

    def save_json(self, data: dict, filename: str):
        """Save data to JSON file."""
        filepath = self.OUTPUT_DIR / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        self.log(f"Saved JSON: {filepath}")

    def save_endpoints_csv(self, endpoints: List[Dict], filename: str):
        """Save endpoints to CSV file."""
        if not endpoints:
            return

        filepath = self.OUTPUT_DIR / filename
        rows = []

        for ep in endpoints:
            row = {
                "category": ep.get("category", ""),
                "section": ep.get("section", ""),
                "method": ep.get("method", ""),
                "path": ep.get("path", ""),
                "title": ep.get("title", ""),
                "description": ep.get("description", "")[:500] if ep.get("description") else "",
                "param_count": len(ep.get("parameters", [])),
                "has_response": bool(ep.get("responseExample")),
                "parameters": json.dumps(ep.get("parameters", [])[:20])  # Limit params
            }
            rows.append(row)

        if rows:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            self.log(f"Saved CSV: {filepath}")

    def generate_summary(self, data: Dict) -> Dict:
        """Generate a summary of scraped data."""
        summary = {
            "total_categories": len(data.get("categories", [])),
            "total_sections": 0,
            "total_endpoints": 0,
            "endpoints_by_method": {},
            "endpoints_by_category": {},
            "errors": self.errors,
            "scraped_at": datetime.now().isoformat()
        }

        for cat in data.get("categories", []):
            cat_name = cat.get("name", "Unknown")
            cat_endpoints = 0

            for section in cat.get("sections", []):
                summary["total_sections"] += 1

                # Count endpoints from structured extraction
                for ep in section.get("endpoints", []):
                    method = ep.get("method", "UNKNOWN") or "UNKNOWN"
                    summary["endpoints_by_method"][method] = \
                        summary["endpoints_by_method"].get(method, 0) + 1
                    cat_endpoints += 1

                # Count endpoints from pattern extraction
                for ep in section.get("raw_endpoints", []):
                    method = ep.get("method", "UNKNOWN") or "UNKNOWN"
                    summary["endpoints_by_method"][method] = \
                        summary["endpoints_by_method"].get(method, 0) + 1
                    cat_endpoints += 1

            summary["endpoints_by_category"][cat_name] = cat_endpoints
            summary["total_endpoints"] += cat_endpoints

        return summary

    async def run(self):
        """Main scraping routine."""
        self.log("=" * 60)
        self.log("BingX API Documentation Scraper")
        self.log("=" * 60)

        try:
            await self.init_browser()

            # Navigate to base URL
            if not await self.navigate_with_retry(self.BASE_URL):
                self.log("Failed to load base URL", "ERROR")
                return

            # Take initial screenshot
            await self.take_screenshot("home_page")

            # Get top navigation tabs (product categories)
            await asyncio.sleep(2)

            # Define the main product categories based on the page structure
            product_categories = [
                "USDT-M Perp Futures",
                "Coin-M Perp Futures",
                "Spot",
                "Standard Futures",
                "Account & Wallet",
                "Copy Trading"
            ]

            self.log(f"\nWill scrape {len(product_categories)} product categories")

            # Main data structure
            all_data = {
                "source": self.BASE_URL,
                "scraped_at": datetime.now().isoformat(),
                "categories": []
            }

            # Scrape each product category
            for category in product_categories:
                category_data = await self.scrape_product_category(category)
                all_data["categories"].append(category_data)

                # Collect all endpoints with category info
                for section in category_data.get("sections", []):
                    for ep in section.get("endpoints", []):
                        ep["category"] = category
                        ep["section"] = section.get("name", "")
                        self.all_endpoints.append(ep)

                    for ep in section.get("raw_endpoints", []):
                        ep["category"] = category
                        ep["section"] = section.get("name", "")
                        self.all_endpoints.append(ep)

            # Generate summary
            summary = self.generate_summary(all_data)
            all_data["summary"] = summary

            # Save outputs
            self.save_json(all_data, "bingx_api_docs.json")
            self.save_endpoints_csv(self.all_endpoints, "bingx_all_endpoints.csv")
            self.save_json(summary, "bingx_scrape_summary.json")

            # Save per-category JSON
            for cat in all_data["categories"]:
                safe_name = re.sub(r'[^\w\-]', '_', cat.get("name", "unknown"))[:30]
                self.save_json(cat, f"bingx_{safe_name}.json")

            # Print summary
            self.log("\n" + "=" * 60)
            self.log("SCRAPING COMPLETE")
            self.log("=" * 60)
            self.log(f"Total categories: {summary['total_categories']}")
            self.log(f"Total sections: {summary['total_sections']}")
            self.log(f"Total endpoints: {summary['total_endpoints']}")
            self.log(f"Methods found: {summary['endpoints_by_method']}")
            self.log(f"Endpoints by category: {summary['endpoints_by_category']}")
            self.log(f"Errors: {len(self.errors)}")
            self.log(f"Output directory: {self.OUTPUT_DIR.absolute()}")

        except Exception as e:
            self.log(f"Fatal error: {e}", "ERROR")
            import traceback
            traceback.print_exc()

        finally:
            await self.close_browser()


async def main():
    """Entry point."""
    parser = argparse.ArgumentParser(description="BingX API Documentation Scraper")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode with slow_mo")
    parser.add_argument("--headed", action="store_true", help="Run browser in headed mode")
    args = parser.parse_args()

    scraper = BingXAPIScraper(debug=args.debug, headed=args.headed)
    await scraper.run()


if __name__ == "__main__":
    asyncio.run(main())
