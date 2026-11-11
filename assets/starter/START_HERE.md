# Start Here

Edit `resume.tex`. Styling lives in `resume.cls`. `cover-letter.tex` uses the same header.

1. Replace the name, contacts, links, education, and credentials with your own.
2. Replace each example and `[placeholder]` with work you can explain. Delete sections you do not need.
3. Compile and read the log. A placeholder reminder names the field that still holds sample text. A page-limit warning means the resume ran past `\resumepagelimit{1}`; cut content rather than shrinking the type.
4. Read every page of the PDF and click its links. [Before you send](https://github.com/deepdave98/latex-resume-and-cv-templates/blob/main/docs/before-you-send.md) lists the final checks.

## Contacts

`\resumeemail{hello@example.com}` and `\resumephone{+1 (555) 555-5555}` print the value and link it. Use a literal email address. Include `+` and the country code in the phone number. Unsupported values warn and print without a link; use `\resumelink{destination}{label}` for other formats. To remove a contact, delete its `\contactsep` too.

## Overleaf

Use [New project > Existing project (.zip)](https://docs.overleaf.com/managing-projects-and-files/uploading-a-project) and upload the ZIP. Set the compiler to **XeLaTeX** and the main document to `resume.tex`, then **Recompile**. Open **View logs** beside Recompile to see the reminders. For the cover letter, switch the main document to `cover-letter.tex`.

## Local

With XeLaTeX and `latexmk` installed, run `latexmk resume.tex` in this folder. The bundled `latexmkrc` selects XeLaTeX.

Escape `&`, `%`, `$`, `#`, and `_` in literal text with a backslash. Promotions, fonts, colors, and paper size are in the [editing reference](https://github.com/deepdave98/latex-resume-and-cv-templates/blob/main/docs/editing.md). [Bullet examples](https://github.com/deepdave98/latex-resume-and-cv-templates/blob/main/examples/engineering-bullets.md) · [Section order](https://github.com/deepdave98/latex-resume-and-cv-templates/blob/main/docs/section-order.md)
