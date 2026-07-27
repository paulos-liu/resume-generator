<!--
Calibration procedure for max_lines.

READ THIS FIRST: max_lines is enforced against the DRAFT MARKDOWN, not the
rendered page. scripts/check_hard_rules.py counts non-blank lines of draft.md,
where one bullet is one line however far it wraps. So what you are measuring is
"how many markdown lines fit on one rendered page" -- NOT "how many lines
appear on page 1". Those differ by the wrap factor: at ~140-character bullets,
about 1.5x. Measuring the wrong one yields a budget roughly 50% too generous,
and a two-page resume then passes a one-page check.

  1. Fill every section below with filler bullets at the length your drafts
     actually use. Check preferences/style.md and a real draft -- do not assume
     ~90 chars. Bullet length is an input to this measurement, not a detail.
  2. Render the filled template. Two paths, depending on what is available:
       - scripts/render_pdf.py <draft.md> --measure, which drives headless
         Chrome and reports a real page count. Works wherever Chrome or
         Chromium is installed.
       - the render-resume skill (plugin/skills/render-resume/SKILL.md), an
         agent skill invoked through the assistant, where a docx tool exists.
  3. Add or remove filler bullets and re-render until the output is exactly one
     full page -- as full as it goes without spilling onto a second.
  4. Now count the non-blank lines of the MARKDOWN that produced that page,
     including headings and the name/contact line. That number is max_lines.
  5. Record it in preferences/hard-rules.md with the date and the bullet length
     it assumes. Recalibrate when the template, the stylesheet, or the house
     bullet length changes -- any of the three invalidates the number.

The measurement is per-user and belongs in preferences/hard-rules.md, not here:
this file is shared and that number is not. The value shipped in a fresh copy is
an UNCALIBRATED PLACEHOLDER, never a measurement, and hard-rules.md says so
until someone runs this procedure.

Note the budget is not linear. templates/print.css avoids stranding a heading at
the foot of a page, so one extra bullet can push a whole heading-plus-bullets
block onto page two rather than spilling a single line.
-->

# {{full_name}}

{{location}} · {{email}} · {{links}}

## Experience

### {{title}}, {{company}} — {{start}}–{{end}}

- {{bullet}}

## Projects

### {{project_name}} — {{start}}–{{end}}

- {{bullet}}

## Skills

{{skills_line}}

## Education

{{education_line}}
