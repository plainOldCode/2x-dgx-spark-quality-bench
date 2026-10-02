# Comparison protocol

## Question and scope

Primary question: does a model or serving change introduce observable regressions on the same software-engineering tasks, and how does end-to-end latency compare on tasks both deployments pass?

This is an original diagnostic regression suite. It is NOT an official public benchmark subset, a contamination-free certification, a general intelligence score, or a proof of equivalent quality. Some tasks are deliberately simple boundary-condition tests. They can detect an obvious breakage but may saturate on both models.

## Two distinct experiment lanes

**Deployment lane (default):** each checkpoint uses its required functioning runtime, fixed before measurement. The requests, generation budgets, Thinking mode, task texts, sampling and actual concurrency are matched. Differences describe the complete deployment, including quantization, parser, kernels, MTP and templates.

**Checkpoint-controlled diagnostic:** when both implementations support it, disable speculative decoding for BOTH models, use BF16 KV for both, and keep compatible runtime/template settings as close as possible. Then re-run the same frozen tasks. This reduces one confound; it does not automatically isolate quantization, because checkpoint source/calibration and mandatory kernels can still differ. This package does NOT restart servers or alter MTP for this lane. Do not disable it for only one model and call the result a controlled test.

For the deployment lane, use the stable settings selected for each deployment and record their actual values. Do not modify a serving system solely to satisfy a benchmark. Label differences in concurrency, speculative decoding, memory limits, and runtime. The same seed is a pairing aid, not a bitwise determinism guarantee.

## Frozen inputs and leakage control

- `core60.jsonl` contains only publicly requested contracts/messages and optional generator metadata.
- `oracles.json` and `reference_solutions/` are for the evaluator. Never mount them in an agent workspace given to a tested model.
- The request builder is an allow-list of messages, tools, sampling and budgets. It does not serialize entire task/oracle dictionaries.
- Long context is materialized once using a running model's tokenizer; both models use byte-identical prepared messages. Check tokenizer/template differences using token ID hashes.
- Do not tune prompts or model settings on this entire set, then claim it is a held-out benchmark. If it becomes a tuning set, evaluate it on a separate task set that was not used to tune prompts or settings.
- Do not include real user/customer documents in synthetic tasks. All supplied identifiers, business records and incidents here are fictional.

## Run controls

Primary C1, then optionally C2 for the 52 short tasks. C4 can be a separate concurrency check, not a replacement for the primary low-concurrency measurement. Long context is C1-only in this tool.

Use the same task order seed and repeat count. `repeats=3` means three first-attempt generations per question, all scored. It is not pass@3 or “select the best of three.” No automatic answer repair or generative retry occurs. The retry tool task retries a declared transient tool error as part of that one task's contract.

Default temperature=0.6, top_p=0.95, top_k=20, min_p=0, repetition_penalty=1, frequency/presence penalties=0; Thinking ON. These are test-design choices, not official model-card reproduction. Greedy evaluation can be an additional separately labeled profile. Change the same request controls for both models.

Never set min_tokens=max_tokens, ignore_eos, forced answer grammar, or benchmark-provided stop strings for this quality test. No `response_format` is sent. Tools use auto choice without an explicit strict schema flag. A server-side grammar/strictness policy may still constrain output; record and match it where possible. Otherwise report a deployment/parser comparison rather than intrinsic JSON ability.

## Output budgets and cutoffs

Coding/Reasoning: 8192 output tokens per request by default. Other categories: 4096. Tool tasks have at most 8 model turns and a total episode output budget of twice the per-request budget. Reasoning consumes that same output budget; do not add reasoning tokens to completion tokens again.

If finish_reason=length, mark generation_truncated and failed under this budget, even if a partial fragment resembles an answer. Do not mine the hidden reasoning field for a valid code block. A parser returning only reasoning and no final content is not a successful answer.

If many cases truncate, run a new paired larger-budget experiment. Preserve the original failures. Report both fixed-budget ability and deployment latency; do not claim a truncation-heavy result measures unconstrained capability.

## Grading

For code, primary pass means every case produces the expected typed JSON and does not mutate its input. One outer code fence is accepted for execution but separately marked as artifact-format noncompliance. That relaxation is only for code, not JSON/text instruction tasks. SQL outputs must have the stated row and column order.

For JSON, reject invalid syntax, duplicate keys, non-finite numbers, extra keys, numeric strings in place of numbers, booleans in place of numbers, and wrong array ordering. Object key order is irrelevant; integral numeric representations such as 1 and 1.0 are equivalent. Text matching strips outer whitespace only.

Tool scoring checks native calls, full arguments, prerequisite stage order, duplicates, no-tool cases and the final answer. Independent calls in one stage may be parallel or sequential in either order. Tools are deterministic simulations; they never access real systems.

Format-only instruction tasks do not prove the factual or stylistic quality of free-form prose. Korean tasks are a small regression check, not a broad language benchmark. Long-context tasks use compact facts scattered through synthetic distractors, not actual full repository execution.

## Quality versus infrastructure

API failures are unscored in the conditional quality rate, counted against operational success, and remain in the result set. They must be investigated, not silently discarded. Parser-related HTTP 400s are not evidence that quantization degraded reasoning. Code compile/runtime errors and bounded execution timeouts are failed code tasks. Missing Docker or inaccessible judge images are infrastructure failures, never zero model scores.

`compare` refuses changed prompts, oracle hashes, sampling, budgets, seeds, repeat counts, concurrency or coverage. It reports each category independently. There is no weighted global winner and no automatic model-adoption action.

Paired bootstrap resamples unique task IDs, averaging repeated attempts per task first. This avoids treating repeated generations as new independent questions. Intervals refer only to this small task set. All-zero observed differences can yield a zero bootstrap interval while still providing no guarantee of general equivalence.

## Timing

Non-streaming requests measure end-to-end API response time, including waiting, prefill, reasoning, final generation and network transport. No TTFT, TPOT, pure decode rate or device power is measured. First-tool-response time is the time at which a full non-streamed tool response arrives, not first-token latency. Tool episodes include all model calls, but tools themselves are instantaneous fixtures; this does not reproduce real filesystem/test/network time.

Compare paired latency ratios on questions BOTH models pass. Also retain operational failures and all response lengths. A faster wrong answer is not productive speed. Grade code after generation or on another host to avoid CPU/memory contention with the serving pair. Build judge images once; reuse their immutable local image IDs.

## Decision process

Inspect model-A-only passes first, especially C02/C05/C09/C14/C16/C17/C20 and T01/T06/T08/T10. They target expiration, tombstones, integer precision, atomicity, authorization and ordering. Reproduce meaningful regressions on new inputs.

No universal 1–2% threshold is justified by 60 handcrafted tasks. One question is 5 percentage points in the 20-question coding category and 10 points in the ten-question tool category. A critical wrong operation matters even when an overall average looks unchanged.

A clean run is permission to test real repository tasks, not proof of equal general quality or long-term memory stability. Add private failing tests and actual agent traces before deciding whether to replace the production serving configuration.
