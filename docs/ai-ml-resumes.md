# Resumes for AI and ML engineering

Choose by the work in the job description, not the title alone.

| Target work | Start here | Show |
| --- | --- | --- |
| Applications built with pretrained models | [AI engineer](../templates/ai-engineer-resume.tex) | The user task, your implementation, evaluation, and failure handling |
| Training, evaluating, and operating models | [ML engineer](../templates/ml-engineer-resume.tex) | Data, baseline, evaluation split, model choice, and deployment |
| Research or applied science | Adapt the ML starter | Your research question, experiments, contribution, and relevant publications |

For academic applications, use the [graduate-admissions CV](graduate-admissions.md).

## Degree requirements differ

An MLE title does not always require graduate research. Google's [AI/ML engineering posting](https://www.google.com/about/careers/applications/jobs/results/95693255462527686-software-engineer-iii-aiml-foundational-lanes) lists a bachelor's degree or equivalent experience as a minimum; a master's or PhD is preferred. By contrast, Amazon's [Applied Scientist posting](https://www.amazon.jobs/en/jobs/10491577/applied-scientist-prime-video-science) requires a PhD or a master's plus experience, along with publications or patents. These are examples checked in September 2026, not a survey of the market.

Google's [Applied AI Engineer posting](https://www.google.com/about/careers/applications/jobs/results/133517804614623942-applied-ai-engineer) asks for software development and deployed AI systems. It does not require a graduate degree. Check each role's requirements.

## Put the relevant work first

- **Student or new grad:** education, relevant research or projects, experience, skills. An internship can go above projects when it is stronger evidence.
- **Working engineer:** experience, selected projects if useful, skills, education. Keep backend and data work that explains your ability to build the system.
- **Research applicant:** bring relevant research forward. Add selected publications with title, authorship, venue, year, and an honest status: published, accepted, preprint, or submitted.

Keep jobs newest first and delete unused sections. See [section order and length](section-order.md).

## Make the evaluation understandable

For AI applications, name the task, test cases, scoring rule, and baseline. Distinguish retrieval failures from bad answers. If a model graded outputs, explain how you checked its judgments against human labels. Label offline results as offline.

For ML, name the prediction target and how data was split. A random row split may leak information when the same user, document, or future event appears on both sides. Fit preprocessing on training data. Use validation data for choices and reserve test data for evaluation. [scikit-learn's leakage examples](https://scikit-learn.org/stable/common_pitfalls.html#data-leakage) explain why.

Keep measurements comparable: dataset, hardware, load, and units. “p95 latency at 20 concurrent requests” says more than “faster inference.” If you cannot share a number, describe the failure you fixed and how you checked it. Do not make one up.

## Bullet prompts

Replace the brackets with your work; delete details that do not apply.

### AI engineering

- **Early career:** Added schema validation to `[extraction task]`; tested missing fields and malformed responses, routing unresolved cases to `[review path]`.
- **Early career:** Compared `[retrieval change]` with `[baseline]` on `[N]` labeled queries; reported recall at `[k]` and inspected misses for `[query type]`.
- **Experienced:** Chose `[model or workflow]` over `[alternative]` after comparing `[task success criterion]`, cost per completed task, and p95 latency on `[evaluation workload]`.
- **Experienced:** Restricted `[tool]` to `[authorized action]`, required confirmation before `[external write]`, and tested denied access, duplicate calls, and timeouts.

### ML engineering

- **Early career:** Reproduced `[baseline]` on `[dataset]`; split by `[time or entity]` and reported `[metric]` separately for `[important subgroup]`.
- **Early career:** Packaged `[model]` with its preprocessing; tested that offline and served predictions matched on `[fixed inputs]`.
- **Experienced:** Replaced `[serving path]` with `[design]` to meet `[latency or memory limit]`; checked prediction parity and rolled back on `[failure threshold]`.
- **Experienced:** Investigated `[quality regression]` after labels arrived, traced it to `[data or feature change]`, and added `[validation check]` before retraining.

### Research, if you have it

Use your actual role and institution. A reproduction is not a novel method. A preprint is not a peer-reviewed publication. This block can replace a project in the ML starter:

```latex
\section{Research}
\jobentry{[Actual research role]}{[University or lab]}{}{[Dates]}
\begin{jobduties}
  \item Tested [hypothesis] against [baseline] on [dataset]; ran [ablation] to isolate [factor] and reported [finding and limitation].
  \item Owned [code, data, or experiment] in [team study]; released [permitted artifact] with [configuration needed to reproduce it].
\end{jobduties}
```

## Sources

- [Eugene Yan and Jason Liu: How to Interview and Hire ML/AI Engineers](https://eugeneyan.com/writing/how-to-interview/) - software, data literacy, evaluation, and the additional depth expected in research roles.
- [Hamel Husain: Your AI Product Needs Evals](https://hamel.dev/blog/posts/evals/) - test cases, error inspection, and human evaluation rather than judging a demo by feel.
- [Chip Huyen: Building LLM Applications for Production](https://huyenchip.com/2023/04/11/llm-engineering.html) - evaluation, model changes, cost, and latency.
- [Google: Rules of Machine Learning](https://developers.google.com/machine-learning/guides/rules-of-ml) - simple baselines, data pipelines, and training-serving differences.
- [Anthropic: Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) - when a fixed workflow is enough and where tool use adds risk.
- [MIT: Resumes](https://capd.mit.edu/resources/resumes/) - section choice, relevant detail, and readable formatting.
