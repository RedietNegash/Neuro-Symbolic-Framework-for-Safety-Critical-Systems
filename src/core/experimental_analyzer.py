import time
from typing import Dict, List, Any

class ExperimentalAnalyzer:
    """Collects and formats experimental results for UAV verification research"""
    
    def __init__(self):
        self.results = {
            "individual_models": {}, # {model_name: {success_rate: 0, avg_time: 0, failures: []}}
            "neuro_symbolic": {
                "success_rate": 0,
                "avg_time": 0,
                "refinement_efficiency": 0,
                "failures": []
            },
            "ensemble": {
                "success_rate": 0,
                "avg_time": 0
            }
        }
        self.raw_data = []

    def log_result(self, category: str, spec_id: str, success: bool, duration: float, 
                  model_name: str = None, error_type: str = None, code: str = None):
        """Log a single experimental measurement"""
        entry = {
            "timestamp": time.time(),
            "category": category,
            "spec_id": spec_id,
            "success": success,
            "duration": duration,
            "model_name": model_name,
            "error_type": error_type,
            "code": code
        }
        self.raw_data.append(entry)

    def generate_report(self) -> str:
        """Generate a detailed summary report of experimental findings"""
        if not self.raw_data:
            return "No experimental data collected."

        report = "\n" + "="*80 + "\n"
        report += "FINAL RESEARCH EVALUATION SUMMARY\n"
        report += "="*80 + "\n"
        
        # Calculate aggregate stats for Neuro-Symbolic
        ns_data = [d for d in self.raw_data if d["category"] == "neuro_symbolic"]
        if ns_data:
            total = len(ns_data)
            successes = sum(1 for d in ns_data if d["success"])
            rate = (successes / total) * 100
            avg_time = sum(d["duration"] for d in ns_data) / total
            total_time = sum(d["duration"] for d in ns_data)
            
            # For iterations, we need to track them in log_result or infer them
            # Let's assume we might have logged more details or just use what we have
            report += f"Overall Success Rate: {rate:.1f}% ({successes}/{total})\n"
            report += f"Average Execution Time: {avg_time:.2f}s\n"
            report += f"Total Execution Time: {total_time:.2f}s\n"
        
        report += "\nCOMPARATIVE MODEL PERFORMANCE\n"
        report += "-"*80 + "\n"
        report += f"{'Model':<20} | {'Success Rate':<15} | {'Avg Time':<10} | {'Status'}\n"
        report += "-"*80 + "\n"
        
        models = set(d["model_name"] for d in self.raw_data if d["model_name"])
        for model in sorted(models):
            model_data = [d for d in self.raw_data if d["model_name"] == model]
            if not model_data: continue
            
            successes = sum(1 for d in model_data if d["success"])
            total = len(model_data)
            rate = (successes / total) * 100
            avg_time = sum(d["duration"] for d in model_data) / total
            
            status = "OPTIMAL" if rate > 80 else "NEEDS REFINEMENT"
            report += f"{model:<20} | {rate:>13.1f}% | {avg_time:>8.2f}s | {status}\n"

        report += "="*80 + "\n"
        return report
