"""Pytest configuration and fixtures for tests."""
import os
import sys
import json
from pathlib import Path

# Add parent directory to Python path for CI/CD environments
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Enable development mode for tests (no API key required)
os.environ["DEV_MODE"] = "true"
os.environ["DEV_MODE_ALLOWED_IN_PRODUCTION"] = "true"


def pytest_configure(config):
    """
    Configure pytest before running tests.

    This creates a minimal test configuration file if one doesn't exist.
    """
    # Check if we're in a test environment without provider.json
    # The provider.json should be in the same directory as the tests or in backend/
    test_dir = Path(__file__).parent

    # Try to find backend directory
    if (test_dir.parent / "backend").exists():
        # Running from project root: tests/ and backend/ are siblings
        backend_path = test_dir.parent / "backend"
    elif (test_dir.parent / "app").exists():
        # Running from backend/tests/: backend/app exists
        backend_path = test_dir.parent
    else:
        # Fallback: assume current directory
        backend_path = Path.cwd()

    provider_json = backend_path / "provider.json"

    if not provider_json.exists():
        # Create a minimal test configuration
        test_config = {
            "providers": [
                {
                    "name": "test-provider",
                    "base_url": "https://api.example.com/v1",
                    "api_key": "sk-test-key",
                    "models": {
                        "small": ["test-small"],
                        "middle": ["test-middle"],
                        "big": ["test-big"]
                    },
                    "enabled": True,
                    "priority": 1,
                    "timeout": 60,
                    "max_retries": 3
                }
            ],
            "model_mapping": {
                "haiku": "small",
                "sonnet": "middle",
                "opus": "big"
            }
        }

        # Write test configuration
        with open(provider_json, 'w', encoding='utf-8') as f:
            json.dump(test_config, f, indent=2)

        # Mark for cleanup
        config._test_provider_json = provider_json


def pytest_unconfigure(config):
    """
    Cleanup after tests complete.

    This removes the test configuration file if it was created.
    """
    if hasattr(config, '_test_provider_json'):
        try:
            config._test_provider_json.unlink()
        except Exception:
            pass
