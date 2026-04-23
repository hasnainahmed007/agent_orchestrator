"""Setup script for Agent Orchestrator - Marketplace Ready Package."""
from setuptools import setup, find_packages
from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="agent-orchestrator",
    version="1.0.0",
    author="Agent Orchestrator Team",
    author_email="contact@agentorchestrator.com",
    description="Multi-Agent Orchestration System for Laravel Development with Telegram Remote Control",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/agentorchestrator/agent-orchestrator",
    project_urls={
        "Bug Tracker": "https://github.com/agentorchestrator/agent-orchestrator/issues",
        "Documentation": "https://agentorchestrator.com/docs",
        "Source Code": "https://github.com/agentorchestrator/agent-orchestrator",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Code Generators",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Framework :: FastAPI",
        "Topic :: Communications :: Chat",
        "Topic :: Internet",
    ],
    keywords="ai, agents, laravel, automation, telegram, crewai, code-generation, devops",
    packages=find_packages(exclude=["tests*", "docs*", "examples*"]),
    python_requires=">=3.10",
    install_requires=[
        "crewai>=0.30.0",
        "langchain>=0.1.0",
        "langchain-openai>=0.0.5",
        "python-telegram-bot>=20.7",
        "GitPython>=3.1.40",
        "pydantic>=2.0.0",
        "python-dotenv>=1.0.0",
        "aiohttp>=3.9.0",
        "schedule>=1.2.0",
        "colorama>=0.4.6",
        "tiktoken>=0.5.0",
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio>=0.21",
            "pytest-cov>=4.0",
            "black>=23.0",
            "ruff>=0.1.0",
            "mypy>=1.0",
        ],
        "docs": [
            "sphinx>=7.0",
            "sphinx-rtd-theme>=1.3",
        ],
    },
    entry_points={
        "console_scripts": [
            "agent-orchestrator=main:main",
            "orchestrator=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "agent_orchestrator": [
            "dashboard/*.html",
            "config/*.py",
            "*.md",
        ],
    },
    license="MIT",
    license_files=["LICENSE"],
)
