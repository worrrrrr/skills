# Estimation and scheduling

## Three-point / PERT
For each leaf give `o` (everything goes right), `likely` (normal day), `p` (one bad surprise).

    mean  = (o + 4*likely + p) / 6
    sigma = (p - o) / 6

Rules:
- Estimate **ideal effort**, not elapsed time. Convert with capacity later.
- `p` covers *known* risks (flaky API, unclear spec), not unknown unknowns - those go in buffer.
- If `p/o > 4`, uncertainty dominates: extract a spike instead of guessing harder.
- Never pad individual tasks. Padding compounds and destroys the signal in the variance.

## Project roll-up
The engine sums variances along the critical path (assumes independence):

    P50 = critical path length
    P80 = P50 + 0.8416 * sqrt(sum(sigma_i^2 on CP))

Caveats to state out loud:
- Near-critical paths can become critical ("merge bias"); P80 is optimistic when several
  paths have similar length. Check slack: paths within ~10% of CP length deserve attention.
- Correlated risks (same vendor, same person) break independence - inflate the buffer.

## Buffers
Put a single project buffer at the end, sized ~25-33% of the critical path, or use
`P80 - P50` as the minimum. Feeding buffers sit before join points with high fan-in.
Never distribute buffer across tasks.

## Capacity and dates

    elapsed_days = ideal_hours / (people_on_path * ideal_hours_per_person_per_day)

Default 6 ideal hours/day for engineers (meetings, review, context switching eat the rest).
Only convert to calendar dates when the user gives a start date and team size; always print
the assumption next to the date. Parallelism is capped by the DAG, not by headcount:
`max useful people = effort / span` (the engine prints this).

## Monte Carlo (optional upgrade)
When paths are near-critical or risks correlate, replace the analytic P80 with sampling:
draw each task duration from a Beta-PERT distribution, run 10k trials, take percentiles.
Stdlib sketch:

    import random
    def betapert(o, m, p, lam=4):
        a = 1 + lam * (m - o) / (p - o)
        b = 1 + lam * (p - m) / (p - o)
        return o + (p - o) * random.betavariate(a, b)

Keep the same DAG; report P50/P80/P95 and the probability of hitting the deadline.

## Re-estimation loop
After each wave completes, compare actual vs `likely`. If the median ratio > 1.3, rescale
remaining estimates by that factor rather than pretending the original numbers still hold.
Record the factor in `assumptions[]`.