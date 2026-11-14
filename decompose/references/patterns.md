# Decomposition patterns

Choose the axis before writing tasks. Mixing axes at the same level produces overlap and
hidden dependencies.

## 1. Vertical slice (default for product work)
One thin user-visible path through every layer. First slice = the riskiest path with the
smallest data set. Each slice ships behind a flag.
- Good: early integration feedback, demoable increments.
- Watch for: shared infrastructure masquerading as a slice -> extract it as an enabler task.

## 2. Contract-first / interface boundary
Freeze the interface, then build producer and consumer in parallel against mocks, then a
contract-test task joins them.
- Node order: contract -> {producer, consumer, fixtures} -> contract tests -> integration.
- Highest-leverage pattern for parallelism: one small node unlocks many.

## 3. Strangler fig (legacy replacement)
seam/router -> shadow implementation -> parity harness -> ramp -> retire old.
Never plan a big-bang cutover node. Every ramp step needs a rehearsed rollback.

## 4. Risk-first / spike-driven
Sort unknowns by (impact x uncertainty). Each unknown becomes a timeboxed spike whose
deliverable is a **written decision**, not code. Spikes may fail - that is a valid outcome
and must have a documented fallback branch.

## 5. Pipeline / data-flow stages
ingest -> validate -> transform -> store -> serve -> observe. Cut at stage boundaries where
a durable artifact exists (a file, a table, a topic). Each stage gets a data-quality check
as acceptance, not as a separate QA phase at the end.

## 6. Lifecycle / environment
provision -> configure -> verify -> migrate data -> cutover -> decommission.
Repeat per environment only if the environments genuinely differ; otherwise parameterize.

## 7. Walking skeleton
End-to-end no-op path first (request in, empty response out, deployed, observable). Then
fill in behavior slice by slice. Best when infra/integration is the main unknown.

## 8. Decision tree (when the plan itself is unknown)
Model as `decision` nodes with mutually exclusive branches. Estimate each branch, mark the
default, and record the trigger that selects a branch. Do not sum branches.

---

## Domain playbooks

### Refactor / performance optimization
1. Baseline measurement task (numbers, reproducible harness) - **always first**.
2. Characterization tests around the code to be changed.
3. One optimization per task, each with a measured delta as acceptance.
4. Regression guard + benchmark in CI.
5. Cleanup/removal of the old path.
Anti-pattern: "optimize the hot loop" with no baseline - unverifiable (T4).

### ML / AI feature
problem framing + metric -> data audit -> labeling spec -> baseline model -> eval harness
-> iteration loops (timeboxed) -> serving integration -> monitoring/drift -> rollout.
Iteration is a **timebox**, not an accuracy promise. Acceptance = "report produced with
metric X on frozen eval set", never "reach 95% accuracy".

### Data migration
schema contract -> dry-run on sample -> backfill (idempotent, resumable) -> verification
counts/checksums -> dual-read -> cutover -> cleanup. Chunk backfill by partition if it
exceeds the size cap.

### Incident / debugging (unknown cause)
reproduce -> bisect/isolate -> hypothesis spikes -> fix -> regression test -> postmortem.
The reproduce task is the gate; without it everything downstream is speculative.

### Writing / research deliverable
question + scope -> source gathering (timeboxed) -> outline -> section drafts (one per
task) -> synthesis -> fact-check pass -> edit pass -> publish. Fact-check is its own task
with its own acceptance, never folded into drafting.

### Infra / platform
design doc + review -> IaC module -> staging apply + verify -> security review -> prod
apply -> runbook + alerting -> handover. Security review is a dependency node, not a
checkbox at the end.