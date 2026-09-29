# Start Here

Edit `resume.tex`. Styling lives in `resume.cls`.

1. Replace the name, contacts, links, education, and credentials with your own.
2. Replace each example and `[placeholder]` with work you can explain. Delete sections you do not need.
3. Compile and check the log for placeholders and extra pages. Replace flagged text or delete unused entries, then recompile.
4. Inspect every page, then download the PDF. Warnings do not catch every unfinished example.

In the no-internship starter, label course projects and your part of team work. Delete **Other Experience** if it does not apply.

For AI/ML roles, distinguish offline experiments from production results. The [AI/ML guide](https://github.com/deepdave98/latex-resume-and-cv-templates/blob/main/docs/ai-ml-resumes.md) covers evaluation, section order, and research entries. For graduate applications, follow the [admissions guide](https://github.com/deepdave98/latex-resume-and-cv-templates/blob/main/docs/graduate-admissions.md) and the program's instructions.

## Contacts

Edit the values in `\resumeemail{alex_morgan+jobs@example.com}` and `\resumephone{+1 (416) 555-0123}` once. They supply both the visible text and the link. Use a literal email and include `+` with your phone's country code. Phone spaces, parentheses, hyphens, and periods stay visible but are removed from the `tel:` link.

Unsupported formats warn and print without a link. Use `\resumelink{destination}{label}` for other formats or labels; check both values. To remove a contact, delete its preceding `\contactsep` too. Click the links in your downloaded PDF before sending.

## Overleaf

Use [New Project > Upload Project](https://www.overleaf.com/learn/latex/Kb/Uploading_a_project) and upload the ZIP. Set the compiler to **XeLaTeX** and the main document to `resume.tex`. Click **Recompile**.

Open **View logs** beside **Recompile** (**Logs and output files** in the older editor). Checks flag sample contacts, known example fields, and `[prompts]` in headers, entries, and lists. Literal brackets may trigger warnings; unmarked examples and text inside custom commands may be missed.

## Page limit

`\resumepagelimit{1}` warns above one page; the experienced starter uses `2`. Change the number for an intentional extra page, or remove the line to disable the warning. It does not change the layout.

If LaTeX asks you to rerun, recompile before checking length. Its temporary rerun pages are not counted by this reminder.

## Local

With XeLaTeX, `latexmk`, and LaTeX 2020-10-01 or newer installed, run this inside the extracted folder:

```bash
latexmk resume.tex
```

The included `latexmkrc` selects XeLaTeX. Your output is `resume.pdf`.

For literal text, escape LaTeX characters: `\&`, `\%`, `\$`, `\#`, and `\_`.

## Fit your content

Long organizations and locations wrap beside the dates. Keep dates short; use `{}` for a location you do not need. For links, show a short label instead of a long URL. Unbroken text can still overflow.

Use `\documentclass[a4paper]{resume}` for A4 or `\documentclass[letterpaper]{resume}` for US Letter. Recompile and inspect all pages after changing paper size.

[Bullet examples](https://github.com/deepdave98/latex-resume-and-cv-templates/blob/main/examples/engineering-bullets.md) · [Section order](https://github.com/deepdave98/latex-resume-and-cv-templates/blob/main/docs/section-order.md)
