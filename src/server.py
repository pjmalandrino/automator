import asyncio
import json
from typing import Dict, List, Any, Optional
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent

from .browser_engine import BrowserEngine
from .nlp_parser import NaturalLanguageParser
from .validator import VisualValidator
from .context_manager import TestContextManager

class BDDAutomationServer:
    def __init__(self):
        self.server = Server("bdd-automation")
        self.browser_engine = BrowserEngine()
        self.parser = NaturalLanguageParser()
        self.context_manager = TestContextManager()
        self.setup_tools()

    async def initialize(self):
        """Initialize all components"""
        await self.browser_engine.initialize()

    def setup_tools(self):
        """Register available tools with MCP protocol"""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="execute_test",
                    description="Execute a natural language test description",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "Natural language test description"
                            },
                            "context_id": {
                                "type": "string",
                                "description": "Optional context identifier for test session",
                                "default": "default"
                            }
                        },
                        "required": ["description"]
                    }
                ),
                Tool(
                    name="validate_page",
                    description="Validate current page state against expectation",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "expectation": {
                                "type": "string",
                                "description": "Natural language expectation"
                            },
                            "context_id": {
                                "type": "string",
                                "default": "default"
                            }
                        },
                        "required": ["expectation"]
                    }
                ),
                Tool(
                    name="run_scenario",
                    description="Run a complete test scenario with multiple steps",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "scenario": {
                                "type": "string",
                                "description": "Multi-step test scenario"
                            },
                            "test_data": {
                                "type": "object",
                                "description": "Test data to use in scenario"
                            }
                        },
                        "required": ["scenario"]
                    }
                ),
                Tool(
                    name="get_test_context",
                    description="Get current test context and state",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "context_id": {"type": "string", "default": "default"}
                        }
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict) -> List[TextContent | ImageContent]:
            try:
                if name == "execute_test":
                    result = await self.execute_test(
                        arguments.get("description"),
                        arguments.get("context_id", "default")
                    )

                elif name == "validate_page":
                    result = await self.validate_page(
                        arguments.get("expectation"),
                        arguments.get("context_id", "default")
                    )

                elif name == "run_scenario":
                    result = await self.run_scenario(
                        arguments.get("scenario"),
                        arguments.get("test_data", {})
                    )

                elif name == "get_test_context":
                    result = await self.get_context_info(
                        arguments.get("context_id", "default")
                    )

                else:
                    result = {"error": f"Unknown tool: {name}"}

                # Return result as text
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]

            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "error": str(e),
                        "tool": name,
                        "arguments": arguments
                    }, indent=2)
                )]

    async def execute_test(self, description: str, context_id: str) -> Dict:
        """Execute a natural language test"""

        # Parse the test description
        parsed = await self.parser.parse_test_description(description)

        # Get or create page for this context
        page = await self.browser_engine.get_or_create_page(context_id)

        # Execute each action
        results = []
        for action in parsed.get('actions', []):
            result = await self.browser_engine.execute_action(page, action)
            results.append({
                "step": action.get('description', str(action)),
                "result": result
            })

            # Stop on failure
            if not result.get('success'):
                break

        # Update context
        self.context_manager.update_context(context_id, {
            "last_test": description,
            "last_result": results,
            "current_url": page.url
        })

        # Return comprehensive result
        success = all(r['result'].get('success') for r in results)

        return {
            "test": description,
            "success": success,
            "scenario_name": parsed.get('scenario_name'),
            "steps_executed": len(results),
            "results": results,
            "final_url": page.url,
            "context_id": context_id
        }

    async def validate_page(self, expectation: str, context_id: str) -> Dict:
        """Validate current page state"""

        page = await self.browser_engine.get_or_create_page(context_id)

        # Get page context
        page_context = await self.browser_engine.get_page_context(page)

        # Take screenshot for visual validation
        screenshot = await self.browser_engine.take_screenshot(page)

        # Create validator and check expectation
        validator = VisualValidator()
        validation_result = await validator.validate_expectation(
            expectation,
            page_context,
            screenshot
        )

        return {
            "expectation": expectation,
            "met": validation_result['met'],
            "evidence": validation_result['evidence'],
            "page_info": {
                "url": page.url,
                "title": page_context['title']
            },
            "context_id": context_id
        }

    async def run_scenario(self, scenario: str, test_data: Dict) -> Dict:
        """Run a complete multi-step scenario"""

        # Parse the entire scenario
        lines = scenario.strip().split('\n')
        context_id = f"scenario_{hash(scenario) % 10000}"

        # Store test data in context
        self.context_manager.update_context(context_id, {"test_data": test_data})

        all_results = []

        for line in lines:
            if line.strip():
                # Execute each line as a test
                result = await self.execute_test(line.strip(), context_id)
                all_results.append(result)

                # Stop on failure
                if not result['success']:
                    break

        return {
            "scenario": scenario,
            "total_steps": len(lines),
            "executed_steps": len(all_results),
            "success": all(r['success'] for r in all_results),
            "results": all_results,
            "test_data": test_data
        }

    async def get_context_info(self, context_id: str) -> Dict:
        """Get information about test context"""

        context = self.context_manager.get_context(context_id)

        if context_id in self.browser_engine.pages:
            page = self.browser_engine.pages[context_id]
            context['current_page'] = {
                "url": page.url,
                "title": await page.title()
            }

        return context

    async def cleanup(self):
        """Clean up resources"""
        await self.browser_engine.cleanup()

    async def run(self):
        """Start the MCP server"""
        await self.initialize()

        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(read_stream, write_stream)
        finally:
            await self.cleanup()

def main():
    """Entry point for the MCP server"""
    import sys
    import logging

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create and run server
    server = BDDAutomationServer()

    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logging.info("Server stopped by user")
    except Exception as e:
        logging.error(f"Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()