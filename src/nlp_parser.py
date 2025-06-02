import json
import ollama
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class ParsedAction:
    action_type: str  # navigate, click, type, assert, wait
    target: str       # selector or URL
    value: str        # input value or expected text
    metadata: Dict    # additional context

class NaturalLanguageParser:
    def __init__(self, model="llama3.2"):
        self.model = model
        self.action_patterns = self._load_action_patterns()

    def _load_action_patterns(self) -> Dict:
        """Load common action patterns for better parsing"""
        return {
            "navigation": ["go to", "navigate to", "open", "visit"],
            "click": ["click", "press", "tap", "select"],
            "type": ["type", "enter", "input", "fill"],
            "assertion": ["should see", "verify", "check", "ensure"],
            "wait": ["wait for", "wait until", "pause"]
        }

    async def parse_test_description(self, description: str) -> Dict:
        """Parse natural language test into structured actions"""

        prompt = f"""Parse this test description into browser automation steps.

Test: {description}

Identify each action needed and return as JSON:
{{
    "scenario_name": "Brief name for this test",
    "preconditions": ["any setup steps needed"],
    "actions": [
        {{
            "action": "navigate|click|type|assert|wait",
            "target": "selector or URL",
            "value": "input text or expected value",
            "description": "what this step does"
        }}
    ],
    "expected_outcome": "what should happen at the end"
}}

Examples:
- "go to example.com" -> action: navigate, target: "https://example.com"
- "click the login button" -> action: click, target: "button:has-text('Login')"
- "type user@email.com in the email field" -> action: type, target: "input[type='email']", value: "user@email.com"
- "should see Welcome message" -> action: assert, target: "text", value: "Welcome"
"""

        response = ollama.generate(
            model=self.model,
            prompt=prompt,
            format="json"
        )

        return json.loads(response['response'])

    async def enhance_selector(self, description: str, page_context: str) -> str:
        """Generate robust selector from element description"""

        prompt = f"""Given this element description and page context, generate the best selector.

Element: {description}
Page context: {page_context}

Return the most robust selector (prefer data-testid, aria-label, or unique text).
"""

        response = ollama.generate(model=self.model, prompt=prompt)
        return response['response'].strip()