"""
MCP BDD Automation Server

A Model Context Protocol server for browser automation using natural language descriptions.
"""

__version__ = "0.1.0"

from .server import BDDAutomationServer
from .browser_engine import BrowserEngine
from .nlp_parser import NaturalLanguageParser
from .action_executor import ActionExecutor
from .context_manager import TestContextManager
from .validator import VisualValidator

__all__ = [
    "BDDAutomationServer",
    "BrowserEngine",
    "NaturalLanguageParser",
    "ActionExecutor",
    "TestContextManager",
    "VisualValidator"
]