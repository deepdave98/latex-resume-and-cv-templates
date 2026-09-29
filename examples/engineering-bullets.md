# Engineering Resume Bullet Examples

Describe your change and how you checked it.

Replace brackets with your own work. Delete examples that do not apply.

- Name your contribution, not the team's.
- Give a baseline, unit, and scope when they matter.
- Label benchmarks and load tests; do not present them as production results.
- Without a useful number, describe the result and how you checked it.
- Mention a tool only when it explains the solution.

For early-career roles, describe the part you built or fixed. For experienced roles, include decisions and rollout responsibilities, not just a larger number.

Applying for AI or ML work? See the [AI and ML starters and bullet prompts](../docs/ai-ml-resumes.md).

To paste an example into a `.tex` file, add `\item` and [escape LaTeX's special characters](../docs/editing.md#entries).

## Backend Engineering

### Early-Career Backend

- Built `[API operation]` for `[user workflow]` with `[framework and database]`, validated `[input or authorization rule]`, and tested `[success and failure cases]`.
- Profiled `[endpoint or query]` against `[dataset]` and added `[index, batching, or cache]`, reducing benchmark p95 latency from `[A] ms` to `[B] ms` at `[load]`.
- Implemented `[background task]` with bounded retries and `[idempotency control]`, then replayed `[failed event or request]` without losing or applying work twice.
- Reproduced `[failure]`, fixed `[underlying defect]`, and added a regression test that failed before the fix.

### Experienced Backend

- Migrated `[service, API, or schema]` with `[rollout method]`, moving `[N clients or records]` with `[downtime result]`; `[reconciliation check]` confirmed `[result]`.
- Made `[workflow]` safe to retry with `[idempotency key or replay-safe write]`; tested duplicate delivery and a timeout after commit.
- Removed `[database, lock, network, or serialization]` bottleneck, reducing production p99 latency from `[A] ms` to `[B] ms` at `[comparable load]`.
- Defined `[shared API contract]` with `[consumer teams]`; migrated `[integrations]` while preserving `[required behavior]` for old clients.

## Frontend Engineering

### Early-Career Frontend

- Built the loading, empty, error, and retry states for `[workflow]`, handled `[stale response or duplicate submission]` with `[control]`, and tested `[failure case]`.
- Implemented `[workflow]` with semantic HTML; verified keyboard operation, focus order, accessible names, and error announcements with `[screen reader and browser]`.
- Profiled `[page]` under `[device and network conditions]` and changed `[image delivery, critical CSS, code splitting, or render path]`, reducing lab LCP from `[A] s` to `[B] s`.
- Built `[workflow]` across `[breakpoints and browsers]`; fixed `[layout failure]` and added a visual regression test at the affected width.

### Experienced Frontend

- Used real-user monitoring to find `[long task, render cascade, or synchronous handler]`, removed it with `[change]`, and improved p75 INP from `[A] ms` to `[B] ms` for `[traffic segment]` over `[time window]`.
- Migrated `[screens]` to `[shared component system]`; preserved `[keyboard or screen-reader behavior]` and tested old and new versions before rollout.
- Fixed `[stale response or cache invalidation defect]` in `[workflow]` with `[change]`; tested rapid navigation and out-of-order responses.
- Instrumented `[checkout or signup flow]` and shipped `[change]`; a controlled experiment moved `[completion, conversion, or error rate]` from `[A]` to `[B]` across `[sample and time window]`.

## Data Engineering

### Early-Career Data

- Built a scheduled `[Python or SQL]` pipeline from `[source]` to `[consumer]`, documented `[data assumptions]`, and tested missing, duplicate, and malformed records before each refresh.
- Modeled `[domain]` into `[table design]`; added uniqueness and freshness checks that stopped invalid refreshes before `[consumer]` updated.
- Backfilled `[dataset and date range]` with checkpoints, reconciled row counts and aggregates against `[source of truth]`, and wrote `[N]` records without duplicates.
- Changed `[partitioning, filter placement, join strategy, or materialization]` after reading `[query plan]`, reducing runtime from `[A]` to `[B]` on `[data volume]`.

### Experienced Data

- Migrated `[warehouse or lake workload]` with dual runs and checkpointed backfills, moving `[N]` tables and `[N] TB` while meeting `[SLA]`; `[row-count or aggregate check]` confirmed `[result]`.
- Added `[freshness or correctness]` checks to `[pipelines]`; routed alerts to the owning team and tested recovery from `[upstream failure]`.
- Changed `[partitioning or materialization]` for `[workload]`, reducing p95 query time from `[A] s` to `[B] s` on `[comparable data volume]`.
- Chose `[batch, micro-batch, or streaming]` for `[use case]` after measuring `[freshness need]`; met `[SLO]` without `[cost or operating burden of the main alternative]`.

## Before and after

| Vague | Specific |
| --- | --- |
| Improved scalability by 40%. | Split `[workflow]` at `[service boundary]`, migrated `[traffic share]` with `[rollout method]`, and reduced production p99 latency from `[A] ms` to `[B] ms` at `[peak load]`. |
| Built responsive React components. | Built `[workflow]` across `[breakpoints and browsers]`, verified `[keyboard or screen-reader behavior]`, and added visual regression tests for `[N]` components. |
| Developed ETL pipelines with Python and Spark. | Built a daily pipeline from `[source]` to `[consumer]` with replay-safe writes and `[quality checks]`, processing `[N]` records within `[freshness window]`. |

Before keeping a bullet, ask whether you would describe the work that way to the person who reviewed it. If you include a measurement, be ready to explain it.

## Further Reading

- [MIT: Resumes](https://capd.mit.edu/resources/resumes/)
- [Google SRE: Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)
- [web.dev: Core Web Vitals Thresholds](https://web.dev/articles/defining-core-web-vitals-thresholds)
- [W3C: Evaluating Web Accessibility](https://www.w3.org/WAI/test-evaluate/)
- [Google Cloud: Plan Dataflow Pipelines](https://docs.cloud.google.com/dataflow/docs/guides/plan-pipelines)
