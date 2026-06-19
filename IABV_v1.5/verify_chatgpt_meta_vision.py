"""
Meta-Vision Proof: ChatGPT Real Interface Audit

This script attempts to:
1. Scan for open windows on the system
2. Detect if ChatGPT is open in a browser
3. Analyze the UI structure
4. Build UI Knowledge Graph
5. Generate Navigation Graph
6. Attempt to interact with the interface (if possible)
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from iabv_v15.services.perception.runtime_perception_and_verification_service import (
    RuntimePerceptionAndVerificationService,
    SurfaceObservation,
    SurfaceType,
    SurfaceState
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    logger.info("=== Meta-Vision Proof: ChatGPT Real Interface Audit ===")
    logger.info("Timestamp: %s", datetime.now(timezone.utc).isoformat())
    
    # Initialize the perception service
    try:
        perception_service = RuntimePerceptionAndVerificationService()
        logger.info("RuntimePerceptionAndVerificationService initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize RuntimePerceptionAndVerificationService: %s", e)
        return
    
    # Scan for open windows
    logger.info("Scanning for open windows...")
    try:
        # Use the internal _scan_surfaces method (it's private but accessible)
        observations = perception_service._scan_surfaces()
        logger.info("Found %d surface observations", len(observations))
        
        # Check if ChatGPT is open
        chatgpt_found = False
        chatgpt_observation = None
        
        for obs in observations:
            logger.info("Surface: %s - %s (PID: %s)", 
                       obs.surface_title, obs.app_name, obs.process_id)
            
            # Check if this is ChatGPT
            if "chatgpt" in obs.surface_title.lower() or "chatgpt" in obs.app_name.lower():
                chatgpt_found = True
                chatgpt_observation = obs
                logger.info("FOUND ChatGPT: %s", obs.surface_title)
        
        if not chatgpt_found:
            logger.warning("ChatGPT NOT FOUND in open windows")
            logger.info("Cannot proceed with meta-vision audit - ChatGPT is not open")
            logger.info("Please open ChatGPT in your browser and run this script again")
            return
        
        # Analyze ChatGPT window
        logger.info("=== Analyzing ChatGPT Window ===")
        logger.info("Surface ID: %s", chatgpt_observation.surface_id)
        logger.info("Surface Title: %s", chatgpt_observation.surface_title)
        logger.info("App Name: %s", chatgpt_observation.app_name)
        logger.info("Process ID: %s", chatgpt_observation.process_id)
        logger.info("Surface Type: %s", chatgpt_observation.surface_type)
        logger.info("Surface State: %s", chatgpt_observation.surface_state)
        
        # Try to get UI structure
        logger.info("Attempting to get UI structure...")
        try:
            ui_structure = perception_service.get_ui_structure(chatgpt_observation.surface_id)
            logger.info("UI Structure retrieved: %d elements", len(ui_structure.get('elements', [])))
            
            # Build UI Knowledge Graph
            logger.info("Building UI Knowledge Graph...")
            ui_knowledge_graph = perception_service.build_ui_knowledge_graph(ui_structure)
            logger.info("UI Knowledge Graph built: %d elements", len(ui_knowledge_graph.get('elements', {})))
            
            # Generate Navigation Graph
            logger.info("Generating Navigation Graph...")
            navigation_graph = perception_service.generate_navigation_graph(ui_knowledge_graph)
            logger.info("Navigation Graph generated: %d states, %d transitions", 
                       len(navigation_graph.get('states', {})), 
                       len(navigation_graph.get('transitions', {})))
            
            # Save results
            output_dir = Path("data/meta_vision_audit")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            with open(output_dir / "chatgpt_observation.json", "w") as f:
                json.dump({
                    "observation": chatgpt_observation.__dict__,
                    "ui_structure": ui_structure,
                    "ui_knowledge_graph": ui_knowledge_graph,
                    "navigation_graph": navigation_graph
                }, f, indent=2, default=str)
            
            logger.info("Results saved to %s", output_dir / "chatgpt_observation.json")
            
        except Exception as e:
            logger.error("Failed to get UI structure or build graphs: %s", e)
            logger.info("This is expected - the IABV system may not have full UI analysis capabilities for web browsers")
        
        # Try to interact with ChatGPT (if possible)
        logger.info("=== Attempting Interaction ===")
        logger.info("NOTE: I cannot actually interact with the browser - this is a limitation of my environment")
        logger.info("I can only OBSERVE what is already open, not CONTROL it")
        
    except Exception as e:
        logger.error("Error during surface scanning: %s", e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
