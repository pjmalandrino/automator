import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, List

from src.server import BDDAutomationServer
from src.browser_engine import BrowserEngine
from src.nlp_parser import NaturalLanguageParser
from src.context_manager import TestContextManager
from mcp.types import Tool, TextContent


class TestBDDAutomationServer:
    """Test suite for BDD Automation MCP Server"""

    @pytest.fixture
    async def server(self):
        """Create server instance with mocked dependencies"""
        server = BDDAutomationServer()

        # Mock browser engine
        server.browser_engine = AsyncMock(spec=BrowserEngine)
        server.browser_engine.initialize = AsyncMock()
        server.browser_engine.get_or_create_page = AsyncMock()
        server.browser_engine.execute_action = AsyncMock()
        server.browser_engine.get_page_context = AsyncMock()
        server.browser_engine.take_screenshot = AsyncMock()
        server.browser_engine.cleanup = AsyncMock()

        # Mock parser
        server.parser = AsyncMock(spec=NaturalLanguageParser)

        # Real context manager (it's lightweight)
        server.context_manager = TestContextManager()

        await server.initialize()
        return server

    @pytest.mark.asyncio
    async def test_server_initialization(self, server):
        """Test server initializes properly"""
        assert server.browser_engine.initialize.called
        assert hasattr(server, 'server')
        assert hasattr(server, 'parser')
        assert hasattr(server, 'context_manager')

    @pytest.mark.asyncio
    async def test_list_tools(self, server):
        """Test tool listing"""
        # Mock the list_tools handler
        tools_handler = None
        for handler in server.server._request_handlers:
            if handler.__name__ == 'list_tools':
                tools_handler = handler
                break

        assert tools_handler is not None

        # Get tools list
        tools = await tools_handler()

        assert len(tools) == 4
        tool_names = [tool.name for tool in tools]
        assert "execute_test" in tool_names
        assert "validate_page" in tool_names
        assert "run_scenario" in tool_names
        assert "get_test_context" in tool_names

    @pytest.mark.asyncio
    async def test_execute_test_success(self, server):
        """Test successful test execution"""
        # Setup mocks
        server.parser.parse_test_description.return_value = {
            'scenario_name': 'Test Navigation',
            'actions': [
                {
                    'action': 'navigate',
                    'target': 'https://example.com',
                    'description': 'Go to example.com'
                }
            ]
        }

        mock_page = AsyncMock()
        mock_page.url = 'https://example.com'
        server.browser_engine.get_or_create_page.return_value = mock_page

        server.browser_engine.execute_action.return_value = {
            'success': True,
            'url': 'https://example.com'
        }

        # Execute test
        result = await server.execute_test(
            "Go to example.com",
            "test_context"
        )

        assert result['success'] is True
        assert result['test'] == "Go to example.com"
        assert result['steps_executed'] == 1
        assert result['final_url'] == 'https://example.com'

    @pytest.mark.asyncio
    async def test_execute_test_failure(self, server):
        """Test handling of failed test execution"""
        server.parser.parse_test_description.return_value = {
            'actions': [
                {
                    'action': 'click',
                    'target': 'button.missing',
                    'description': 'Click missing button'
                }
            ]
        }

        mock_page = AsyncMock()
        mock_page.url = 'https://example.com'
        server.browser_engine.get_or_create_page.return_value = mock_page

        server.browser_engine.execute_action.return_value = {
            'success': False,
            'error': 'Element not found'
        }

        result = await server.execute_test(
            "Click missing button",
            "test_context"
        )

        assert result['success'] is False
        assert result['results'][0]['result']['error'] == 'Element not found'

    @pytest.mark.asyncio
    async def test_validate_page(self, server):
        """Test page validation"""
        mock_page = AsyncMock()
        mock_page.url = 'https://example.com'
        server.browser_engine.get_or_create_page.return_value = mock_page

        server.browser_engine.get_page_context.return_value = {
            'url': 'https://example.com',
            'title': 'Example Domain',
            'text_content': 'This domain is for use in examples'
        }

        server.browser_engine.take_screenshot.return_value = b'fake_screenshot'

        # Mock validator
        with patch('src.server.VisualValidator') as mock_validator_class:
            mock_validator = AsyncMock()
            mock_validator_class.return_value = mock_validator
            mock_validator.validate_expectation.return_value = {
                'met': True,
                'evidence': 'Page contains expected text',
                'missing': ''
            }

            result = await server.validate_page(
                "Page should contain Example Domain",
                "test_context"
            )

        assert result['met'] is True
        assert result['expectation'] == "Page should contain Example Domain"
        assert 'page_info' in result

    @pytest.mark.asyncio
    async def test_run_scenario(self, server):
        """Test running multi-step scenario"""
        scenario = """Navigate to login page
Enter username
Enter password
Click login button"""

        # Setup parser to return actions for each line
        server.parser.parse_test_description.side_effect = [
            {'actions': [{'action': 'navigate', 'target': '/login'}]},
            {'actions': [{'action': 'type', 'target': 'username', 'value': 'user'}]},
            {'actions': [{'action': 'type', 'target': 'password', 'value': 'pass'}]},
            {'actions': [{'action': 'click', 'target': 'submit'}]}
        ]

        mock_page = AsyncMock()
        mock_page.url = 'https://example.com/dashboard'
        server.browser_engine.get_or_create_page.return_value = mock_page

        server.browser_engine.execute_action.return_value = {'success': True}

        result = await server.run_scenario(scenario, {'username': 'testuser'})

        assert result['success'] is True
        assert result['total_steps'] == 4
        assert result['executed_steps'] == 4

    @pytest.mark.asyncio
    async def test_get_context_info(self, server):
        """Test getting context information"""
        # Add some test data to context
        server.context_manager.update_context("test_ctx", {
            "last_test": "Click button test",
            "current_url": "https://example.com"
        })

        result = await server.get_context_info("test_ctx")

        assert result['last_test'] == "Click button test"
        assert result['current_url'] == "https://example.com"

    @pytest.mark.asyncio
    async def test_call_tool_execute_test(self, server):
        """Test calling execute_test through MCP protocol"""
        # Mock execute_test method
        server.execute_test = AsyncMock(return_value={
            'success': True,
            'test': 'test description'
        })

        # Get the call_tool handler
        call_tool_handler = None
        for handler in server.server._notification_handlers:
            if handler.__name__ == 'call_tool':
                call_tool_handler = handler
                break

        # If not in notification handlers, check request handlers
        if not call_tool_handler:
            for handler in server.server._request_handlers:
                if handler.__name__ == 'call_tool':
                    call_tool_handler = handler
                    break

        assert call_tool_handler is not None

        result = await call_tool_handler(
            "execute_test",
            {"description": "Click the button"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "success" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_unknown(self, server):
        """Test calling unknown tool"""
        call_tool_handler = None
        for handler in server.server._request_handlers:
            if handler.__name__ == 'call_tool':
                call_tool_handler = handler
                break

        result = await call_tool_handler(
            "unknown_tool",
            {"param": "value"}
        )

        assert len(result) == 1
        assert "Unknown tool" in result[0].text

    @pytest.mark.asyncio
    async def test_context_persistence(self, server):
        """Test context persists across test executions"""
        # First test
        server.parser.parse_test_description.return_value = {
            'actions': [{'action': 'navigate', 'target': 'page1'}]
        }

        mock_page = AsyncMock()
        mock_page.url = 'https://example.com/page1'
        server.browser_engine.get_or_create_page.return_value = mock_page
        server.browser_engine.execute_action.return_value = {'success': True}

        await server.execute_test("Go to page 1", "shared_context")

        # Second test in same context
        server.parser.parse_test_description.return_value = {
            'actions': [{'action': 'click', 'target': 'button'}]
        }

        mock_page.url = 'https://example.com/page2'

        await server.execute_test("Click button", "shared_context")

        # Check context
        context = server.context_manager.get_context("shared_context")
        assert len(context['history']) == 2
        assert context['current_url'] == 'https://example.com/page2'

    @pytest.mark.asyncio
    async def test_test_data_in_scenario(self, server):
        """Test using test data in scenarios"""
        scenario = "Enter {{username}} in username field"
        test_data = {"username": "john_doe"}

        server.parser.parse_test_description.return_value = {
            'actions': [{'action': 'type', 'target': 'username', 'value': 'john_doe'}]
        }

        mock_page = AsyncMock()
        server.browser_engine.get_or_create_page.return_value = mock_page
        server.browser_engine.execute_action.return_value = {'success': True}

        result = await server.run_scenario(scenario, test_data)

        assert result['success'] is True
        assert result['test_data'] == test_data

    @pytest.mark.asyncio
    async def test_cleanup(self, server):
        """Test server cleanup"""
        await server.cleanup()

        assert server.browser_engine.cleanup.called


class TestServerIntegration:
    """Integration tests for server components"""

    @pytest.mark.asyncio
    async def test_full_flow(self):
        """Test complete flow from description to execution"""
        server = BDDAutomationServer()

        # This would be an integration test with real browser
        # For now, we'll mock the key components
        server.browser_engine = AsyncMock()
        server.parser = AsyncMock()

        server.parser.parse_test_description.return_value = {
            'scenario_name': 'Login Flow',
            'actions': [
                {'action': 'navigate', 'target': 'https://app.com/login'},
                {'action': 'type', 'target': 'email', 'value': 'user@example.com'},
                {'action': 'type', 'target': 'password', 'value': 'secret'},
                {'action': 'click', 'target': 'submit'},
                {'action': 'assert', 'target': 'text', 'value': 'Dashboard'}
            ]
        }

        mock_page = AsyncMock()
        server.browser_engine.get_or_create_page.return_value = mock_page
        server.browser_engine.execute_action.return_value = {'success': True}

        await server.initialize()

        # Execute complete login flow
        result = await server.execute_test(
            """Go to https://app.com/login
            Enter user@example.com in email field
            Enter secret in password field
            Click submit button
            Verify Dashboard is shown""",
            "integration_test"
        )

        assert result['success'] is True
        assert result['steps_executed'] == 5