import ollama
import base64
from typing import Dict, Any

class VisualValidator:
    def __init__(self, model="llava:7b"):
        self.model = model

    async def validate_expectation(
            self,
            expectation: str,
            page_context: Dict,
            screenshot: bytes
    ) -> Dict:
        """Validate if page meets expectation using vision AI"""

        # Convert screenshot to base64 for LLM
        screenshot_b64 = base64.b64encode(screenshot).decode()

        # Create comprehensive prompt
        prompt = f"""Analyze this webpage and determine if it meets the expectation.

Expectation: {expectation}

Page Information:
- URL: {page_context.get('url')}
- Title: {page_context.get('title')}
- Visible text (first 500 chars): {page_context.get('text_content', '')[:500]}

Interactive elements found: {len(page_context.get('interactive_elements', []))}

Based on the screenshot and page information, answer:
1. Does the page meet the expectation? (yes/no)
2. What evidence supports your answer?
3. If not met, what is missing or wrong?

Be specific and reference actual elements you can see."""

        response = ollama.generate(
            model=self.model,
            prompt=prompt,
            images=[screenshot]
        )

        # Parse response
        lines = response['response'].strip().split('\n')

        met = 'yes' in lines[0].lower() if lines else False
        evidence = lines[1] if len(lines) > 1 else "No evidence provided"
        missing = lines[2] if len(lines) > 2 else ""

        return {
            "met": met,
            "evidence": evidence,
            "missing": missing,
            "raw_analysis": response['response']
        }