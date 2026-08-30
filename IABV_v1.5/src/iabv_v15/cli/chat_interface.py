"""CLI chat interface for IABV without GUI.

Allows programmatic interaction with IABV for automated testing,
CI/CD integration, and headless operation.

IMPORTANT: All queries go through InferenceService to enforce
reflection routing and resource governance. Direct provider calls
are prohibited to prevent bypassing safety checks.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from uuid import uuid4

from iabv_v15.domain.models import InferenceRequest, TaskRole
from iabv_v15.infra.config import load_app_config
from iabv_v15.infra.logging import configure_logging

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    """Main entry point for CLI chat interface."""
    argv = list(argv or [])
    
    parser = argparse.ArgumentParser(
        prog="python -m iabv_v15 chat",
        description="CLI chat interface for IABV without GUI.",
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="Query to send to IABV. If not provided, starts interactive mode.",
    )
    parser.add_argument(
        "--workspace",
        default="C:\\Python\\IABV_v1.5",
        help="Workspace root directory (default: C:\\Python\\IABV_v1.5).",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Exit after processing query (no interactive mode).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    
    args = parser.parse_args(argv)
    
    # Load config first to get workspace
    workspace = Path(args.workspace)
    config = load_app_config(workspace)
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.getLogger().setLevel(log_level)
    configure_logging(logs_dir=str(workspace / "data" / "logs"))
    
    try:
        # Bootstrap IABV services (without UI)
        from iabv_v15.bootstrap import AppBootstrap
        
        bootstrap = AppBootstrap(workspace_root=str(workspace), _defer_services=False)
        logger.info("IABV services bootstrapped successfully")
        
        # Get inference service to enforce reflection routing and resource governance
        inference_service = bootstrap.inference_service
        if inference_service is None:
            logger.error("Inference service not available")
            return 1
        
        def process_query(query_text: str) -> str:
            """Process a query through the governed inference pipeline."""
            request = InferenceRequest(
                request_id=str(uuid4()),
                user_goal=query_text,
                task_role=TaskRole.KNOWLEDGE,
            )
            try:
                record = inference_service.infer_task(request)
                return record.result.summary or ""
            except Exception as e:
                logger.error(f"Inference failed: {e}")
                raise
        
        if args.query:
            # Single query mode
            logger.info(f"Processing query: {args.query}")
            try:
                response = process_query(args.query)
                print(response)
                return 0
            except Exception as e:
                logger.error(f"Error processing query: {e}")
                return 1
        elif args.non_interactive:
            logger.error("No query provided in non-interactive mode")
            return 1
        else:
            # Interactive mode
            print("IABV CLI Chat Interface")
            print("Type 'exit' or 'quit' to exit")
            print("-" * 40)
            
            while True:
                try:
                    query = input("You: ").strip()
                    if not query:
                        continue
                    if query.lower() in ("exit", "quit"):
                        print("Exiting...")
                        break
                    
                    logger.info(f"Processing query: {query}")
                    response = process_query(query)
                    print(f"IABV: {response}")
                    print()
                except KeyboardInterrupt:
                    print("\nExiting...")
                    break
                except Exception as e:
                    logger.error(f"Error processing query: {e}")
                    print(f"Error: {e}")
            
            return 0
    
    except Exception as e:
        logger.error(f"Failed to bootstrap IABV: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
