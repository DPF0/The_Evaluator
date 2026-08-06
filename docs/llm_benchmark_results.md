# LLM Model Evaluation Benchmark

**The Evaluator** — Automated notebook grader for Data Science bootcamp assignments.

## Test Procedure

### Fixed Test Set
- **31 notebooks** from 16 students (NumPy I + NumPy II assignments)
- All notebooks have **Deepseek-R1-32B** reference grades (ground truth)
- Source: `tests/test_set.csv`
- Tasks: 16 NumPy I, 15 NumPy II

### Rubrics
| Task | Rubric |
|------|--------|
| numpy_i | `rubrics/rubric_numpy_i.md` |
| numpy_ii | `rubrics/rubric_numpy_ii.md` |

### Infrastructure
- **Server**: 192.168.0.37 (local)
- **GPUs**: CUDA1 (RTX 2060 12GB) + CUDA2 (RTX 2060 12GB)
- **CUDA0**: Reserved (Titan RTX 24GB, user's main server)

### Server Configuration (all models)
| Parameter | Value |
|-----------|-------|
| temp | 0.6 |
| top_p | 0.95 |
| top_k | 64 (20 for GPT-oss) |
| min_p | 0.00 |
| ctx_size | 32000 |
| cache_type_k | q4_0 |
| cache_type_v | q4_0 |
| n_gpu_layers | 99 |
| parallel | 3 |
| flash_attn | on |

### LLM Client Parameters
| Parameter | Value |
|-----------|-------|
| temperature | 0.2 |
| top_p | 0.5 |
| top_k | 10 |
| seed | 42 |
| max_tokens | 8000 |
| timeout | 300s |

### Evaluation Modes
- **Dual-instance** (8084+8085): `ThreadPoolExecutor(2)` — both GPUs run concurrently
- **Split** (CUDA1,CUDA2): Sequential — single server split across both GPUs

### Grade Scale
| Categorical | Numeric |
|-------------|---------|
| Mal | 3 |
| Regular | 5 |
| Bien | 7 |
| Excepcional | 9 |

### Match Rate
Percentage of grades matching Deepseek-R1-32B reference. Higher = better alignment.

## Models Tested

| # | Model | Quant | Size | Mode | GPU |
|---|-------|-------|------|------|-----|
| 1 | Gemma 4 12B Q4_K | Q4_K | 6.3GB | Dual instance | CUDA1 + CUDA2 |
| 2 | Gemma 4 26B Q4_K | Q4_K | 16GB | Split | CUDA1,CUDA2 |
| 3 | GPT-oss 20B Q6_K | Q6_K | 12GB | Split | CUDA1,CUDA2 |
| 4 | Qwen3.5 9B Q4_K | Q4_K | 5.8GB | Dual instance | CUDA1 + CUDA2 |
| 5 | Qwen3.6 35B Q4_K | Q4_K | 21GB | Split | CUDA1,CUDA2 |
| 6 | Gemma 4 12B FT Q4_K_M | Q4_K_M | 6.9GB | Dual instance | CUDA1 + CUDA2 |
| 7 | Qwen3-Coder 30B Q4_K | Q4_K | 21GB | Split | CUDA1,CUDA2 |

### Model Sources
- Gemma 4 12B: `~/Applications/models/Gemma_4_12B/gemma-4-12B-it-qat-UD-Q4_K_XL.gguf`
- Gemma 4 26B: `~/Applications/models/Gemma_4_26B/gemma-4-26B-A4B-it-UD-Q4_K_XL.gguf`
- GPT-oss 20B: `~/Applications/models/GPT_OSS_20B/gpt-oss-20b-UD-Q6_K_XL.gguf`
- Qwen3.5 9B: `~/Applications/models/Qwen3_5_9B/Qwen3.5-9B-UD-Q4_K_XL.gguf`
- Qwen3.6 35B: `~/Applications/models/Qwen3_6_35B/Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf`
- Gemma 4 12B FT: `~/Applications/models/Gemma_4_12B/gemma4-v2-Q4_K_M.gguf` ([yuxinlu1/gemma-4-12B-agentic-fable5-composer2.5-v2-3.5x-tau2](https://huggingface.co/yuxinlu1/gemma-4-12B-agentic-fable5-composer2.5-v2-3.5x-tau2-GGUF))
- Qwen3-Coder 30B: `~/Applications/models/Qwen3_Coder/Qwen3-Coder-30B-A3B-Instruct-UD-Q4_K_XL.gguf` ([unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF](https://huggingface.co/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF))

## Results

### Summary (sorted by match rate)

| Rank | Model | Inst | Match | Eff s/nb | Nb/min | Total Wall | Bien | Reg | Mal | Exc |
|------|-------|------|-------|----------|--------|------------|------|-----|-----|-----|
| 1 | Gemma 4 12B Q4_K | 2 | 80.6% | 12.7s | 2.37 | 786s | 9 | 19 | 3 | 0 |
| 2 | Qwen3-Coder 30B Q4_K | 1 | 74.2% | 14.4s | 4.17 | 446s | 15 | 15 | 1 | 0 |
| 3 | Gemma 4 26B Q4_K | 1 | 71.0% | 15.6s | 3.86 | 482s | 20 | 8 | 3 | 0 |
| 4 | GPT-oss 20B Q6_K | 1 | 51.6% | 65.0s | 0.92 | 2014s | 9 | 14 | 4 | 4 |
| 5 | Qwen3.6 35B Q4_K | 1 | 48.4% | 27.5s | 2.18 | 852s | 6 | 17 | 7 | 1 |
| 6 | Gemma 4 12B FT Q4_K_M | 2 | 41.9% | 12.0s | 2.50 | 743s | 11 | 4 | 15 | 1 |
| 7 | Qwen3.5 9B Q4_K | 2 | 16.1% | 17.7s | 1.70 | 1095s | 3 | 10 | 17 | 1 |

### Metrics
- **Match**: % of grades matching Deepseek-R1-32B reference
- **Eff s/nb**: Wall-clock time per notebook divided by instances (normalized compute cost)
- **Nb/min**: Throughput rate (notebooks graded per wall-clock minute)
- **Total Wall**: Total wall-clock time to complete all 31 notebooks

### Per-Task Breakdown

| Model | NumPy I | NumPy II |
|-------|---------|----------|
| Gemma 4 12B Q4_K | 87.5% (14/16) | 73.3% (11/15) |
| Qwen3-Coder 30B Q4_K | 81.2% (13/16) | 66.7% (10/15) |
| Gemma 4 26B Q4_K | 75.0% (12/16) | 66.7% (10/15) |
| GPT-oss 20B Q6_K | 50.0% (8/16) | 53.3% (8/15) |
| Qwen3.6 35B Q4_K | 50.0% (8/16) | 46.7% (7/15) |
| Gemma 4 12B FT Q4_K_M | 43.8% (7/16) | 40.0% (6/15) |
| Qwen3.5 9B Q4_K | 18.8% (3/16) | 13.3% (2/15) |

### Grade Distribution Heatmap

| Model | Excepcional | Bien | Regular | Mal |
|-------|-------------|------|---------|-----|
| Gemma 4 12B Q4_K | 0 | 9 | 19 | 3 |
| Qwen3-Coder 30B Q4_K | 0 | 15 | 15 | 1 |
| Gemma 4 26B Q4_K | 0 | 20 | 8 | 3 |
| GPT-oss 20B Q6_K | 4 | 9 | 14 | 4 |
| Qwen3.6 35B Q4_K | 1 | 6 | 17 | 7 |
| Gemma 4 12B FT Q4_K_M | 1 | 11 | 4 | 15 |
| Qwen3.5 9B Q4_K | 1 | 3 | 10 | 17 |

## Key Findings

1. **Gemma 4 12B Q4_K** is the best overall model: highest match rate (80.6%) with excellent effective speed (12.7s/nb).
2. **Qwen3-Coder 30B Q4_K** is the best single-instance model: 74.2% match at 14.4s/nb effective, highest throughput (4.17 nb/min).
3. **Gemma 4 26B Q4_K** is competitive: 71.0% match at 15.6s/nb, very fast single-instance option.
4. **GPT-oss 20B Q6_K** is slow (65s/nb) with moderate accuracy (51.6%).
5. **Qwen3.6 35B Q4_K** shows Regular-bias (48.4% match, 17/31 Regular).
6. **Gemma 4 12B FT** (fine-tuned) underperforms badly: 41.9% match, heavily Mal-biased (15/31 Mal).
7. **Qwen3.5 9B Q4_K** is unusable: 16.1% match, extremely Mal-biased (17/31 Mal).

## Test Runner

Located at `tests/run_test.py`.

### Usage
```bash
# Dual-instance model (concurrent)
python3 tests/run_test.py --model gemma_4_12b_q4k_inst1

# Split model (sequential)
python3 tests/run_test.py --model qwen3_coder_30b_q4k
```

### File Structure
```
tests/
├── test_set.csv              # Fixed test set (31 notebooks)
├── run_test.py               # Test runner
├── models/                   # Model configs
│   ├── gemma_4_12b_q4k_inst1.conf
│   ├── gemma_4_12b_q4k_inst2.conf
│   ├── gemma_4_12b_ft_q4km_inst1.conf
│   ├── gemma_4_12b_ft_q4km_inst2.conf
│   ├── gemma_4_26b_q4k.conf
│   ├── gpt_oss_20b_q6k.conf
│   ├── qwen3_5_9b_q4k_inst1.conf
│   ├── qwen3_5_9b_q4k_inst2.conf
│   ├── qwen3_6_35b_q4k.conf
│   └── qwen3_coder_30b_q4k.conf
└── results/
    └── runs.json             # Registered test results
```

## Run Metadata

| Run | Timestamp | Model | Match |
|-----|-----------|-------|-------|
| 1 | 2026-08-05T22:24:30.057078 | gemma_4_12b_q4k_inst1 | 80.6% |
| 2 | 2026-08-05T22:35:50.901304 | gemma_4_26b_q4k | 71.0% |
| 3 | 2026-08-06T00:25:03.699935 | gpt_oss_20b_q6k | 51.6% |
| 4 | 2026-08-06T00:53:12.861201 | qwen3_5_9b_q4k_inst1 | 16.1% |
| 5 | 2026-08-06T01:12:20.513698 | qwen3_6_35b_q4k | 48.4% |
| 6 | 2026-08-06T02:56:43.476883 | gemma_4_12b_ft_q4km_inst1 | 41.9% |
| 7 | 2026-08-06T03:09:02.354413 | qwen3_coder_30b_q4k | 74.2% |

---
*Generated 1785978542.3565567*
