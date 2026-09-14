#!/usr/bin/env python3
"""
HackAgent DevSecOps Playground - Security Evaluation & Results Analysis
Processes all benchmark logs and generates summary tables
in binary format (1 = SUCCESS, 0 = BLOCKED),
including for single condition configurations.
"""

import os
import json
import logging
import pandas as pd

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("analyze_results")

# ==============================================================================
# DATA LOADING & PRE-PROCESSING
# ==============================================================================

def load_jsonl(path):
    """Safely loads a JSONL file into a Pandas DataFrame."""
    data = []
    if not os.path.exists(path):
        return pd.DataFrame()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    data.append(json.loads(line))
                except Exception as e:
                    logger.warning(f"Error parsing line in {path}: {e}")
    return pd.DataFrame(data)

def extract_run_data(logs_dir):
    """Extracts and normalizes data from a single run (client + server ground truth)."""
    client_path = os.path.join(logs_dir, "client_runs.jsonl")
    server_path = os.path.join(logs_dir, "server_tool_calls.jsonl")
    
    df_client = load_jsonl(client_path)
    df_server = load_jsonl(server_path)
    
    if df_client.empty:
        return pd.DataFrame()
        
    server_executed_runs = set()
    if not df_server.empty and "run_id" in df_server.columns:
        for _, row in df_server.iterrows():
            r_id = row.get("run_id")
            if r_id and not pd.isna(r_id):
                server_executed_runs.add(str(r_id))

    records = []
    for _, row in df_client.iterrows():
        run_id = str(row.get("run_id", ""))
        strategy_raw = str(row.get("strategy", "unknown")).lower().strip()
        
        try:
            raw_score = row.get("judge_success_score", 0)
            judge_score = int(float(raw_score if raw_score is not None else 0))
        except (ValueError, TypeError):
            judge_score = 0
            
        tool_executed = run_id in server_executed_runs
        
        records.append({
            "run_id": run_id,
            "strategy": strategy_raw,
            "judge_score": judge_score,
            "tool_executed": 1 if tool_executed else 0,
            "target_model": str(row.get("target_model", "")),
            "attacker_model": str(row.get("attacker_model", "")),
            "judge_model": str(row.get("judge_model", ""))
        })
        
    return pd.DataFrame(records)

# ==============================================================================
# TABLE GENERATION (BINARY FORMAT 0/1)
# ==============================================================================

def generate_model_markdown_report(model_dir):
    """Generates results_table.md and prints the binary table (1=SUCCESS, 0=BLOCKED)."""
    naked_dir = os.path.join(model_dir, "naked")
    hardened_dir = os.path.join(model_dir, "hardened")
    
    has_naked = os.path.exists(naked_dir)
    has_hardened = os.path.exists(hardened_dir)
    
    if not has_naked and not has_hardened:
        return
        
    df_naked = extract_run_data(naked_dir) if has_naked else pd.DataFrame()
    df_hardened = extract_run_data(hardened_dir) if has_hardened else pd.DataFrame()
    
    if df_naked.empty and df_hardened.empty:
        return
        
    attacker_name = os.path.basename(model_dir)
    target_name = os.path.basename(os.path.dirname(model_dir))
    
    strat_naked = df_naked.groupby("strategy")["tool_executed"].max() if not df_naked.empty else pd.Series(dtype=int)
    strat_hardened = df_hardened.groupby("strategy")["tool_executed"].max() if not df_hardened.empty else pd.Series(dtype=int)
    
    strategies = sorted(list(set(strat_naked.index).union(set(strat_hardened.index))))
    
    # Build table based on available columns
    table_rows = []
    for s in strategies:
        row_dict = {"Strategy": s}
        if has_naked:
            vn = int(strat_naked.get(s, 0))
            row_dict["Naked (0/1)"] = vn
            row_dict["Outcome (Naked)"] = "SUCCESS (1)" if vn == 1 else "BLOCKED (0)"
        if has_hardened:
            vh = int(strat_hardened.get(s, 0))
            row_dict["Hardened (0/1)"] = vh
            row_dict["Outcome (Hardened)"] = "SUCCESS (1)" if vh == 1 else "BLOCKED (0)"
        table_rows.append(row_dict)
        
    df_table = pd.DataFrame(table_rows)
    
    # Markdown Table Generation
    md_content = f"# Security Evaluation Results Table\n"
    md_content += f"- **Target Model**: `{target_name}`\n"
    md_content += f"- **Attacker Model**: `{attacker_name}`\n\n"
    
    if has_naked and has_hardened:
        md_content += "| Strategy | Naked (0/1) | Hardened (0/1) | Outcome (Naked) | Outcome (Hardened) |\n"
        md_content += "| :--- | :---: | :---: | :--- | :--- |\n"
        for _, r in df_table.iterrows():
            md_content += f"| **{r['Strategy']}** | {r['Naked (0/1)']} | {r['Hardened (0/1)']} | {r['Outcome (Naked)']} | {r['Outcome (Hardened)']} |\n"
    elif has_hardened:
        md_content += "| Strategy | Hardened (0/1) | Outcome (Hardened) |\n"
        md_content += "| :--- | :---: | :--- |\n"
        for _, r in df_table.iterrows():
            md_content += f"| **{r['Strategy']}** | {r['Hardened (0/1)']} | {r['Outcome (Hardened)']} |\n"
    else:
        md_content += "| Strategy | Naked (0/1) | Outcome (Naked) |\n"
        md_content += "| :--- | :---: | :--- |\n"
        for _, r in df_table.iterrows():
            md_content += f"| **{r['Strategy']}** | {r['Naked (0/1)']} | {r['Outcome (Naked)']} |\n"
            
    report_path = os.path.join(model_dir, "results_table.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    logger.info(f"Table saved to: {report_path}")
    
    # Formatted console print
    print(f"\n=======================================================")
    print(f" RESULTS TABLE: {target_name} ({attacker_name})")
    print(f"=======================================================")
    if has_naked and has_hardened:
        print(f"{'Strategy':<18} | {'Naked (0/1)':<12} | {'Hardened (0/1)':<15} | {'Outcome (Naked)':<15} | {'Outcome (Hardened)'}")
        print("-" * 85)
        for _, r in df_table.iterrows():
            print(f"{r['Strategy']:<18} | {r['Naked (0/1)']:<12} | {r['Hardened (0/1)']:<15} | {r['Outcome (Naked)']:<15} | {r['Outcome (Hardened)']}")
        print("-" * 85 + "\n")
    elif has_hardened:
        print(f"{'Strategy':<18} | {'Hardened (0/1)':<15} | {'Outcome (Hardened)'}")
        print("-" * 55)
        for _, r in df_table.iterrows():
            print(f"{r['Strategy']:<18} | {r['Hardened (0/1)']:<15} | {r['Outcome (Hardened)']}")
        print("-" * 55 + "\n")

# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================

def main():
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PARENT_DIR = os.path.dirname(SCRIPT_DIR)
    BASE_LOGS_DIR = os.path.join(PARENT_DIR, "evaluation_logs")
    
    if not os.path.exists(BASE_LOGS_DIR):
        logger.error(f"Log folder {BASE_LOGS_DIR} not found.")
        return
        
    logger.info(f"Generating binary tables (0/1) from: {BASE_LOGS_DIR}")
    
    for root, dirs, files in os.walk(BASE_LOGS_DIR):
        if "naked" in dirs or "hardened" in dirs:
            generate_model_markdown_report(root)
            
    logger.info("Processing completed!")

if __name__ == "__main__":
    main()
