# Package validation — 2026-09-27

## Completed checks

- **48 self-tests passed**, with no skipped tests in the preparation environment.
- All **20 trusted reference programs** passed all **166 supplied code input/output fixtures**.
- Python 12, TypeScript 4, SQL 4 reference implementations were tested using the same wrapper protocols shipped for Docker execution.
- All 60 task records and the evaluator oracle map passed the supplied JSON schemas.
- Non-code reference answers passed their graders; invalid JSON, duplicate keys, NaN, boolean/number confusion, wrong constraints and code-input mutation are rejected in tests.
- All ten native-tool scenarios passed mocked multi-turn HTTP execution, including independent calls in either order, no-tool decisions, transient retries and wrong-call rejection.
- A local HTTP mock exercised run -> persist -> resume -> grade -> compare -> blind export, and deliberately introduced a candidate error so paired regression detection was checked.
- Long-context preparation was tested with a MOCK tokenizer to verify resizing, freezing and rejection of unprepared previews. This is a test of the mechanism, NOT a token measurement from either Qwen tokenizer.
- All Python package, generator and wrapper files compiled successfully.

## Preparation environment

```text
Python: 3.13.5
Node: v22.16.0
TypeScript: Version 5.8.3
SQLite: 3.46.1
Docker executable/daemon: unavailable
```

## Not executed here

- NVIDIA Qwen3.8-Flash-Next inference or hibrid48 inference.
- `/tokenize` on either real Qwen serving image, including its chat-template kwargs support.
- Building the Docker judge images or running the Docker isolation flags on ARM64/GB10.
- Device memory, GPU power, OOM, long soak, C2/C4 performance, or real repository task measurements.
- Any official public benchmark, third-party LLM judge, or score proving quantization equivalence.

This public source release includes curated GLM-5.3 Flash endpoint measurements under `results/glm53/`. These aggregate quality and throughput results are separate from the package self-test logs: the `model-a`/`model-b` entries are synthetic HTTP test doubles. The published GLM result files omit raw model responses and local endpoint, container, and host identifiers. Docker resource isolation must still be checked on the target host before evaluating generated code. Local self-tests execute only the bundled trusted references, never model responses.

The 166 fixtures are a diagnostic test set, not exhaustive formal verification of each implementation. Model code may pass these inputs and still fail unseen cases. Do not promote a unit-task pass into a claim about complete application correctness.
