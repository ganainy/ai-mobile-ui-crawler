#!/usr/bin/env python
"""Test script for crawler_agent integration."""

import logging
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_crawler_agent_import():
    """Test crawler_agent import and basic functionality."""
    try:
        import mobile_crawler.domain.crawler_agent as crawler_agent
        logger.info(f"✅ crawler_agent imported successfully (version: {getattr(crawler_agent, '__version__', 'unknown')})")
        return True
    except ImportError as e:
        logger.error(f"❌ Failed to import crawler_agent: {e}")
        return False

def test_mobile_crawler_imports():
    """Test mobile crawler imports."""
    try:
        from mobile_crawler.config.config_manager import ConfigManager
        from mobile_crawler.domain.adb_action_executor import ADBActionExecutor
        from mobile_crawler.domain.crawler_agent_service import CrawlerAgentService

        _ = (ConfigManager, ADBActionExecutor, CrawlerAgentService)
        logger.info("✅ ConfigManager import successful")
        logger.info("✅ CrawlerAgentService import successful")
        logger.info("✅ ADBActionExecutor import successful")

        return True
    except ImportError as e:
        logger.error(f"❌ Failed to import mobile crawler components: {e}")
        return False

def test_droidrun_config():
    """Test DroidRun configuration creation."""
    try:
        from mobile_crawler.config.config_manager import ConfigManager
        from mobile_crawler.domain.crawler_agent_service import CrawlerAgentService
        from mobile_crawler.infrastructure.ai_interaction_repository import AIInteractionRepository
        from mobile_crawler.infrastructure.database import DatabaseManager

        # Create test configuration
        config_manager = ConfigManager()
        config_manager.set('use_droidrun_agent', True)
        config_manager.set('ai_provider', 'openai')  # Use openai provider for testing

        # Initialize database components
        db = DatabaseManager()
        ai_repo = AIInteractionRepository(db)

        # Test DroidRun agent service creation
        agent_service = CrawlerAgentService(
            config_manager=config_manager,
            ai_interaction_repository=ai_repo,
            device_id="test_device"
        )

        logger.info("✅ DroidRun agent service created successfully")

        # Test configuration conversion
        droidrun_config = agent_service._get_droidrun_config()
        logger.info(f"✅ DroidRun configuration created: {list(droidrun_config.keys())}")

        return True
    except Exception as e:
        logger.error(f"❌ Failed to create DroidRun configuration: {e}")
        return False

def test_adb_executor():
    """Test ADB action executor."""
    try:
        from mobile_crawler.domain.adb_action_executor import ADBActionExecutor

        # Create executor (won't actually connect to device)
        ADBActionExecutor(device_id="test_device")
        logger.info("✅ ADB action executor created successfully")

        return True
    except Exception as e:
        logger.error(f"❌ Failed to create ADB action executor: {e}")
        return False

def test_ui_imports():
    """Test UI component imports."""
    try:
        from mobile_crawler.ui.widgets.settings_panel import SettingsPanel

        _ = SettingsPanel
        logger.info("✅ Settings panel import successful")

        return True
    except ImportError as e:
        logger.error(f"❌ Failed to import UI components: {e}")
        return False

def main():
    """Run all tests."""
    logger.info("🚀 Starting crawler_agent integration tests...")

    tests = [
        ("crawler_agent Import", test_crawler_agent_import),
        ("Mobile Crawler Imports", test_mobile_crawler_imports),
        ("DroidRun Configuration", test_droidrun_config),
        ("ADB Action Executor", test_adb_executor),
        ("UI Components", test_ui_imports),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        logger.info(f"\n--- Running {test_name} ---")
        if test_func():
            passed += 1
        else:
            logger.error(f"Test '{test_name}' failed")

    logger.info(f"\n📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        logger.info("🎉 All tests passed! crawler_agent integration is ready.")
        return 0
    else:
        logger.error("❌ Some tests failed. Please check the installation.")
        return 1

if __name__ == "__main__":
    exit(main())
