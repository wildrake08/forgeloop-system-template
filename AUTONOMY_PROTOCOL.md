# External Agent Protocol

## Input

Each invocation runs in a temporary working directory containing read-only-purpose copies of `src/` and `tests/`, plus:

- `context.json`: objective, active specification, current file hashes, path and criterion boundaries, budgets, iteration number, and previous trial evidence.
- `response.schema.json`: the required response contract.

OS-level isolation is supplied by the configured agent and runner. The built-in Codex profile requests its read-only sandbox. Generic profiles should use an organization-controlled sandbox or container.

## Output

The driver returns:

```json
{
  "status": "propose_changes",
  "summary": "Why this is the smallest next step",
  "changes": [
    {
      "path": "tests/test_behavior.py",
      "instruction": "Add the declared behavior test",
      "content": "complete replacement file contents",
      "requirement_keys": ["test_pass_rate"]
    }
  ]
}
```

`status` may be `propose_changes`, `done`, or `blocked`. Only `propose_changes` may contain changes. The control plane validates every field, budget, path, criterion, specification digest, and prior-file digest before applying a proposal through the signed agent-execution mechanism.

## Durable states

- `engineering`: invoke agent, apply bounded proposal, run trial tests, and repeat.
- `budget_exhausted`: stop without authority or release.
- `blocked`: stop with the external agent's reason.
- `awaiting_build`: wait for a human signature over the exact final change-set scope.
- `awaiting_release`: wait for separate artifact acceptance and deployment authorization.
- `complete`: deployment, observation, A1–A8 validation, signed closure, and accepted baseline succeeded.

Restarting `autonomy-run` resumes the recorded state. The agent cannot transition an authority gate by its own output.
