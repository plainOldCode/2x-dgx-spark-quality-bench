# Contributor and agent guidance

- Read `README.md`, `PROTOCOL.md`, and `VALIDATION.md` before contacting a model endpoint.
- Do not start, stop, or reconfigure a serving deployment as a side effect of running this client.
- Keep API keys in environment variables. Use HTTPS for network endpoints; plain HTTP is allowed only on loopback. Review endpoint configuration before setting a key.
- The public package contains prompts, scoring rules, oracles, and reference solutions. Never send evaluator-only material to a tested model. The suite is open and is not a blind or contamination-free benchmark.
- Treat model-generated code as untrusted. Run it only through the bounded Docker judges. Never add a host-execution fallback. Prefer a disposable environment without secrets.
- Keep long-context requests serial and reuse the same frozen input file when comparing models. Do not trim prompts silently.
- Preserve failed, truncated, and infrastructure-error records. Do not automatically repair model output or grade an answer found only in reasoning content.
- Inspect run artifacts before sharing. They contain prompts and complete model responses, which may include reasoning fields.
- Report the exact runs, skipped cases, settings, and limitations. Do not present this synthetic suite as an official leaderboard score.
