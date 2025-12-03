#!/usr/bin/env python3
"""
Main entry point for Neuro-Symbolic UAV Framework
Phase 1: LLM Ensemble with Z3 Pre-Check
"""
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.llm_ensemble.ensemble_manager import LLMEnsembleManager
from examples.demo_ensemble import demo_basic_ensemble, demo_refinement_loop
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

def run_single_verification():
    """Run single verification with ensemble"""
    
    print("Neuro-Symbolic UAV Framework - Single Verification")
    print("-" * 60)
    
    ensemble = LLMEnsembleManager()
    
    # Example safety requirement
    requirement = input("Enter requirement (or press Enter for default): ").strip()
    if not requirement:
        requirement = "The drone must maintain altitude between 40 and 60 meters."
    
    safety_property = "And(altitude >= 40, altitude <= 60)"
    variables = {"altitude": "real"}
    
    print(f"\nGenerating code for: {requirement}")
    print(f"Safety property: {safety_property}")
    
    candidates = ensemble.generate_ensemble(
        requirement=requirement,
        safety_property=safety_property,
        variables=variables
    )
    
    best = ensemble.select_best_candidate(candidates)
    
    print(f"\n✅ Best candidate from {best['model']}:")
    print(f"Z3 Pre-Check Score: {best.get('z3_score', 0):.3f}")
    print(f"\nGenerated Code:")
    print("-" * 40)
    print(best['code'])
    print("-" * 40)
    
    return best

def run_batch_verification():
    """Run batch verification on multiple requirements"""
    
    print("Neuro-Symbolic UAV Framework - Batch Verification")
    print("-" * 60)
    
    ensemble = LLMEnsembleManager()
    
    # Batch of safety requirements
    requirements = [
        {
            "id": "altitude_safety",
            "requirement": "The drone must maintain altitude between 40 and 60 meters.",
            "property": "And(altitude >= 40, altitude <= 60)",
            "variables": {"altitude": "real"}
        },
        {
            "id": "speed_safety",
            "requirement": "Speed must not exceed 10 m/s when obstacle within 20m.",
            "property": "Implies(distance < 20, speed <= 10)",
            "variables": {"speed": "real", "distance": "real"}
        },
        {
            "id": "grasp_safety",
            "requirement": "Robot must not grasp if already holding.",
            "property": "Implies(action == 'Grasp', Not(is_holding))",
            "variables": {"is_holding": "bool", "action": "string"}
        }
    ]
    
    results = []
    for req in requirements:
        print(f"\nProcessing: {req['id']}")
        
        candidates = ensemble.generate_ensemble(
            requirement=req["requirement"],
            safety_property=req["property"],
            variables=req["variables"]
        )
        
        best = ensemble.select_best_candidate(candidates)
        results.append({
            "id": req["id"],
            "model": best["model"],
            "z3_score": best.get("z3_score", 0),
            "success": best.get("success", False)
        })
        
        print(f"  Selected: {best['model']} (Z3: {best.get('z3_score', 0):.3f})")
    
    # Summary
    print("\n" + "=" * 60)
    print("BATCH VERIFICATION SUMMARY")
    print("=" * 60)
    
    for result in results:
        status = "✅" if result["z3_score"] > 0.6 else "⚠️ "
        print(f"{status} {result['id']}: {result['model']} (Z3: {result['z3_score']:.3f})")
    
    avg_score = sum(r["z3_score"] for r in results) / len(results)
    print(f"\nAverage Z3 Pre-Check Score: {avg_score:.3f}")
    
    return results

def show_ensemble_stats():
    """Show ensemble statistics"""
    
    print("Ensemble Statistics")
    print("-" * 60)
    
    ensemble = LLMEnsembleManager()
    stats = ensemble.get_stats()
    
    print(f"Total Models: {stats['total_models']}")
    print(f"Z3 Pre-Checks Enabled: {stats['z3_pre_checks_enabled']}")
    
    print("\nModel Details:")
    for model_name, model_stats in stats["models"].items():
        print(f"\n  {model_name}:")
        for key, value in model_stats.items():
            print(f"    {key}: {value}")

def main():
    """Main CLI interface"""
    
    parser = argparse.ArgumentParser(
        description="Neuro-Symbolic UAV Framework - Phase 1: LLM Ensemble"
    )
    
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run comprehensive demo"
    )
    
    parser.add_argument(
        "--single",
        action="store_true",
        help="Run single verification"
    )
    
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Run batch verification"
    )
    
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show ensemble statistics"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    print("\n" + "=" * 70)
    print("NEURO-SYMBOLIC UAV FRAMEWORK - PHASE 1")
    print("LLM Ensemble with Z3 Pre-Check")
    print("=" * 70 + "\n")
    
    if args.demo:
        # Run full demo
        from examples.demo_ensemble import main as demo_main
        return demo_main()
    
    elif args.single:
        run_single_verification()
    
    elif args.batch:
        run_batch_verification()
    
    elif args.stats:
        show_ensemble_stats()
    
    else:
        # Interactive mode
        print("Available modes:")
        print("  1. Single verification")
        print("  2. Batch verification")
        print("  3. Show ensemble statistics")
        print("  4. Run full demo")
        print("  0. Exit")
        
        choice = input("\nSelect mode (0-4): ").strip()
        
        if choice == "1":
            run_single_verification()
        elif choice == "2":
            run_batch_verification()
        elif choice == "3":
            show_ensemble_stats()
        elif choice == "4":
            from examples.demo_ensemble import main as demo_main
            demo_main()
        else:
            print("Exiting.")
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)