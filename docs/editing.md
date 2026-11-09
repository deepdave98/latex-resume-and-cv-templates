# Editing reference

Edit `resume.tex` in a starter ZIP or `templates/*-resume.tex` in a clone. Shared styling lives in `resume.cls`.

## Contacts

Keep these inside `\resumecontact`; each value supplies both the printed text and the link:

```latex
\resumephone{+1 (555) 555-5555}
\resumeemail{hello@example.com}
```

Use a literal email address; underscores, plus signs, and hyphens work. Phone numbers need `+`, a country code, and 7 to 15 digits in total. Spaces, parentheses, hyphens, and periods stay visible but are removed from the link. No country code is guessed.

Unsupported formats warn and print without a link. Use `\resumelink{destination}{label}` for extensions, custom email syntax, or different labels; check both values. Remove a contact with its preceding `\contactsep`. A long contact line wraps after a separator.

## Entries

```latex
\jobentry[Optional summary]{Role}{Organization}{Location}{Dates}
\begin{jobduties}
  \item Fixed [failure] in [workflow] by [change]; added a regression test for [trigger].
\end{jobduties}
```

Omit `[Optional summary]` when unnecessary. Use `{}` for no location. Long organizations and locations wrap beside the dates. Keep dates short and use labels instead of long URLs; unbroken text can overflow.

To link a project, wrap its name: `\jobentry{Course project; Tools}{\resumelink{https://...}{Project Name}}{}{Dates}`. Keep the label short.

Do not start a bullet with `[`: LaTeX reads `\item [text]` as a label and drops the brackets. Write `\item {[Authors in order]}` to keep them.

Escape special characters in literal text: `\&`, `\%`, `\$`, `\#`, `\_`.

Move whole `\section{...}` blocks to change the order. Let LaTeX paginate naturally as you add or remove entries. [Section order guide](section-order.md).

## Promotions

Keep one heading per employer. Pass `{}` as the role, then add a `\jobsubentry` with its own bullets for each title, newest first:

```latex
\jobentry{}{Company A}{City, Region}{2020 -- Present}
\jobsubentry{Senior Software Engineer}{2023 -- Present}
\begin{jobduties}
  \item ...
\end{jobduties}
\jobsubentry{Software Engineer}{2020 -- 2023}
\begin{jobduties}
  \item ...
\end{jobduties}
```

The experienced starter ships with this pattern.

## Rows

`\resumerow{Name}{Detail}{Date}` prints one dated line without bullets, for certifications, awards, talks, licenses, or roles too old for bullets. Pass `{}` for a detail or date you do not have. Write a level after a comma; the row prints its own dash before the detail:

```latex
\section{Certifications}
\resumerow{AWS Certified Solutions Architect, Associate}{Amazon Web Services}{2024}
```

## Summary

`\resumesummary{...}` after `\resumecontact` prints a short paragraph under the header rule. Two sentences at most. Say what the first entry cannot, such as the field you are moving from or the systems you own. No adjectives. The experienced, AI, and ML starters carry a commented line.

## Cover letter

`cover-letter.tex` shares the header commands. `\letterfor{Company}{Role}` defines `\Company` and `\Role`, so each is typed once per application. `\letteropening{Date}{Recipient}{Organization}{Greeting}` prints the opening; pass `{}` for a line you do not have. Paragraphs go inside `letterbody`, separated by blank lines. `\letterclosing{Sincerely,}{}` ends the letter using the header name. Supply a name in the second argument to override it. The log flags known sample values in letter fields.

## Change the look

Put overrides in `resume.tex` after `\documentclass`. Edits to `resume.cls` are lost when you download a starter again.

Font, using files that ship with TeX Live and Overleaf:

```latex
\setmainfont{texgyrepagella-regular.otf}[
  BoldFont=texgyrepagella-bold.otf,
  ItalicFont=texgyrepagella-italic.otf,
  BoldItalicFont=texgyrepagella-bolditalic.otf]
```

Replace `texgyrepagella` with `texgyreheros` for a sans-serif face. For Libertinus, use `LibertinusSerif-Regular.otf`, `-Bold`, `-Italic`, and `-BoldItalic`.

Colors: `\definecolor{namecolor}{HTML}{1F2933}` sets the name, headings, and entry lines. `\definecolor{resumetextcolor}{HTML}{000000}` sets bullet and letter text.

Size: `\documentclass[11pt]{resume}`. Margins are the four values on the `geometry` line in `resume.cls`.

Recompile and inspect every page after any of these; line and page breaks move.

## Paper size

Use `\documentclass[a4paper]{resume}` for A4 or `\documentclass[letterpaper]{resume}` for US Letter. Recompile and inspect every page; changing paper size can change line and page breaks.

## Compile warnings

Open **View logs** in Overleaf (**Logs and output files** in the older editor), or read the local compile log.

- **Placeholders:** flags sample contacts, `your-handle` anywhere, known example fields, and `[prompts]` in headers, the summary, entries, rows, lists, and letter parts. Replace flagged text or delete unused entries. Literal square brackets may be flagged; unmarked examples and text inside custom commands may be missed.
- **Page limit:** all starters use `\resumepagelimit{1}` to warn above one page. Cut less relevant content first. Use `\resumepagelimit{2}` when a second page is useful, or remove the command to disable the warning. From page 2, the footer prints your name and page number.
- **Empty list:** an empty `jobduties` block prints nothing and warns. Add a bullet or delete the block.

These warnings do not change the PDF or stop compilation. Resolve rerun warnings before checking length; temporary rerun pages are not counted by the reminder. Review the final text, layout, and links yourself.

[Back to the README](../README.md#edit-the-content)
