

import sys
import os

# Fix Windows encoding issues - force UTF-8 encoding
os.environ['PYTHONUTF8'] = '1'
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import argparse
from cli import run
from config.app_config import Config

def main():
    # Check if running in crawler mode (via flag)
    # The crawler process is started with --crawler-run by the orchestrator
    crawler_mode = "--crawler-run" in sys.argv
    
    if crawler_mode:
        # Extract timestamp if present - simple parsing since we haven't set up argparse yet
        # for this mode (to avoid conflicts with subcommands)
        session_timestamp = None
        if "--timestamp" in sys.argv:
            try:
                ts_index = sys.argv.index("--timestamp") + 1
                if ts_index < len(sys.argv):
                    session_timestamp = sys.argv[ts_index]
                    # Remove from argv so it doesn't confuse other parsers
                    sys.argv.pop(ts_index)
                    sys.argv.pop(ts_index - 1)
            except ValueError:
                pass
                
        # Remove the crawler mode flag from argv
        if "--crawler-run" in sys.argv:
            sys.argv.remove("--crawler-run")
        
        # Run crawler loop directly
        # Note: run_crawler_loop handles its own exceptions
        from core.crawler_loop import run_crawler_loop
        config = Config(session_timestamp=session_timestamp)
        run_crawler_loop(config)
        return
    
    # Use parse_known_args to allow subcommands to pass through
    parser = argparse.ArgumentParser(description="Appium Traverser CLI", add_help=False)
    from domain.providers.registry import ProviderRegistry
    valid_providers = ProviderRegistry.get_all_names()
    parser.add_argument("--provider", type=str, default=None, help=f"AI provider to use ({', '.join(valid_providers)})")
    parser.add_argument("--model", type=str, default=None, help="Model name/alias to use")
    parser.add_argument("--help", "-h", action="store_true", help="Show help message")
    
    args, unknown = parser.parse_known_args()

    config = Config()

    # Set provider if given
    provider = args.provider or config.get("AI_PROVIDER")
    
    # Only prompt for provider if no subcommand is being run and it's not a help request
    if not provider and not unknown and not args.help:
        provider = input(f"Select AI provider ({', '.join(valid_providers)}): ").strip().lower()
    
    if provider:
        from domain.providers.enums import AIProvider
        try:
            # Validate provider using enum
            provider_enum = AIProvider.from_string(provider)
            config.set("AI_PROVIDER", provider_enum.value)
        except ValueError as e:
            print(f"[ERROR] {e}")
            sys.exit(1)

    # Set model if given
    if args.model:
        config.set("DEFAULT_MODEL_TYPE", args.model)

    # Pass through all unknown args (including subcommands and their --help)
    # Reconstruct sys.argv with script name + unknown args
    sys.argv = [sys.argv[0]] + unknown
    
    # Run CLI
    run()

if __name__ == "__main__":
    main()
