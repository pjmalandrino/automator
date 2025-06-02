from setuptools import setup, find_packages

setup(
    name="mcp-bdd-automation",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "mcp>=0.1.0",
        "playwright>=1.40.0",
        "ollama>=0.1.7",
        "pydantic>=2.0.0"
    ],
    entry_points={
        "console_scripts": [
            "mcp-bdd-server=src.server:main"
        ]
    },
    python_requires=">=3.8",
)