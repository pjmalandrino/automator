from typing import Dict, Any, Optional
from datetime import datetime
import json

class TestContextManager:
    """Manages test contexts and sessions"""

    def __init__(self):
        self.contexts: Dict[str, Dict[str, Any]] = {}

    def create_context(self, context_id: str, initial_data: Optional[Dict] = None) -> Dict:
        """Create a new test context"""
        self.contexts[context_id] = {
            "id": context_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "test_data": {},
            "history": [],
            "current_state": {},
            **(initial_data or {})
        }
        return self.contexts[context_id]

    def get_context(self, context_id: str) -> Dict:
        """Get context by ID, create if doesn't exist"""
        if context_id not in self.contexts:
            return self.create_context(context_id)
        return self.contexts[context_id]

    def update_context(self, context_id: str, updates: Dict[str, Any]) -> Dict:
        """Update context with new data"""
        context = self.get_context(context_id)

        # Add to history if it's a test result
        if "last_result" in updates:
            context["history"].append({
                "timestamp": datetime.now().isoformat(),
                "test": updates.get("last_test", ""),
                "result": updates["last_result"]
            })

        # Update the context
        for key, value in updates.items():
            if key == "test_data":
                # Merge test data instead of replacing
                context["test_data"].update(value)
            else:
                context[key] = value

        context["updated_at"] = datetime.now().isoformat()
        return context

    def get_test_data(self, context_id: str, key: Optional[str] = None) -> Any:
        """Get test data from context"""
        context = self.get_context(context_id)
        test_data = context.get("test_data", {})

        if key:
            return test_data.get(key)
        return test_data

    def set_test_data(self, context_id: str, key: str, value: Any):
        """Set test data in context"""
        context = self.get_context(context_id)
        if "test_data" not in context:
            context["test_data"] = {}
        context["test_data"][key] = value
        context["updated_at"] = datetime.now().isoformat()

    def get_history(self, context_id: str, limit: Optional[int] = None) -> list:
        """Get test history for context"""
        context = self.get_context(context_id)
        history = context.get("history", [])

        if limit:
            return history[-limit:]
        return history

    def clear_context(self, context_id: str):
        """Clear a specific context"""
        if context_id in self.contexts:
            del self.contexts[context_id]

    def list_contexts(self) -> Dict[str, Dict]:
        """List all active contexts"""
        return {
            context_id: {
                "id": context["id"],
                "created_at": context["created_at"],
                "updated_at": context["updated_at"],
                "test_count": len(context.get("history", [])),
                "current_url": context.get("current_url", "")
            }
            for context_id, context in self.contexts.items()
        }

    def export_context(self, context_id: str) -> str:
        """Export context as JSON"""
        context = self.get_context(context_id)
        return json.dumps(context, indent=2)

    def import_context(self, context_id: str, data: str) -> Dict:
        """Import context from JSON"""
        context_data = json.loads(data)
        context_data["id"] = context_id
        context_data["imported_at"] = datetime.now().isoformat()
        self.contexts[context_id] = context_data
        return self.contexts[context_id]