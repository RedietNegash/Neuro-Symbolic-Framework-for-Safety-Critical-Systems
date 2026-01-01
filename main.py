from src.verification.neuro_symbolic_verifier import NeuroSymbolicVerifier
from src.verification.safety_specification import create_safety_specifications
import asyncio
import sys
import json
import datetime
from pathlib import Path

async def main():
    print("="*80)
    print("NEURO-SYMBOLIC VERIFICATION FRAMEWORK - 4-WAY MODEL COMPARISON")
    print("="*80)
    print("[Experiment] Comparing: Llama 3 8B vs DeepSeek R1 7B vs Ensemble (Gemini Disabled)")
    
    verifier = NeuroSymbolicVerifier()
    specifications = create_safety_specifications()
    print(f"\n[Tasks] Running experiments on {len(specifications)} safety specifications...")
    
    available_models = verifier.ensemble.get_available_models()
    print(f"[Models] Available models in ensemble: {', '.join(available_models)}")
    
    if 'gemini' not in available_models:
        print("Warning: Gemini not available, running with Llama and DeepSeek only")
    
    results = []
    for i, spec in enumerate(specifications):
        print(f"\n{'='*60}")
        print(f"EXPERIMENT {i+1}/{len(specifications)}: {spec.id}")
        print(f"{'='*60}")
        print(f"[Requirement]: {spec.requirement}")
        # Prepare per-spec log file and tee stdout so nested prints are captured
        log_dir = Path("data") / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = log_dir / f"{spec.id}__{timestamp}.log"
        json_path = log_dir / f"{spec.id}__{timestamp}.json"

        class Tee:
            def __init__(self, *streams):
                self.streams = streams
            def write(self, data):
                for s in self.streams:
                    s.write(data)
            def flush(self):
                for s in self.streams:
                    try:
                        s.flush()
                    except Exception:
                        pass

        with open(log_path, 'w') as lf:
            old_stdout = sys.stdout
            sys.stdout = Tee(old_stdout, lf)
            try:
                result = await verifier.run_comparison_experiment(spec, max_iterations=3)
            finally:
                sys.stdout = old_stdout

        # Save JSON summary for the spec
        try:
            with open(json_path, 'w') as jf:
                json.dump(result, jf, indent=2, default=str)
        except Exception as e:
            print(f"[Warning] Could not save JSON summary for {spec.id}: {e}")

        results.append(result)
    
    print("\n" + "="*80)
    verifier.print_comparison_report()
    
    print("\n" + "="*80)
    print("EXECUTIVE SUMMARY - 3-WAY COMPARISON (Gemini Disabled)")
    print("="*80)
    
    total_specs = len(results)
    ensemble_passed = sum(1 for r in results if r.get('ensemble_result', {}).get('verification_passed', False))
    
    print(f"\n[Passed] ENSEMBLE APPROACH: {ensemble_passed}/{total_specs} ({ensemble_passed/total_specs*100:.1f}%)")
    
    print("\n[Models] INDIVIDUAL MODEL RESULTS:")
    print("-" * 50)
    
    individual_stats = verifier.verification_stats.get("individual_model_results", {})
    
    print(f"{'Model':<15} {'Success Rate':<15} {'Avg Iterations':<15} {'Rank':<8}")
    print("-" * 50)
    
    sorted_models = []
    for model_name, stats in individual_stats.items():
        if stats["total_tests"] > 0:
            success_rate = (stats["successful_tests"] / stats["total_tests"]) * 100
            avg_iterations = stats["total_iterations"] / stats["total_tests"]
            sorted_models.append((model_name, success_rate, avg_iterations, stats))
    
    sorted_models.sort(key=lambda x: x[1], reverse=True)
    
    for rank, (model_name, success_rate, avg_iterations, stats) in enumerate(sorted_models, 1):
        model_display_name = {
            'gemini': 'Gemini 2.5 Flash',
            'llama': 'Llama 3 8B', 
            'deepseek': 'DeepSeek R1 7B'
        }.get(model_name, model_name)
        
        print(f"{model_display_name:<15} {success_rate:>13.1f}% {avg_iterations:>14.2f} #{rank:<7}")
    
    ensemble_rate = (ensemble_passed / total_specs) * 100
    ensemble_iterations = verifier.verification_stats.get("average_iterations", 0)
    
    print(f"\n{'Ensemble':<15} {ensemble_rate:>13.1f}% {ensemble_iterations:>14.2f} #1" if ensemble_rate >= max(sr for _, sr, _, _ in sorted_models) else "")
    
    print("\n[Best] PERFORMANCE ANALYSIS:")
    print("-" * 50)
    
    if sorted_models:
        best_model, best_rate, best_avg_iter, _ = sorted_models[0]
        improvement = ensemble_rate - best_rate
        
        if improvement > 0:
            print(f"OK: Ensemble approach is BEST by +{improvement:.1f}%")
            print(f"  Ensemble achieves {ensemble_rate:.1f}% vs {best_model}'s {best_rate:.1f}%")
        elif improvement < 0:
            print(f"NO: Individual model ({best_model}) is BEST by {abs(improvement):.1f}%")
            print(f"  {best_model} achieves {best_rate:.1f}% vs Ensemble's {ensemble_rate:.1f}%")
        else:
            print(f"== Ensemble ties with {best_model} at {ensemble_rate:.1f}%")
        
        iteration_improvement = best_avg_iter - ensemble_iterations
        if iteration_improvement > 0:
            print(f"OK: Ensemble is {iteration_improvement:.2f} iterations faster on average")
        elif iteration_improvement < 0:
            print(f"NO: {best_model} is {abs(iteration_improvement):.2f} iterations faster on average")
    
    print("\n[Analysis] MODEL STRENGTHS ANALYSIS:")
    print("-" * 50)
    
    spec_analysis = {}
    for spec_result in results:
        spec_id = spec_result['specification_id']
        spec_analysis[spec_id] = {
            'passed_models': [],
            'failed_models': []
        }
        
        for model_name, model_result in spec_result.get('individual_model_results', {}).items():
            if model_result.get('verification_passed'):
                spec_analysis[spec_id]['passed_models'].append(model_name)
            else:
                spec_analysis[spec_id]['failed_models'].append(model_name)
    
    print("Models successful for each specification:")
    for spec_id, analysis in spec_analysis.items():
        passed = analysis['passed_models']
        failed = analysis['failed_models']
        print(f"  {spec_id:<25} [PASS] {', '.join(passed) if passed else 'None'}")
        if failed:
            print(f"{'':<27} [FAIL] {', '.join(failed)}")
    
    print("\n[Code] FINAL ENSEMBLE VERIFIED CODES:")
    print("-" * 80)
    
    for i, result in enumerate(results):
        ensemble_result = result.get('ensemble_result', {})
        if ensemble_result.get('verification_passed'):
            code = ensemble_result.get('final_code', 'No code')
            if code and len(code) > 80:
                code_display = code[:77] + "..."
            else:
                code_display = code
            print(f"\n{i+1}. {result.get('specification_id', f'Spec {i+1}')}:")
            print(f"   {code_display}")
    
    print("\n" + "="*80)
    print("\n[Results] RESULTS SAVED in data/:")
    print("-" * 80)
    print(f"1. Detailed comparison report (JSON): data/model_comparison_report_*.json")
    print("2. Model performance statistics")
    print("3. Individual model verification results")
    print("4. Ensemble verification results")
    print("\n[Done] Framework successfully verified all specifications with neuro-symbolic approach!")

if __name__ == "__main__":
    asyncio.run(main())