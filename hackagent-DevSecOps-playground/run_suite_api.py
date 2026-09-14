import os
import time
import json
import uuid
from loguru import logger

# configure timeouts so it doesn't hang forever
os.environ["LITELLM_TIMEOUT"] = "1200"
os.environ["REQUEST_TIMEOUT"] = "1200"
os.environ["OLLAMA_TIMEOUT"] = "1200"
os.environ["AIOHTTP_CLIENT_TIMEOUT"] = "1200"

# disable telemetry because it blocks threads and I hate it
os.environ["LITELLM_LOG"] = "ERROR"

import litellm
# force httpx timeout
litellm.request_timeout = 1200

# setup paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(SCRIPT_DIR)
BASE_LOGS_DIR = os.path.join(PARENT_DIR, "evaluation_logs")

AGENT_HARDENING: bool = os.environ.get("AGENT_HARDENING", "false").lower() == "true"
TARGET_MODEL: str = os.environ.get("TARGET_MODEL", "qwen2.5:7b")
ATTACKER_MODEL: str = os.environ.get("ATTACKER_MODEL", "zhipu/glm-5.2")

def get_safe_model_name(model_name: str) -> str:
    return model_name.replace(":", "_").replace("/", "_")

def get_eval_logs_dir(target_model: str, attacker_model: str) -> str:
    safe_target = get_safe_model_name(target_model)
    safe_attacker = get_safe_model_name(attacker_model)
    hardening_str = "hardened" if AGENT_HARDENING else "naked"
    return os.path.join(BASE_LOGS_DIR, safe_target, f"vs_{safe_attacker}", hardening_str)

# loguru setup, dumps to suite_runner.log
os.makedirs(BASE_LOGS_DIR, exist_ok=True)
logger.add(os.path.join(BASE_LOGS_DIR, "suite_runner.log"), rotation="10 MB")

from strategies.run_pair import run_attack as run_pair
from strategies.run_tap import run_attack as run_tap
from strategies.run_bon import run_attack as run_bon
from strategies.run_cipherchat import run_attack as run_cipherchat
from strategies.run_flipattack import run_attack as run_flipattack
from strategies.run_advprefix import run_attack as run_advprefix
from strategies.run_static_template import run_attack as run_static_template
from strategies.run_autodan_turbo import run_attack as run_autodan_turbo
from strategies.run_h4rm3l import run_attack as run_h4rm3l
from strategies.run_pap import run_attack as run_pap
from strategies.run_tfc import run_attack as run_tfc

# strategy map
STRATEGIES = {
    "pair": run_pair,
    "tap": run_tap,
    "bon": run_bon,
    "cipherchat": run_cipherchat,
    "flipattack": run_flipattack,
    "advprefix": run_advprefix,
    "static_template": run_static_template,
    "autodan_turbo": run_autodan_turbo,
    "h4rm3l": run_h4rm3l,
    "pap": run_pap,
    "tfc": run_tfc
}

def write_run_id(run_id: str, logs_dir: str):
    os.makedirs(logs_dir, exist_ok=True)
    path = os.path.join(logs_dir, ".current_run_id")
    with open(path, "w") as f:
        f.write(run_id)

def clear_run_id(logs_dir: str):
    path = os.path.join(logs_dir, ".current_run_id")
    if os.path.exists(path):
        os.remove(path)

def log_client_run(run_id, strategy_name, attacker, target, judge, results, logs_dir: str):
    path = os.path.join(logs_dir, "client_runs.jsonl")
    
    # Extract success score and prompt from the result if available
    judge_success_score = 0
    final_prompt = ""
    
    # Normalize results to a list
    results_list = []
    if isinstance(results, list):
        results_list = results
    elif isinstance(results, dict):
        if "results" in results and isinstance(results["results"], list):
            results_list = results["results"]
        elif "attack_log" in results and isinstance(results["attack_log"], list):
            results_list = results["attack_log"]
        elif "attack_results" in results and isinstance(results["attack_results"], list):
            results_list = results["attack_results"]
        else:
            results_list = [results]
    elif results:
        results_list = [results]
    
    for res in results_list:
        # Safely extract score and prompt
        current_score = 0
        current_prompt = ""
        
        if hasattr(res, "score"):
            current_score = float(res.score or 0)
            if hasattr(res, "prompt"):
                current_prompt = res.prompt
        elif isinstance(res, dict):
            current_score = float(res.get("score", 0) or 0)
            current_prompt = res.get("prompt", "")
            
        # Track the maximum score achieved and its prompt
        if current_score > judge_success_score:
            judge_success_score = current_score
            final_prompt = current_prompt
            
        # Early exit if we hit a perfect score
        if judge_success_score >= 1:
            break
    
    # Safe dump of the basic metadata
    entry = {
        "run_id": run_id,
        "timestamp": time.time(),
        "strategy": strategy_name,
        "attacker_model": attacker,
        "target_model": target,
        "judge_model": judge,
        "judge_success_score": judge_success_score,
        "final_prompt": final_prompt
    }
    
    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def main():
    # setup configs
    base_config = {
        "attacker_model": ATTACKER_MODEL,
        "judge_model": "llama3.1:8b",
        "target_model": TARGET_MODEL
    }

    #start from a specific test to reduce costs
    start_from = os.environ.get("START_FROM", "").lower().strip()
    all_strategies = list(STRATEGIES.keys())
    
    if start_from and start_from in all_strategies:
        start_idx = all_strategies.index(start_from)
        strategies_to_run = all_strategies[start_idx:]
        logger.info(f"Resuming tests starting from: '{start_from}' ({len(strategies_to_run)} tests remaining)")
    else:
        strategies_to_run = all_strategies

    test_configs = []
    for strategy in strategies_to_run:
        cfg = base_config.copy()
        cfg["strategy"] = strategy
        test_configs.append(cfg)

    # clear stale run ids
    for config in test_configs:
        logs_dir = get_eval_logs_dir(config.get("target_model", TARGET_MODEL), config.get("attacker_model", ATTACKER_MODEL))
        clear_run_id(logs_dir)

    logger.info(f"Starting Full Test Suite (run_suite_api): {len(test_configs)} tests scheduled with Attacker: {ATTACKER_MODEL}")

    for i, config in enumerate(test_configs):
        strategy = config["strategy"]
        run_id = str(uuid.uuid4())
        
        attacker_model = config.get("attacker_model")
        judge_model = config.get("judge_model")
        target_model = config.get("target_model")
        
        if not all([attacker_model, judge_model, target_model]):
            logger.error(f"Incomplete or malformed configuration in test {i+1}. Skipping.")
            continue
            
        logs_dir = get_eval_logs_dir(target_model, attacker_model)
        
        logger.info(f"--- Running Test {i+1}/{len(test_configs)} ---")
        logger.info(f"ID: {run_id} | Strategy: {strategy} | Target: {target_model} | Attacker: {attacker_model} | Hardening: {AGENT_HARDENING}")
        
        write_run_id(run_id, logs_dir)
        
        func = STRATEGIES.get(strategy)
        if not func:
            logger.error(f"Strategy {strategy} not found!")
            clear_run_id(logs_dir)
            continue
            
        try:
            results = func(
                attacker_model=attacker_model,
                judge_model=judge_model,
                target_model=target_model,
                run_id=run_id
            )
            logger.success(f"Test completed for ID: {run_id}")
            log_client_run(run_id, strategy, attacker_model, target_model, judge_model, results, logs_dir)
        except Exception as e:
            logger.exception(f"Error during test execution {run_id}: {e}")
        finally:
            clear_run_id(logs_dir)

if __name__ == "__main__":
    main()
