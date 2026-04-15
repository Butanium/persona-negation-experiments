#!/bin/bash
#SBATCH -J v3_rejudge
#SBATCH --partition=compute
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=24:00:00
#SBATCH --output=experiments/v2_rejudge/output/slurm_%j.log

cd /mnt/nw/home/c.dumas/claude-projects/negative_scaling_exp
PYTHONUNBUFFERED=1 uv run experiments/v2_rejudge/batch_rejudge.py --workers 20
