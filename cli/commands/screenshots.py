#!/usr/bin/env python3
"""
Screenshots command group for managing screenshot-related operations.
"""

import argparse
from pathlib import Path
from typing import List

from cli.commands.base import CommandGroup, CommandHandler, CommandResult
from cli.shared.context import ApplicationContext
from cli.constants.messages import (
    SCREENSHOTS_GROUP_DESC,
    CMD_ANNOTATE_SCREENSHOTS_DESC,
    ARG_HELP_SESSION_DIR,
    MSG_ANNOTATE_SCREENSHOTS_SUCCESS,
    MSG_ANNOTATE_SCREENSHOTS_PARTIAL,
    ERR_ANNOTATE_SCREENSHOTS_FAILED,
    ERR_ANNOTATE_SCREENSHOTS_NO_SESSION,
)


class AnnotateScreenshotsCommand(CommandHandler):
    """Handle annotate screenshots command."""
    
    @property
    def name(self) -> str:
        """Get command name."""
        return "annotate"
    
    @property
    def description(self) -> str:
        """Get command description."""
        return CMD_ANNOTATE_SCREENSHOTS_DESC
    
    def register(self, subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
        """Register the command with the argument parser."""
        parser = subparsers.add_parser(
            self.name,
            help=self.description,
            description=self.description
        )
        self.add_common_arguments(parser)
        parser.add_argument(
            "--session-dir",
            type=str,
            default=None,
            help=ARG_HELP_SESSION_DIR
        )
        parser.add_argument(
            "--output-dir",
            type=str,
            default=None,
            help="Output directory for annotated screenshots (default: session_dir/annotated_screenshots)"
        )
        parser.set_defaults(handler=self)
        return parser
    
    def run(self, args: argparse.Namespace, context: ApplicationContext) -> CommandResult:
        """Execute the command."""
        from cli.services.screenshot_annotator import ScreenshotAnnotator
        from cli.services.analysis_service import AnalysisService
        
        annotator = ScreenshotAnnotator()
        
        # Determine session directory
        if args.session_dir:
            session_dir = Path(args.session_dir)
            if not session_dir.exists():
                return CommandResult(
                    success=False,
                    message=f"Session directory not found: {args.session_dir}",
                    exit_code=1
                )
        else:
            # Find latest session
            analysis_service = AnalysisService(context)
            session_info = analysis_service.find_latest_session_dir()
            if not session_info:
                return CommandResult(
                    success=False,
                    message=ERR_ANNOTATE_SCREENSHOTS_NO_SESSION,
                    exit_code=1
                )
            session_dir = Path(session_info[0])
        
        # Determine output directory
        output_dir = None
        if args.output_dir:
            output_dir = Path(args.output_dir)
        
        # Run annotation
        print(f"Annotating screenshots in: {session_dir}")
        success, result = annotator.annotate_session(session_dir, output_dir)
        
        # Report results
        annotated = result.get("annotated_count", 0)
        skipped = result.get("skipped_count", 0)
        out_dir = result.get("output_dir", "")
        errors = result.get("errors", [])
        
        if success:
            if skipped > 0:
                message = MSG_ANNOTATE_SCREENSHOTS_PARTIAL.format(
                    annotated=annotated,
                    skipped=skipped,
                    output_dir=out_dir
                )
            else:
                message = MSG_ANNOTATE_SCREENSHOTS_SUCCESS.format(
                    count=annotated,
                    output_dir=out_dir
                )
            print(f"\n✅ {message}")
            return CommandResult(success=True, message=message)
        else:
            error_detail = "; ".join(errors) if errors else "Unknown error"
            message = f"{ERR_ANNOTATE_SCREENSHOTS_FAILED}: {error_detail}"
            print(f"\n❌ {message}")
            return CommandResult(success=False, message=message, exit_code=1)


class ScreenshotsCommandGroup(CommandGroup):
    """Screenshots command group."""
    
    def __init__(self):
        """Initialize Screenshots command group."""
        super().__init__("screenshots", SCREENSHOTS_GROUP_DESC)
    
    def get_commands(self) -> List[CommandHandler]:
        """Get commands in this group."""
        return [
            AnnotateScreenshotsCommand(),
        ]
