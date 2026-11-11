# Choose Your Section Order

Lead with education as a student or new grad; lead with relevant work once you have it. [CareerOneStop's guidance](https://cloudfront.careeronestop.org/JobSearch/Resumes/ResumeGuide/education.aspx).

- **No internship yet:** education, projects, other experience, skills. Use the [project-first starter](../templates/no-internship-resume.tex). Keep course projects labeled as projects and separate your contribution from the team's. Other experience can be paid work, tutoring, volunteering, or a club responsibility; delete that section if it does not apply.
- **New grad with relevant work:** education, relevant experience, projects, skills. Put projects above unrelated jobs when they show more of your engineering ability.
- **Engineer with relevant work:** experience, skills, education. Give recent work the most space. Keep projects only when they add evidence your jobs do not cover.
- **Changing fields:** start from the no-internship starter and put Projects first. Rename Other Experience to Experience and keep one prior role with its real title; its bullets cover scope, systems, and people. List a bootcamp or certificate as an Education entry above the degree. Keep entries within each section in reverse chronological order.

Keep certifications only when relevant. The new-grad and experienced starters include a commented-out block you can enable. Move a required credential near the top; otherwise put it below experience and projects.

For AI and ML roles, prioritize the work requested in the job description. Research and publications matter more for some roles than others. [AI/ML guide](ai-ml-resumes.md).

Use a second page when relevant experience needs it, not because of your title. [MIT's length guidance](https://capd.mit.edu/resources/resumes/).

For PhD and research master's applications, education and research usually lead. Keep publications near that evidence if you have them; omit the section if you do not. The program's CV and page-limit instructions take precedence. [Admissions starter and guide](graduate-admissions.md).

## Where a line goes

- Security clearance, work authorization, and willingness to relocate go in the contact line after the city, each with its own `\contactsep`. The line wraps after a separator.
- Spoken languages are a Skills bullet labeled **Spoken languages** with a level word: native, fluent, or working. Keep the existing **Languages** bullet for code.
- A certification, award, talk, or license is a `\resumerow`. A bootcamp or certificate program is an Education entry above the degree.
- A career break is `\jobentry{}{Career break}{}{Year -- Year}` with no bullets, or nothing. Years alone are fine when every entry uses them.

## For one posting

1. Pick the two or three responsibilities the posting repeats.
2. Make the first two bullets of your first experience or project entry show them.
3. Move the matching project or job up; cut the least related bullet.
4. Reorder skills lines to lead with what they ask. Add nothing you cannot discuss.
5. Save the source as `acme-backend.tex` beside `resume.tex` (on Overleaf, **Make a copy** with that name) and rebuild. The rebuild takes seconds; deciding is the work.
6. Export as `Firstname-Lastname-Resume.pdf`, then keep the sent copy as described in [Before you send](before-you-send.md#keep-the-pdf-you-sent).

To reorder these templates, move each complete `\section{...}` block with its entries. All starters begin at one page. If relevant content needs a second, set `\resumepagelimit{2}` and let LaTeX paginate naturally; a heading moves to the next page with its first entry, and the footer prints your name and page number from page 2. Rebuild and inspect the PDF after changing the order or length.
