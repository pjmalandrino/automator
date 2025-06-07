import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import json

from src.nlp_parser import NaturalLanguageParser, ParsedAction


class TestNaturalLanguageParser:
    """Test suite for NLP parser"""

    @pytest.fixture
    def parser(self):
        """Create parser instance"""
        return NaturalLanguageParser(model="llama3.2")

    @pytest.fixture
    def mock_ollama(self):
        """Mock ollama responses"""
        with patch('src.nlp_parser.ollama') as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_parse_navigation(self, parser, mock_ollama):
        """Test parsing navigation commands"""
        # Mock ollama response
        mock_ollama.generate.return_value = {
            'response': json.dumps({
                "scenario_name": "Navigate to example",
                "preconditions": [],
                "actions": [{
                    "action": "navigate",
                    "target": "https://example.com",
                    "value": "",
                    "description": "Navigate to example.com"
                }],
                "expected_outcome": "Page loads successfully"
            })
        }

        result = await parser.parse_test_description("Go to example.com")

        assert result['scenario_name'] == "Navigate to example"
        assert len(result['actions']) == 1
        assert result['actions'][0]['action'] == 'navigate'
        assert result['actions'][0]['target'] == 'https://example.com'

    @pytest.mark.asyncio
    async def test_parse_click_action(self, parser, mock_ollama):
        """Test parsing click actions"""
        mock_ollama.generate.return_value = {
            'response': json.dumps({
                "scenario_name": "Click login button",
                "preconditions": [],
                "actions": [{
                    "action": "click",
                    "target": "button:has-text('Login')",
                    "value": "",
                    "description": "Click the login button"
                }],
                "expected_outcome": "Login form appears"
            })
        }

        result = await parser.parse_test_description("Click the login button")

        assert result['actions'][0]['action'] == 'click'
        assert 'Login' in result['actions'][0]['target']

    @pytest.mark.asyncio
    async def test_parse_type_action(self, parser, mock_ollama):
        """Test parsing type/input actions"""
        mock_ollama.generate.return_value = {
            'response': json.dumps({
                "scenario_name": "Enter email",
                "preconditions": [],
                "actions": [{
                    "action": "type",
                    "target": "input[type='email']",
                    "value": "user@example.com",
                    "description": "Enter email address"
                }],
                "expected_outcome": "Email field is filled"
            })
        }

        result = await parser.parse_test_description(
            "Type user@example.com in the email field"
        )

        assert result['actions'][0]['action'] == 'type'
        assert result['actions'][0]['value'] == 'user@example.com'

    @pytest.mark.asyncio
    async def test_parse_assertion(self, parser, mock_ollama):
        """Test parsing assertions"""
        mock_ollama.generate.return_value = {
            'response': json.dumps({
                "scenario_name": "Verify welcome message",
                "preconditions": [],
                "actions": [{
                    "action": "assert",
                    "target": "text",
                    "value": "Welcome",
                    "description": "Verify welcome message appears"
                }],
                "expected_outcome": "Welcome message is visible"
            })
        }

        result = await parser.parse_test_description(
            "Verify I see Welcome message"
        )

        assert result['actions'][0]['action'] == 'assert'
        assert result['actions'][0]['value'] == 'Welcome'

    @pytest.mark.asyncio
    async def test_parse_complex_scenario(self, parser, mock_ollama):
        """Test parsing multi-step scenario"""
        mock_ollama.generate.return_value = {
            'response': json.dumps({
                "scenario_name": "Complete login flow",
                "preconditions": ["User has valid credentials"],
                "actions": [
                    {
                        "action": "navigate",
                        "target": "https://app.example.com/login",
                        "value": "",
                        "description": "Go to login page"
                    },
                    {
                        "action": "type",
                        "target": "input[name='email']",
                        "value": "user@example.com",
                        "description": "Enter email"
                    },
                    {
                        "action": "type",
                        "target": "input[name='password']",
                        "value": "password123",
                        "description": "Enter password"
                    },
                    {
                        "action": "click",
                        "target": "button[type='submit']",
                        "value": "",
                        "description": "Click submit button"
                    },
                    {
                        "action": "assert",
                        "target": "text",
                        "value": "Dashboard",
                        "description": "Verify dashboard loads"
                    }
                ],
                "expected_outcome": "User is logged in and sees dashboard"
            })
        }

        scenario = """
        Go to https://app.example.com/login
        Enter user@example.com in email field
        Enter password123 in password field
        Click submit button
        Verify I see Dashboard
        """

        result = await parser.parse_test_description(scenario)

        assert len(result['actions']) == 5
        assert result['actions'][0]['action'] == 'navigate'
        assert result['actions'][1]['action'] == 'type'
        assert result['actions'][2]['action'] == 'type'
        assert result['actions'][3]['action'] == 'click'
        assert result['actions'][4]['action'] == 'assert'

    @pytest.mark.asyncio
    async def test_enhance_selector(self, parser, mock_ollama):
        """Test selector enhancement"""
        mock_ollama.generate.return_value = {
            'response': "button[data-testid='submit-button']"
        }

        page_context = """
        <form>
            <button data-testid="submit-button">Submit</button>
        </form>
        """

        selector = await parser.enhance_selector("submit button", page_context)

        assert selector == "button[data-testid='submit-button']"

    def test_action_patterns(self, parser):
        """Test action pattern loading"""
        patterns = parser.action_patterns

        assert "navigation" in patterns
        assert "go to" in patterns["navigation"]
        assert "click" in patterns
        assert "type" in patterns
        assert "assertion" in patterns

    @pytest.mark.asyncio
    async def test_parse_wait_action(self, parser, mock_ollama):
        """Test parsing wait commands"""
        mock_ollama.generate.return_value = {
            'response': json.dumps({
                "scenario_name": "Wait for loading",
                "preconditions": [],
                "actions": [{
                    "action": "wait",
                    "target": "element",
                    "value": ".loading-spinner",
                    "description": "Wait for loading to complete"
                }],
                "expected_outcome": "Loading completes"
            })
        }

        result = await parser.parse_test_description(
            "Wait for loading spinner to disappear"
        )

        assert result['actions'][0]['action'] == 'wait'

    @pytest.mark.asyncio
    async def test_error_handling(self, parser, mock_ollama):
        """Test error handling in parsing"""
        # Simulate invalid JSON response
        mock_ollama.generate.return_value = {
            'response': "Invalid JSON"
        }

        with pytest.raises(json.JSONDecodeError):
            await parser.parse_test_description("Some test")


@pytest.mark.asyncio
async def test_parsed_action_dataclass():
    """Test ParsedAction dataclass"""
    action = ParsedAction(
        action_type="click",
        target="button.submit",
        value="",
        metadata={"confidence": 0.95}
    )

    assert action.action_type == "click"
    assert action.target == "button.submit"
    assert action.value == ""
    assert action.metadata["confidence"] == 0.95