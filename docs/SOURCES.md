# Provenance and technical references

## Task data

All 60 task prompts, fixture values, tool episodes, and answer oracles were authored for this package. The task set was not copied from public benchmark questions, company records, or private source repositories. The email fixtures use reserved example domains.

This is a synthetic regression suite for comparing local model deployments. Its task counts, sampling values, budgets, scoring rules, and run order are design choices, not official model evaluation protocols. The full task set and evaluator materials are included in this public package, so it is not a blind or held-out evaluation set.

## Technical interfaces consulted

The implementation uses the vLLM chat-completions tool-calling interface. Native tool calls are checked separately from text that merely names a tool.

```text
https://docs.vllm.ai/en/latest/features/tool_calling/
```

Docker run options provide process, network, filesystem, and resource controls for the code judges. Containerization is not asserted to be a perfect security boundary.

```text
https://docs.docker.com/engine/containers/run/
```

The external references describe interfaces and controls. Compatibility with a particular model server must be checked with that deployment's smoke run.
