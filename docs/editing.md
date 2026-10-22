# Editing reference

Edit `resume.tex` in a starter ZIP or `templates/*-resume.tex` in a clone. Shared styling lives in `resume.cls`.

## Contacts

Keep these inside `\resumecontact`; each value supplies both the printed text and link:

```latex
\resumephone{+1 (416) 555-0123}
\resumeemail{alex_morgan+jobs@example.com}
```

Use a literal email address; underscores, plus signs, and hyphens work. Phone numbers need `+`, a country code, and 7–15 digits total. Spaces, parentheses, hyphens, and periods stay visible but are removed from the link. No country code is guessed.

Unsupported formats warn and print without a link. Use `\resumelink{destination}{label}` for extensions, custom email syntax, or different labels; check both values. Remove a contact with its preceding `\contactsep`.

## Entries

```latex
\jobentry[Optional summary]{Role}{Organization}{Location}{Dates}
\begin{jobduties}
  \item Fixed [failure] in [workflow] by [change]; added a regression test for [trigger].
\end{jobduties}
```

Omit `[Optional summary]` when unnecessary. Use `{}` for no location. Long organizations and locations wrap beside the dates. Keep dates short and use labels instead of long URLs; unbroken text can overflow.

Escape special characters in literal text: `\&`, `\%`, `\$`, `\#`, `\_`.

Move whole `\section{...}` blocks to change the order. Let LaTeX paginate naturally as you add or remove entries. [Section order guide](section-order.md).

## Paper size

Use `\documentclass[a4paper]{resume}` for A4 or `\documentclass[letterpaper]{resume}` for US Letter. Recompile and inspect every page; changing paper size can change line and page breaks.

## Compile warnings

Open **View logs** in Overleaf (**Logs and output files** in the older editor), or read the local compile log.

- **Placeholders:** flags sample contacts, known example fields, and `[prompts]` in headers, entries, and lists. Replace flagged text or delete unused entries. Literal square brackets may be flagged; unmarked examples and text inside custom commands may be missed.
- **Page limit:** all starters use `\resumepagelimit{1}` to warn above one page. Cut less relevant content first. Use `\resumepagelimit{2}` when a second page is useful, or remove the command to disable the warning.

Neither warning changes the PDF or stops compilation. Resolve rerun warnings before checking length; temporary rerun pages are not counted by the reminder. Review the final text, layout, and links yourself.

[Back to the README](../README.md#edit-the-content)
