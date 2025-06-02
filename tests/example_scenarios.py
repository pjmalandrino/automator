"""
Example test scenarios that can be run through the MCP server
"""

EXAMPLE_SCENARIOS = [
    # Simple navigation test
    "Go to https://example.com and verify the page says Example Domain",

    # Login flow test
    """Navigate to https://demo.site/login
    Enter 'testuser@email.com' in the email field
    Enter 'password123' in the password field  
    Click the Login button
    Verify I see the Dashboard page""",

    # E-commerce test
    """Go to the online store
    Search for 'blue shoes'
    Click on the first product
    Select size 10
    Add to cart
    Go to checkout
    Verify the total is shown""",

    # Form validation test
    """Open the registration form
    Try to submit without filling anything
    Verify I see error messages
    Fill in all required fields
    Submit the form
    Check for success message"""
]

# Test data examples
TEST_DATA_EXAMPLES = {
    "user_registration": {
        "first_name": "Test",
        "last_name": "User",
        "email": "test@example.com",
        "password": "SecurePass123!",
        "phone": "+1234567890"
    },
    "product_search": {
        "search_terms": ["laptop", "wireless mouse", "USB cable"],
        "price_range": {"min": 10, "max": 500}
    }
}