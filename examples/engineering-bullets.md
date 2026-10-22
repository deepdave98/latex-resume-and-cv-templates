# Write a useful engineering bullet

Start with what you changed and who or what it helped. Add a technical detail when it explains the work. Use a measurement when you have one.

You do not need a metric, a tool list, and a test claim in every bullet. Two clear sentences are better than one sentence packed with five claims.

## Before and after

These are fictional writing examples. The added details show what to ask about your own work; use them only when they are true of it.

### A feature someone can use

**Vague:** Built responsive React components.

**Specific:** Built the account-settings form in React. Kept edits after failed saves and moved keyboard focus to the field that needed attention.

The reader can picture the feature and the behavior you implemented. “Responsive components” does not explain either.

### A bug without a business metric

**Vague:** Improved backend reliability.

**Specific:** Fixed duplicate receipts when the payment provider retried a webhook by storing its event ID before sending email.

The failure and the fix are enough. Add a regression test if it helps explain why the fix holds; you do not need to invent an outage reduction.

### A measurement with context

**Vague:** Made the API faster.

**Specific:** Added an index for order-history queries, reducing p95 response time from 800 ms to 120 ms in a load test with 20 concurrent requests.

The numbers here are fictional. In your resume, give the measurement, comparison, and test setting you actually used. Do not call a local test a production result.

### Your part of a team project

**Vague:** Led development of a full-stack campus app.

**Specific:** Built room search and booking validation for a four-person course project; prevented overlapping reservations in the database.

Keep the project label and your contribution visible. Use “led” only when you can explain the responsibility you held.

### An experienced engineer's decision

**Vague:** Spearheaded a scalable data-platform transformation.

**Specific:** Moved daily imports to resumable batches so failed runs could restart from the last completed file. Kept the old importer available until row counts matched for a week.

The decision, reason, and rollout explain the scope without a senior-sounding verb.

## Turn your notes into a bullet

Write down the task, your contribution, and what changed. Then ask:

- What did I build, fix, decide, or remove?
- Which detail makes this work different from a generic job description?
- What result can I support: a working feature, a resolved failure, adoption, or a measured change?
- Would the teammate who reviewed it agree with this wording?

Keep the details that help a reader understand your work. Delete the rest. If you have no internship, use course, personal, or volunteer work and label it accurately.

To use a bullet in LaTeX, prefix it with `\item` and [escape special characters](../docs/editing.md#entries). For AI/ML evaluation and research examples, see the [role guide](../docs/ai-ml-resumes.md).
