# GPT-oss-20b Testing Log

## Configuration
- **Model**: gpt-oss-20b-UD-Q6_K_XL.gguf (12GB)
- **GPU**: CUDA1,CUDA2 (2x RTX 4090 24GB)
- **Server flags**: `--temp 0.6 --top-p 0.95 --top-k 20 --min-p 0.00 --ctx-size 32000 -fa on --cache-type-k q4_0 --cache-type-v q4_0 --n-gpu-layers 99 --fit off --reasoning off --parallel 3 --jinja`
- **Client params**: temperature=0.2, top_p=0.5, top_k=10, seed=42, max_tokens=8000
- **Started**: 2025-08-05 09:03 UTC

## Baseline Comparisons (from previous testing)
| Model | Match % | Avg Time | Notes |
|-------|---------|----------|-------|
| Gemma 4 12B Q4_K | 49.1% (28/57) | 55.5s | Best stable model |
| Gemma 4 26B Q4_K | 31.6% (18/57) | 39.7s | Bien-biased |
| Qwen3.5-9B Q4_K | 33.9% (19/57) | 62.9s | Mal-biased |
| Qwen 3.6 27B Q4_K | 68.4% (39/57) | 150s | CUDA0, gold standard |

## Test 1: Full batch (57 notebooks, 32k ctx, concurrent workers=3)
- **Date**: 2025-08-05 09:10 UTC
- **Duration**: ~11.7 min
- **Result**: 35.1% match (20/57)
- **Avg time**: 123s (min: 32.5s, max: 238.3s)
- **Grade distribution**: 5 Excepcional, 20 Bien, 26 Regular, 6 Mal
- **Per-task**:
  - numpy_i (rubric): 5/7 = 71.4%
  - numpy_ii (rubric): 11/30 = 36.7%
  - euro12 (NO rubric): 1/9 = 11.1%
  - logistic_regression (NO rubric): 3/11 = 27.3%
- **Server status**: Stable, still running after 58 min

## Observations
1. Server crash investigation: OLD server (110k ctx) got clean SIGTERM, not crash. Likely bash session disconnect. New server (32k ctx) stable 58+ min.
2. GPT-oss heavily biased toward "Regular" (26/57 = 45.6%)
3. Without rubrics, match rate collapses (euro12: 11.1%, logistic_regression: 27.3%)
4. With rubrics, performance is decent (numpy_i: 71.4%, numpy_ii: 36.7%)
5. Overall 35.1% is WORSE than Gemma 12B (49.1%) - rubric bias drags down non-rubric tasks
6. GPT-oss generates 8-10k tokens per response (ignores max_tokens=8000)

## TODO
- [ ] Test numpy_i + numpy_ii only (37 notebooks with rubrics) for fair comparison
- [ ] Test with 110k context to check if it actually causes instability
- [ ] Test with --max-output-token to cap token generation
- [ ] Compare GPT-oss rubric-only vs Gemma 12B rubric-only

## Test 2: Numpy-only (37 notebooks, rubrics only)
- **Started**: 2025-08-05 ~10:00 UTC
- **Status**: Running in background (PID 3237735)
- **Purpose**: Fair comparison - only notebooks with rubrics

## Test 3: GPT-oss-20b vs Gemma 4 12B head-to-head
- **Started**: 2025-08-05 ~10:05 UTC
- **Status**: Running in background (PID 3239519)
- **Setup**: GPT-oss on :8084, Gemma 12B on :8085
- **Purpose**: Direct comparison on same 37 numpy notebooks
- **Expected duration**: ~1.5 hours (37 notebooks × 2 models × ~100s avg)

## Server Status
- GPT-oss-20b (PID 3208243): Running 1h42m+, stable, 32k ctx
- Gemma 4 12B (PID 3239010): Running, 32k ctx
