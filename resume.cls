\NeedsTeXFormat{LaTeX2e}[2020-10-01]
\ProvidesClass{resume}[2026/09/06 Compact resume template]

% Pass options such as a4paper or 11pt from \documentclass to article.
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{article}}
\ProcessOptions\relax
\LoadClass{article}

% Page margins: change the four geometry values below.
\RequirePackage[left=0.5in,top=0.5in,right=0.5in,bottom=0.5in]{geometry}
\RequirePackage{xcolor}
\RequirePackage{fontspec}
\RequirePackage{titlesec}
\RequirePackage{enumitem}
\RequirePackage{etoolbox}
\RequirePackage{needspace}
\RequirePackage[normalem]{ulem}
\RequirePackage{hyperref}

\pagestyle{empty}
\raggedbottom

% Font: replace the four OpenType filenames below; compile with XeLaTeX.
\setmainfont{lmroman10-regular.otf}[
  BoldFont=lmroman10-bold.otf,
  ItalicFont=lmroman10-italic.otf,
  BoldItalicFont=lmroman10-bolditalic.otf
]

% Colors: namecolor controls resume text and headings; linkblue controls links.
\definecolor{namecolor}{HTML}{293E49}
\definecolor{linkblue}{HTML}{003B73}

% Link colors and default PDF metadata; each resume can override its title and subject.
\hypersetup{
  colorlinks=true,
  urlcolor=linkblue,
  linkcolor=linkblue,
  pdftitle={Resume},
  pdfauthor={},
  pdfsubject={},
  pdfkeywords={},
  pdfcreator={XeLaTeX},
  pdfproducer={}
}
\urlstyle{same}

