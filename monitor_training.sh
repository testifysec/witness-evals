#!/bin/bash
# Monitor MLX training progress
# Checks every 5 minutes and logs progress

LOG_FILE="/Users/nkennedy/proj/witness-evals/training_progress.log"
MODEL_DIR="/Users/nkennedy/proj/witness-evals/witness-llama-3.2-3b-verified-10k"

echo "Witness Expert Model Training Monitor" > "$LOG_FILE"
echo "Started: $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

for i in {1..20}; do  # Check up to 20 times (100 minutes max)
    echo "[$(date +%H:%M:%S)] Check #$i" >> "$LOG_FILE"

    # Check if model directory exists and has checkpoints
    if [ -d "$MODEL_DIR" ]; then
        echo "  Model directory exists" >> "$LOG_FILE"

        # List checkpoint files
        CHECKPOINTS=$(ls "$MODEL_DIR"/*.safetensors 2>/dev/null | wc -l)
        echo "  Checkpoints: $CHECKPOINTS" >> "$LOG_FILE"

        # Check for final adapters.safetensors (indicates completion)
        if [ -f "$MODEL_DIR/adapters.safetensors" ]; then
            echo "  ✅ TRAINING COMPLETE!" >> "$LOG_FILE"
            echo "" >> "$LOG_FILE"
            echo "Final model saved to: $MODEL_DIR" >> "$LOG_FILE"
            echo "Completed at: $(date)" >> "$LOG_FILE"
            echo "" >> "$LOG_FILE"
            echo "Next steps:" >> "$LOG_FILE"
            echo "  1. Test the model: cd /Users/nkennedy/proj/witness-evals && source venv-mlx/bin/activate" >> "$LOG_FILE"
            echo "  2. mlx_lm.generate --model witness-llama-3.2-3b-verified-10k --prompt \"How do I use witness?\"" >> "$LOG_FILE"
            break
        fi
    else
        echo "  Waiting for training to start..." >> "$LOG_FILE"
    fi

    echo "" >> "$LOG_FILE"

    # Wait 5 minutes before next check
    sleep 300
done

echo "" >> "$LOG_FILE"
echo "Monitor ended: $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"
