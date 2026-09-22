---
generated: partial
---
# mobile_crawler.cli

<!-- summary:start -->
Click command-line interface (crawl, list, delete, report, config).
<!-- summary:end -->

## Modules
- [[code/cli/commands/_index|cli.commands]]
- [[code/cli/console_reader|cli.console_reader]] - One reader of stdin shared by every CLI prompt in a crawl (Human Fallback, --step-by-step pauses).
- [[code/cli/main|cli.main]] - Main CLI entry point using Click.
- [[code/cli/step_by_step_console|cli.step_by_step_console]] - Terminal side of `crawl --step-by-step`: summarize each paused step, advance on Enter.
- [[code/cli/terminal_human_prompter|cli.terminal_human_prompter]] - Terminal bridge for Human Fallback: blocks the calling (crawl) thread on a console prompt.