% Link styling: replace \uline{#2} with #2 to remove underlining.
\newcommand{\resumelink}[2]{\href{#1}{\uline{#2}}}

% Edit-once contact links. Email display and mailto target use the same value.
% Phone display keeps its formatting; tel removes spaces, parentheses, dots,
% and hyphens. Supply +countrycode and 7--15 digits; extensions are not parsed.
% These helpers accept literal text, not custom commands. Email also accepts
% \_ for an underscore. For other formats, use \resumelink{target}{label}.
% Unsupported input is printed without a link and warned about, never guessed.
\ExplSyntaxOn
\tl_new:N \l__resume_contact_tl
\tl_new:N \l__resume_contact_target_tl
\cs_new_protected:Npn \__resume_contact_plain:n #1
  {
    \ClassWarning{resume}{Unsupported~#1~format;~contact~is~not~linked.\MessageBreak
      Check~the~contact~helper~instructions~or~use~
      \string\resumelink\space with~an~explicit~target~and~label}
    \tl_use:N \l__resume_contact_tl
  }
\NewDocumentCommand{\resumeemail}{m}
  {
    \group_begin:
    % Stringify before inspecting or printing: raw _ remains ordinary text,
    % and commands supplied as values cannot execute during these checks.
    \tl_set:Nx \l__resume_contact_tl { \tl_to_str:n {#1} }
    \tl_trim_spaces:N \l__resume_contact_tl
    \regex_replace_all:nnN { \\ _ } { _ } \l__resume_contact_tl
    % The replacement underscore inherits its source catcode; make it text.
    \tl_set:Nx \l__resume_contact_tl { \tl_to_str:V \l__resume_contact_tl }
    \exp_args:NnV \regex_match:nnTF
      {
        \A [A-Za-z0-9_+\-]+ ( \. [A-Za-z0-9_+\-]+ )* @
        [A-Za-z0-9] ( [A-Za-z0-9\-]* [A-Za-z0-9] )?
        ( \. [A-Za-z0-9] ( [A-Za-z0-9\-]* [A-Za-z0-9] )? )+ \Z
      }
      \l__resume_contact_tl
      {
        \tl_set:Nx \l__resume_contact_target_tl
          { \tl_to_str:n {mailto:}\exp_not:V \l__resume_contact_tl }
        \exp_args:NVV \resumelink \l__resume_contact_target_tl \l__resume_contact_tl
      }
      { \__resume_contact_plain:n {email} }
    \group_end:
  }
\NewDocumentCommand{\resumephone}{m}
  {
    \group_begin:
    \tl_set:Nx \l__resume_contact_tl { \tl_to_str:n {#1} }
    \tl_trim_spaces:N \l__resume_contact_tl
    \tl_set_eq:NN \l__resume_contact_target_tl \l__resume_contact_tl
    \regex_replace_all:nnN { [\s().\-] } { } \l__resume_contact_target_tl
    \exp_args:NnV \regex_match:nnTF { \A \+ [1-9][0-9]{6,14} \Z }
      \l__resume_contact_target_tl
      {
        % hyperref needs the colon to be an ordinary character, not an
        % expl3 letter, or it treats the URI as a file destination.
        \tl_put_left:Nx \l__resume_contact_target_tl { \tl_to_str:n {tel:} }
        \exp_args:NVV \resumelink \l__resume_contact_target_tl \l__resume_contact_tl
      }
      { \__resume_contact_plain:n {phone} }
    \group_end:
  }
\ExplSyntaxOff

% Automatic reminders for the template's sample values and [bracketed prompts].
% Inspect only content passed to the resume commands below, without expanding
% user macros or printing their values in the log. TeX has already removed comments.
\ExplSyntaxOn
\tl_new:N \l__resume_check_tl
\bool_new:N \l__resume_placeholder_bool
\cs_new_protected:Npn \__resume_match:n #1
  {
    \exp_args:NnV \regex_match:nnT {#1} \l__resume_check_tl
      { \bool_set_true:N \l__resume_placeholder_bool }
  }
\cs_new_protected:Npn \resumecheckfield #1#2#3
  {
    \tl_set:Nx \l__resume_check_tl { \tl_to_str:n {#3} }
    % This separator has no arguments: a following [Phone] is visible content.
    \regex_replace_all:nnN { \\ contactsep \s+ } { } \l__resume_check_tl
    % Ignore optional command arguments such as \item[label] or \\[3pt].
    \regex_replace_all:nnN
      { \\ ( [A-Za-z@]+ \s* \*? | \\ ) ( \s* \[ [^\[\]]* \] )+ }
      { } \l__resume_check_tl
    \bool_set_false:N \l__resume_placeholder_bool
    \__resume_match:n { \[ [^\[\]]* \] }
    \str_case:nn {#2}
      {
        {name}{ \__resume_match:n { \A \s* Your \s+ Name \s* \Z } }
        {contact}{
          \__resume_match:n
            { hello@example\.com | your-handle |
              \+1 [\s().\-]* 555 [\s().\-]* 555 [\s().\-]* 5555 |
              City,? \s+ Region }
        }
        {role}{ \__resume_match:n { \A \s* Issuing \s+ Organization \s* \Z } }
        {organization}{
          \__resume_match:n
            { \A \s* ( Company \s+ [A-E] | Company \s+ Name |
              Organization \s+ Name | Project \s+ Name | Certification \s+ Name |
              Professional \s+ Certification | Additional \s+ Certification ) \s* \Z }
        }
        {location}{ \__resume_match:n { \A \s* City,? \s+ Region \s* \Z } }
        {dates}{ \__resume_match:n { Month \s+ Year | \A \s* Year \s* \Z } }
      }
    \bool_if:NT \l__resume_placeholder_bool
      {
        \ClassWarning{resume}{Placeholder~reminder~in~#1.\MessageBreak
          Replace~sample~values~and~bracketed~prompts~before~sharing}
      }
  }
\ExplSyntaxOff

% Set a page budget in resume.tex with \resumepagelimit{1} or {2}.
% Removing that line disables the reminder. No layout values are changed.
% Read the kernel's shipped-page count after the final page, not the page
% number or a previous build's .aux file. This also handles page-number resets.
\ExplSyntaxOn
\int_new:N \g__resume_page_limit_int
\NewDocumentCommand{\resumepagelimit}{m}
  {
    % Bound the accepted decimal length to avoid TeX integer overflow.
    % Do not expand custom commands or include the supplied value in the log.
    \regex_match:nnTF { \A \s* [1-9][0-9]{0,8} \s* \Z } {#1}
      { \int_gset:Nn \g__resume_page_limit_int {#1} }
      {
        \ClassWarning{resume}{Invalid~page~limit.\MessageBreak
          Use~a~whole~number~from~1~to~999999999,~such~as~
          \string\resumepagelimit{1}.\MessageBreak
          The~previous~page~limit~has~not~changed}
      }
  }
\AddToHook{enddocument/afterlastpage}[resume/page-limit]
  {
    \int_compare:nNnT { \g__resume_page_limit_int } > {0}
      {
        \int_compare:nNnT { \ReadonlyShipoutCounter } > { \g__resume_page_limit_int }
          {
            \ClassWarningNoLine{resume}{Page~limit~exceeded:
              \space\int_use:N \ReadonlyShipoutCounter\space pages;~limit
              \space\int_use:N \g__resume_page_limit_int.\MessageBreak
              Cut~less~relevant~content~or~change~\string\resumepagelimit
              \space if~the~extra~page~is~intentional.\MessageBreak
              Font~size~and~spacing~have~not~changed}
          }
      }
  }
\ExplSyntaxOff

\setlength{\parindent}{0pt}
\setlength{\parskip}{0pt}

% Header styling: adjust the name size, contact size, and vertical gaps here.
\newcommand{\resumename}[1]{%
  \resumecheckfield{resume name}{name}{#1}%
  \noindent{\fontsize{30}{36}\selectfont\color{namecolor}\textbf{#1}}\par
  \vspace{6pt}%
}

\newcommand{\contactsep}{\enspace\ensuremath{\diamond}\enspace}

\newcommand{\resumecontact}[1]{%
  \resumecheckfield{contact details}{contact}{#1}%
  {\small\color{namecolor}#1}\par
  \vspace{8pt}{\color{black!60}\hrule height 0.5pt}%
}

% Section styling: adjust heading typography, divider, and spacing below.
\titleformat{\section}
  {\large\bfseries\color{namecolor}}
  {}{0pt}{}
  [\vspace{6pt}{\color{black!60}\hrule height 0.5pt}]

\titlespacing*{\section}{0pt}{9pt}{6pt}

\newlength{\jobdutiesvspace}
\newcounter{resumeentry}
\newsavebox{\resumeorganizationbox}
\newsavebox{\resumedatesbox}
\newsavebox{\resumeheadingbox}
\newlength{\resumedateswidth}
\newlength{\resumeorganizationwidth}
\newlength{\resumeentryspace}

% Keep the original single-line layout when it fits. Otherwise, wrap the
% organization/location beside dates. Dates use at most 40% of the line;
% a 1em gap separates the columns. No font sizes or margins are reduced.
\newcommand{\resumeentryheading}[3]{%
  \sbox{\resumeorganizationbox}{\color{namecolor}\textbf{#1}\ifblank{#2}{}{\space--\space#2}}%
  \sbox{\resumedatesbox}{\small\textbf{\color{namecolor}#3}}%
  \ifdim\dimexpr\wd\resumeorganizationbox+\wd\resumedatesbox+2\tabcolsep\relax>\linewidth
    \setlength{\resumedateswidth}{\wd\resumedatesbox}%
    \ifdim\resumedateswidth>0.4\linewidth
      \setlength{\resumedateswidth}{0.4\linewidth}%
    \fi
    \setlength{\resumeorganizationwidth}{\dimexpr\linewidth-\resumedateswidth-1em\relax}%
    \sbox{\resumeheadingbox}{%
      \begin{tabular}{@{}p{\resumeorganizationwidth}@{\hspace{1em}}p{\resumedateswidth}@{}}
        \raggedright\leavevmode{\color{namecolor}\textbf{#1}\ifblank{#2}{}{\space--\space#2}} &
        \raggedleft\small\leavevmode\textbf{\color{namecolor}#3}\tabularnewline
      \end{tabular}%
    }%
  \else
    \sbox{\resumeheadingbox}{%
      \begin{tabular*}{\linewidth}{@{}l@{\extracolsep{\fill}}r@{}}
        \usebox{\resumeorganizationbox} & \usebox{\resumedatesbox}
      \end{tabular*}%
    }%
  \fi
  % Reserve space for wrapped headings and the role that follows them.
  \setlength{\resumeentryspace}{\dimexpr\ht\resumeheadingbox+\dp\resumeheadingbox+3\baselineskip\relax}%
  \ifdim\resumeentryspace<5\baselineskip
    \setlength{\resumeentryspace}{5\baselineskip}%
  \fi
  \Needspace{\resumeentryspace}%
  \vspace{8pt}%
  \noindent\usebox{\resumeheadingbox}\par\nopagebreak%
}

% \jobentry[Optional summary]{Title}{Company}{Location}{Dates}
% Pass {} for Location to omit it.
% The gap before jobduties is 5pt with a summary and 3pt without.
\newcommand{\jobentry}[5][]{%
  \stepcounter{resumeentry}%
  \resumecheckfield{entry \arabic{resumeentry} summary}{summary}{#1}%
  \resumecheckfield{entry \arabic{resumeentry} role}{role}{#2}%
  \resumecheckfield{entry \arabic{resumeentry} organization}{organization}{#3}%
  \resumecheckfield{entry \arabic{resumeentry} location}{location}{#4}%
  \resumecheckfield{entry \arabic{resumeentry} dates}{dates}{#5}%
  \ifblank{#1}{\setlength{\jobdutiesvspace}{3pt}}{\setlength{\jobdutiesvspace}{5pt}}%
  \resumeentryheading{#3}{#4}{#5}%
  \vspace{1pt}%
  {\color{namecolor}\textit{#2}}\par\nopagebreak%
  \ifblank{#1}{}{%
    \vspace{4pt}%
    {\small\itshape\color{namecolor}#1\/}\par\nopagebreak%
  }%
  \par\nopagebreak%
}

% Entry bullets: adjust line spacing, marker, indentation, and list spacing here.
\NewDocumentEnvironment{jobduties}{+b}{%
  \resumecheckfield{entry \arabic{resumeentry} bullets}{bullets}{#1}%
  \vspace{\jobdutiesvspace}%
  \color{namecolor}\normalfont%
  \linespread{1.06}\selectfont%
  \begin{itemize}[
    leftmargin=*,
    label=\textbullet,
    topsep=2pt,
    itemsep=2pt,
    parsep=0pt,
    partopsep=0pt
  ]
  #1%
  \end{itemize}
  \vspace{4pt}%
}{}

% Skills bullets: change these values if skills should use a different list style.
\NewDocumentEnvironment{skillitems}{+b}{%
  \resumecheckfield{skills bullets}{bullets}{#1}%
  \vspace{8pt}%
  \color{namecolor}\normalfont%
  \linespread{1.06}\selectfont%
  \begin{itemize}[
    leftmargin=*,
    label=\textbullet,
    topsep=2pt,
    itemsep=2pt,
    parsep=0pt,
    partopsep=0pt
  ]
  #1%
  \end{itemize}
  \vspace{4pt}%
}{}
