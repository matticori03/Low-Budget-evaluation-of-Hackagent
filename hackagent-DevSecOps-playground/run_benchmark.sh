#!/bin/bash
# ==============================================================================
# FULL BENCHMARK AUTOMATION SCRIPT (MULTI-RUN & MULTI-TARGET)
# Attacker: huihui_ai/gemma-4-abliterated:12b
# Target: qwen2.5:7b and llama3.1:8b (Both Naked and Hardened)
# ==============================================================================

set -e

# Number of full runs to execute for each combination
NUM_RUNS=${1:-1}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
BANK_DIR="$PARENT_DIR/vulnerable-bank-agent"
HACKAGENT_DIR="$SCRIPT_DIR"

export ATTACKER_MODEL="huihui_ai/gemma-4-abliterated:12b"

# Function to cleanly stop the banking agent server if running on port 8000
stop_server() {
    echo "Stopping any existing Banking Agent server on port 8000..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    sleep 2
}

# Function to start the banking agent server with the correct environment
start_server() {
    local target=$1
    local hardening=$2
    
    stop_server
    echo "Starting Banking Agent server (Target: $target | Hardening: $hardening)..."
    
    cd "$BANK_DIR"
    source .venv/bin/activate
    
    export MODEL_NAME="$target"
    export ATTACKER_MODEL="$ATTACKER_MODEL"
    export SECURITY_HARDENING="$hardening"
    
    python server.py > "$HACKAGENT_DIR/server_bench.log" 2>&1 &
    SERVER_PID=$!
    
    echo "Waiting for server startup on http://localhost:8000..."
    sleep 4
}

echo "================================================================="
echo " STARTING MULTI-RUN BENCHMARK ($NUM_RUNS iterations per config)"
echo " Attacker: $ATTACKER_MODEL"
echo "================================================================="

# Trap to ensure the server is always stopped at the end or on ctrl-c
trap stop_server EXIT

TARGETS=("qwen2.5:7b" "llama3.1:8b")
HARDENING_MODES=("false" "true")

cd "$HACKAGENT_DIR"
source .venv/bin/activate

for target in "${TARGETS[@]}"; do
    for hardening in "${HARDENING_MODES[@]}"; do
        mode_label="Naked"
        if [ "$hardening" = "true" ]; then
            mode_label="Hardened"
        fi
        
        echo ""
        echo "-----------------------------------------------------------------"
        echo " TEST MATRIX: Target = $target | Mode = $mode_label"
        echo "-----------------------------------------------------------------"
        
        # Start the bank agent server for this combination
        start_server "$target" "$hardening"
        
        cd "$HACKAGENT_DIR"
        source "$HACKAGENT_DIR/.venv/bin/activate"
        export TARGET_MODEL="$target"
        export AGENT_HARDENING="$hardening"
        
        for ((run=1; run<=NUM_RUNS; run++)); do
            echo ">>> Executing Run $run / $NUM_RUNS for [$target | $mode_label]..."
            python run_suite_local.py
        done
    done
done

echo ""
echo "================================================================="
echo " BENCHMARK EXECUTION COMPLETED! GENERATING TABLES AND PLOTS..."
echo "================================================================="

cd "$HACKAGENT_DIR"
python analyze_results.py

echo ""
echo "✅ ALL PLOTS AND SUMMARY TABLES HAVE BEEN SUCCESSFULLY UPDATED!"
