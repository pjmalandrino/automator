from typing import Dict, List, Any, Optional, Callable
from playwright.async_api import Page, ElementHandle
import asyncio
import re

class ActionExecutor:
    """Advanced action execution with retry logic and smart element finding"""

    def __init__(self, retry_count: int = 3, retry_delay: float = 1.0):
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.action_handlers = {
            'navigate': self._execute_navigate,
            'click': self._execute_click,
            'type': self._execute_type,
            'select': self._execute_select,
            'assert': self._execute_assert,
            'wait': self._execute_wait,
            'hover': self._execute_hover,
            'screenshot': self._execute_screenshot,
            'scroll': self._execute_scroll,
            'press': self._execute_press,
            'check': self._execute_check,
            'uncheck': self._execute_uncheck,
            'upload': self._execute_upload,
            'download': self._execute_download,
            'iframe': self._execute_iframe,
            'execute_script': self._execute_script
        }

    async def execute(self, page: Page, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an action with retry logic"""
        action_type = action.get('action', '').lower()

        if action_type not in self.action_handlers:
            return {
                "success": False,
                "error": f"Unknown action type: {action_type}",
                "action": action
            }

        handler = self.action_handlers[action_type]

        for attempt in range(self.retry_count):
            try:
                result = await handler(page, action)
                result["attempts"] = attempt + 1
                return result
            except Exception as e:
                if attempt < self.retry_count - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue
                else:
                    return {
                        "success": False,
                        "error": str(e),
                        "action": action,
                        "attempts": attempt + 1
                    }

    async def _find_element(self, page: Page, target: str, description: str = "") -> ElementHandle:
        """Smart element finding with multiple strategies"""
        strategies = [
            # Direct selector
            lambda: page.locator(target),
            # By text content
            lambda: page.get_by_text(target, exact=True),
            # By partial text
            lambda: page.get_by_text(target, exact=False),
            # By placeholder
            lambda: page.get_by_placeholder(target),
            # By label
            lambda: page.get_by_label(target),
            # By title
            lambda: page.get_by_title(target),
            # By alt text
            lambda: page.get_by_alt_text(target),
            # By role and name
            lambda: page.get_by_role("button", name=target),
            lambda: page.get_by_role("link", name=target),
            lambda: page.get_by_role("textbox", name=target),
            # CSS selectors with attributes
            lambda: page.locator(f"[aria-label*='{target}' i]"),
            lambda: page.locator(f"[title*='{target}' i]"),
            lambda: page.locator(f"[data-testid*='{target}' i]"),
            # XPath
            lambda: page.locator(f"//*[contains(text(), '{target}')]")
        ]

        for strategy in strategies:
            try:
                locator = strategy()
                if await locator.count() > 0:
                    return locator.first
            except:
                continue

        # Try by description if provided
        if description:
            desc_words = description.lower().split()
            for word in desc_words:
                if len(word) > 3:  # Skip short words
                    try:
                        locator = page.locator(f"*:has-text('{word}')")
                        if await locator.count() > 0:
                            return locator.first
                    except:
                        continue

        raise Exception(f"Could not find element: {target}")

    async def _execute_navigate(self, page: Page, action: Dict) -> Dict:
        """Navigate to URL"""
        url = action.get('target', action.get('value', ''))

        # Add protocol if missing
        if url and not url.startswith(('http://', 'https://')):
            url = f'https://{url}'

        wait_until = action.get('wait_until', 'networkidle')

        response = await page.goto(url, wait_until=wait_until)

        return {
            "success": response.ok if response else True,
            "url": page.url,
            "status": response.status if response else None
        }

    async def _execute_click(self, page: Page, action: Dict) -> Dict:
        """Click an element"""
        target = action.get('target', '')
        description = action.get('description', '')

        element = await self._find_element(page, target, description)
        await element.click()

        # Wait for navigation if it occurs
        try:
            await page.wait_for_load_state('networkidle', timeout=5000)
        except:
            pass  # Navigation might not occur

        return {
            "success": True,
            "clicked": target,
            "new_url": page.url
        }

    async def _execute_type(self, page: Page, action: Dict) -> Dict:
        """Type text into an element"""
        target = action.get('target', '')
        value = action.get('value', '')
        description = action.get('description', '')
        clear_first = action.get('clear', True)

        element = await self._find_element(page, target, description)

        if clear_first:
            await element.clear()

        await element.type(value, delay=action.get('delay', 0))

        return {
            "success": True,
            "typed": value,
            "target": target
        }

    async def _execute_select(self, page: Page, action: Dict) -> Dict:
        """Select from dropdown"""
        target = action.get('target', '')
        value = action.get('value', '')
        by = action.get('by', 'value')  # value, label, or index

        element = await self._find_element(page, target)

        if by == 'label':
            await element.select_option(label=value)
        elif by == 'index':
            await element.select_option(index=int(value))
        else:
            await element.select_option(value)

        return {
            "success": True,
            "selected": value,
            "by": by
        }

    async def _execute_assert(self, page: Page, action: Dict) -> Dict:
        """Assert page content"""
        assert_type = action.get('target', 'text').lower()
        expected = action.get('value', '')

        actual = None
        matched = False

        if assert_type == 'title':
            actual = await page.title()
            matched = expected.lower() in actual.lower()

        elif assert_type == 'url':
            actual = page.url
            matched = expected in actual

        elif assert_type == 'text':
            content = await page.content()
            matched = expected.lower() in content.lower()
            actual = f"Page contains text: {matched}"

        elif assert_type == 'element':
            try:
                element = await self._find_element(page, expected)
                matched = await element.is_visible()
                actual = f"Element visible: {matched}"
            except:
                matched = False
                actual = "Element not found"

        elif assert_type == 'value':
            # Assert input value
            selector = action.get('selector', '')
            element = await self._find_element(page, selector)
            actual = await element.input_value()
            matched = actual == expected

        else:
            # Custom CSS selector assertion
            elements = await page.locator(assert_type).count()
            matched = elements > 0
            actual = f"Found {elements} elements"

        return {
            "success": matched,
            "assertion": f"{assert_type} = {expected}",
            "actual": actual,
            "matched": matched
        }

    async def _execute_wait(self, page: Page, action: Dict) -> Dict:
        """Wait for condition"""
        wait_type = action.get('target', 'time').lower()
        value = action.get('value', '1')

        if wait_type == 'time':
            # Wait for specific time in seconds
            wait_ms = int(float(value) * 1000)
            await page.wait_for_timeout(wait_ms)

        elif wait_type == 'element':
            # Wait for element to appear
            element = await self._find_element(page, value)
            await element.wait_for(state='visible')

        elif wait_type == 'hidden':
            # Wait for element to disappear
            element = await self._find_element(page, value)
            await element.wait_for(state='hidden')

        elif wait_type == 'network':
            # Wait for network to be idle
            await page.wait_for_load_state('networkidle')

        elif wait_type == 'load':
            # Wait for page load
            await page.wait_for_load_state('load')

        return {
            "success": True,
            "waited_for": f"{wait_type}: {value}"
        }

    async def _execute_hover(self, page: Page, action: Dict) -> Dict:
        """Hover over element"""
        target = action.get('target', '')
        element = await self._find_element(page, target)
        await element.hover()

        return {
            "success": True,
            "hovered": target
        }

    async def _execute_screenshot(self, page: Page, action: Dict) -> Dict:
        """Take screenshot"""
        filename = action.get('value', 'screenshot.png')
        full_page = action.get('full_page', True)

        screenshot_bytes = await page.screenshot(
            path=filename,
            full_page=full_page
        )

        return {
            "success": True,
            "filename": filename,
            "size": len(screenshot_bytes)
        }

    async def _execute_scroll(self, page: Page, action: Dict) -> Dict:
        """Scroll page or element"""
        target = action.get('target', 'page')
        direction = action.get('value', 'down')
        amount = action.get('amount', 500)

        if target == 'page':
            if direction == 'down':
                await page.evaluate(f"window.scrollBy(0, {amount})")
            elif direction == 'up':
                await page.evaluate(f"window.scrollBy(0, -{amount})")
            elif direction == 'top':
                await page.evaluate("window.scrollTo(0, 0)")
            elif direction == 'bottom':
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        else:
            element = await self._find_element(page, target)
            await element.scroll_into_view_if_needed()

        return {
            "success": True,
            "scrolled": f"{direction} {amount}px"
        }

    async def _execute_press(self, page: Page, action: Dict) -> Dict:
        """Press keyboard key"""
        key = action.get('value', action.get('target', ''))
        await page.keyboard.press(key)

        return {
            "success": True,
            "pressed": key
        }

    async def _execute_check(self, page: Page, action: Dict) -> Dict:
        """Check checkbox"""
        target = action.get('target', '')
        element = await self._find_element(page, target)
        await element.check()

        return {
            "success": True,
            "checked": target
        }

    async def _execute_uncheck(self, page: Page, action: Dict) -> Dict:
        """Uncheck checkbox"""
        target = action.get('target', '')
        element = await self._find_element(page, target)
        await element.uncheck()

        return {
            "success": True,
            "unchecked": target
        }

    async def _execute_upload(self, page: Page, action: Dict) -> Dict:
        """Upload file"""
        target = action.get('target', '')
        file_path = action.get('value', '')

        element = await self._find_element(page, target)
        await element.set_input_files(file_path)

        return {
            "success": True,
            "uploaded": file_path
        }

    async def _execute_download(self, page: Page, action: Dict) -> Dict:
        """Handle download"""
        target = action.get('target', '')

        # Start waiting for download
        async with page.expect_download() as download_info:
            # Click download button
            element = await self._find_element(page, target)
            await element.click()

        download = await download_info.value

        # Save to specified path or default
        save_path = action.get('value', download.suggested_filename)
        await download.save_as(save_path)

        return {
            "success": True,
            "downloaded": save_path,
            "url": download.url
        }

    async def _execute_iframe(self, page: Page, action: Dict) -> Dict:
        """Switch to iframe"""
        target = action.get('target', '')

        if target == 'main':
            # Switch back to main frame
            page = page.main_frame
        else:
            # Switch to iframe
            iframe = await self._find_element(page, target)
            page = await iframe.content_frame()

        return {
            "success": True,
            "switched_to": target
        }

    async def _execute_script(self, page: Page, action: Dict) -> Dict:
        """Execute JavaScript"""
        script = action.get('value', '')

        result = await page.evaluate(script)

        return {
            "success": True,
            "script_result": result
        }