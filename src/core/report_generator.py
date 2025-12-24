import json
import datetime
from typing import Dict, List

class ReportGenerator:
    """Generate comprehensive verification reports"""
    
    @staticmethod
    def generate_markdown_report(verification_stats: Dict) -> str:
        """Generate markdown report"""
        report = "# Neuro-Symbolic Verification Framework Report\n\n"
        
        # Timestamp
        report += f"**Generated**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # Executive Summary
        report += "## Executive Summary\n\n"
        total = verification_stats.get("total_verifications", 0)
        passed = verification_stats.get("successful_verifications", 0)
        failed = verification_stats.get("failed_verifications", 0)
        
        report += f"- **Total Specifications**: {total}\n"
        report += f"- **Successfully Verified**: {passed}\n"
        report += f"- **Failed**: {failed}\n"
        
        if total > 0:
            success_rate = (passed / total) * 100
            report += f"- **Success Rate**: {success_rate:.1f}%\n"
        report += f"- **Average Iterations**: {verification_stats.get('average_iterations', 0):.2f}\n\n"
        
        # Model Performance
        report += "## Model Performance\n\n"
        report += "| Model | Generation Success | Verification Success | Total Attempts |\n"
        report += "|-------|-------------------|---------------------|----------------|\n"
        
        model_perf = verification_stats.get("model_performance", {})
        for model_name, stats in model_perf.items():
            gen_rate = (stats.get("valid_syntax_count", 0) / max(1, stats.get("generation_attempts", 1))) * 100
            verify_rate = (stats.get("verification_success", 0) / max(1, stats.get("verification_attempts", 1))) * 100
            report += f"| {model_name} | {gen_rate:.1f}% | {verify_rate:.1f}% | {stats.get('verification_attempts', 0)} |\n"
        
        report += "\n"
        
        # Detailed Results
        report += "## Detailed Results\n\n"
        
        for spec_result in verification_stats.get("detailed_results", []):
            report += f"### {spec_result.get('specification_id', 'Unknown')}\n\n"
            report += f"**Requirement**: {spec_result.get('requirement', 'N/A')}\n\n"
            report += f"**Result**: {'✅ PASSED' if spec_result.get('verification_passed') else '❌ FAILED'}\n\n"
            report += f"**Iterations**: {spec_result.get('iterations', 0)}\n\n"
            
            if spec_result.get('final_code'):
                report += "**Final Code**:\n```python\n"
                report += f"{spec_result['final_code']}\n"
                report += "```\n\n"
            
            # Model outputs
            if spec_result.get('model_outputs'):
                report += "**Model Outputs (First Iteration)**:\n\n"
                for model_name, code in spec_result['model_outputs'].items():
                    if code:
                        report += f"- **{model_name}**:\n```python\n{code[:200]}...\n```\n\n"
        
        return report
    
    @staticmethod
    def save_report(verification_stats: Dict, format: str = "both"):
        """Save report in multiple formats"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save JSON
        if format in ["json", "both"]:
            json_filename = f"verification_report_{timestamp}.json"
            with open(json_filename, 'w') as f:
                json.dump(verification_stats, f, indent=2, default=str)
            print(f"✅ JSON report saved: {json_filename}")
        
        # Save Markdown
        if format in ["markdown", "both"]:
            md_filename = f"verification_report_{timestamp}.md"
            md_report = ReportGenerator.generate_markdown_report(verification_stats)
            with open(md_filename, 'w') as f:
                f.write(md_report)
            print(f"✅ Markdown report saved: {md_filename}")