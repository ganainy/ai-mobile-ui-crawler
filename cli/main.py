"""
Main entry point for the modular CLI.
"""

import argparse
import logging
import sys
from typing import List, Optional

from cli.commands.base import CommandRegistry
from cli.argument_parser import build_parser
from cli.shared.context import ApplicationContext



def run(args: Optional[List[str]] = None) -> int:
    """
    Main CLI entry point.
    
    Args:
        args: Command line arguments (defaults to sys.argv[1:])
        
    Returns:
        Exit code
    """
    try:
        # Build argument parser
        parser = build_parser()

        # Set up and register all commands BEFORE parsing args so --help shows them
        registry = CommandRegistry()
        _register_commands(registry)
        registry.register_all(parser)

        # Parse arguments (help will now include all subcommands)
        parsed_args = parser.parse_args(args)

        # Initialize CLI context (after parsing to get verbose flag)
        context = ApplicationContext(verbose=getattr(parsed_args, 'verbose', False))

        # Register telemetry service
        from cli.services.telemetry import TelemetryService
        context.services.register("telemetry", TelemetryService())

        # Register core services
        from cli.services.analysis_service import AnalysisService
        from cli.services.app_scan_service import AppScanService
        from cli.services.crawler_service import CrawlerService
        from cli.services.device_service import DeviceService

        from cli.services.mobsf_service import MobSFService
        from cli.services.openrouter_service import OpenRouterService
        from cli.services.ollama_service import OllamaService
        from cli.services.gemini_service import GeminiService
        from cli.services.crawler_actions_service import CrawlerActionsService
        from cli.services.crawler_prompts_service import CrawlerPromptsService

        context.services.register("device", DeviceService(context))
        context.services.register("app_scan", AppScanService(context))
        crawler_service = CrawlerService(context)
        context.services.register("crawler", crawler_service)
        context.services.register("analysis", AnalysisService(context))

        context.services.register("mobsf", MobSFService(context))
        context.services.register("openrouter", OpenRouterService(context))
        context.services.register("ollama", OllamaService(context))
        context.services.register("gemini", GeminiService(context))
        context.services.register("actions", CrawlerActionsService(context))
        context.services.register("prompts", CrawlerPromptsService(context))

        # Set up signal handler for graceful shutdown (Ctrl+C)
        from core.signal_handler import setup_cli_signal_handler
        setup_cli_signal_handler(crawler_service=crawler_service)

        # Execute command
        handler = registry.get_command_handler(parsed_args)
        if handler:
            result = handler.run(parsed_args, context)
            if result.message:
                if result.success:
                    print(result.message)
                else:
                    logging.error(result.message)
            return result.exit_code
        else:
            parser.print_help()
            return 1
            
    except KeyboardInterrupt:
        return 130
    except Exception as e:
        logging.critical(f"Unexpected CLI error: {e}", exc_info=True)
        return 1


def _register_commands(registry: CommandRegistry) -> None:
    """
    Register all command modules.
    
    Args:
        registry: Command registry to register with
    """
    # Import command modules (lazy loading to avoid circular imports)
    try:
        from cli.commands import (
            actions,
            analysis,
            apps,
            settings,
            crawler,
            crawler_prompts,
            device,

            gemini,
            mobsf,
            ollama,
            openrouter,
            packages,
            screenshots,
            services_check
        )

        # Register standalone commands
        registry.add_standalone_command(services_check.PrecheckCommand())

        # Register command groups
        config_group = settings.ConfigCommandGroup()
        device_group = device.DeviceCommandGroup()
        apps_group = apps.AppsCommandGroup()
        crawler_group = crawler.CrawlerCommandGroup()

        gemini_group = gemini.GeminiCommandGroup()
        mobsf_group = mobsf.MobSFCommandGroup()
        ollama_group = ollama.OllamaCommandGroup()
        openrouter_group = openrouter.OpenRouterCommandGroup()
        analysis_group = analysis.AnalysisCommandGroup()
        packages_group = packages.PackagesCommandGroup()
        actions_group = actions.CrawlerActionsCommandGroup()
        prompts_group = crawler_prompts.CrawlerPromptsCommandGroup()
        screenshots_group = screenshots.ScreenshotsCommandGroup()

        # Register groups instead of individual commands
        registry.add_group(config_group)
        registry.add_group(device_group)
        registry.add_group(apps_group)
        registry.add_group(crawler_group)

        registry.add_group(gemini_group)
        registry.add_group(mobsf_group)
        registry.add_group(ollama_group)
        registry.add_group(openrouter_group)
        registry.add_group(analysis_group)
        registry.add_group(packages_group)
        registry.add_group(actions_group)
        registry.add_group(prompts_group)
        registry.add_group(screenshots_group)


    except ImportError as e:
        logging.error(f"Failed to import command modules: {e}")
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(run())
