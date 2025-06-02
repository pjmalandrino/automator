from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from typing import Dict, Optional, Any
import asyncio

class BrowserEngine:
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.contexts: Dict[str, BrowserContext] = {}
        self.pages: Dict[str, Page] = {}

    async def initialize(self):
        """Initialize Playwright and browser"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )

    async def get_or_create_page(self, context_id: str = "default") -> Page:
        """Get existing page or create new one for context"""

        if context_id not in self.pages:
            if context_id not in self.contexts:
                self.contexts[context_id] = await self.browser.new_context()

            self.pages[context_id] = await self.contexts[context_id].new_page()

            # Set up console and error logging
            self.pages[context_id].on("console", lambda msg: print(f"Console: {msg.text}"))
            self.pages[context_id].on("pageerror", lambda err: print(f"Error: {err}"))

        return self.pages[context_id]

    async def execute_action(self, page: Page, action: Dict) -> Dict:
        """Execute a single browser action"""

        action_type = action.get('action')
        target = action.get('target')
        value = action.get('value', '')

        try:
            if action_type == 'navigate':
                await page.goto(target, wait_until='networkidle')
                return {"success": True, "url": page.url}

            elif action_type == 'click':
                # Try multiple strategies
                await self._smart_click(page, target, action.get('description'))
                return {"success": True, "clicked": target}

            elif action_type == 'type':
                await self._smart_type(page, target, value)
                return {"success": True, "typed": value}

            elif action_type == 'assert':
                result = await self._smart_assert(page, target, value)
                return {"success": result, "assertion": f"{target} = {value}"}

            elif action_type == 'wait':
                await page.wait_for_timeout(int(value) * 1000 if value.isdigit() else 2000)
                return {"success": True, "waited": value}

            else:
                return {"success": False, "error": f"Unknown action: {action_type}"}

        except Exception as e:
            return {"success": False, "error": str(e), "action": action}

    async def _smart_click(self, page: Page, selector: str, description: str = ""):
        """Click with multiple fallback strategies"""

        strategies = [
            # Try exact selector
            lambda: page.click(selector, timeout=5000),
            # Try by text
            lambda: page.get_by_text(selector).click(timeout=5000),
            # Try by partial text
            lambda: page.locator(f"*:has-text('{selector}')").first.click(timeout=5000),
            # Try by role
            lambda: page.get_by_role("button", name=selector).click(timeout=5000),
        ]

        for strategy in strategies:
            try:
                await strategy()
                return
            except:
                continue

        # If all fail, try to find by description
        if description:
            await self._click_by_description(page, description)
        else:
            raise Exception(f"Could not click: {selector}")

    async def _smart_type(self, page: Page, selector: str, value: str):
        """Type with smart selector resolution"""

        try:
            await page.fill(selector, value)
        except:
            # Try common input selectors
            for attempt in [
                f"input[placeholder*='{selector}' i]",
                f"input[name*='{selector}' i]",
                f"input[id*='{selector}' i]",
                f"textarea:has-text('{selector}')"
            ]:
                try:
                    await page.fill(attempt, value)
                    return
                except:
                    continue
            raise

    async def _smart_assert(self, page: Page, assert_type: str, expected: str) -> bool:
        """Smart assertion with multiple strategies"""

        if assert_type == "text":
            content = await page.content()
            return expected.lower() in content.lower()
        elif assert_type == "title":
            title = await page.title()
            return expected.lower() in title.lower()
        elif assert_type == "url":
            return expected in page.url
        else:
            # Try to find element with text
            elements = await page.locator(f"*:has-text('{expected}')").count()
            return elements > 0

    async def take_screenshot(self, page: Page) -> bytes:
        """Take screenshot for visual validation"""
        return await page.screenshot(full_page=True)

    async def get_page_context(self, page: Page) -> Dict:
        """Extract page context for AI analysis"""

        return {
            "url": page.url,
            "title": await page.title(),
            "text_content": await page.evaluate("() => document.body.innerText"),
            "interactive_elements": await page.evaluate("""() => {
                const elements = document.querySelectorAll('button, a, input, select, textarea, [role="button"]');
                return Array.from(elements).map(el => ({
                    tag: el.tagName,
                    text: el.innerText || el.value || el.placeholder,
                    type: el.type,
                    name: el.name,
                    id: el.id,
                    class: el.className
                }));
            }""")
        }

    async def cleanup(self):
        """Clean up browser resources"""
        for context in self.contexts.values():
            await context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()