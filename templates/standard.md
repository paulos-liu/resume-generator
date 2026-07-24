<!--
Calibration procedure for max_lines:
  1. Fill every section below with filler bullets of typical length (~90 chars).
  2. Render the filled template using the render-resume skill
     (plugin/skills/render-resume/SKILL.md) -- it is an agent skill, invoked
     through the assistant, not a script. There is no `python3 <path>` form of
     this step; render-resume itself only works where a docx-rendering tool is
     available (e.g. Cowork), and says so plainly when it is not.
  3. Count non-blank lines that fit on page 1, including heading lines (section
     headings and the name/contact line count -- they occupy vertical space on
     the page exactly like a bullet does). That number is max_lines.
  4. Record it in preferences/hard-rules.md and note the date there.

Calibration status: NOT YET RUN. The value shipped in preferences/hard-rules.md
(42) is an UNCALIBRATED DEFAULT, not a measurement -- this development
environment is stdlib-only (see AGENTS.md) with no docx/pandoc/LibreOffice
tooling, so step 2 cannot execute here. Run this procedure for real wherever
document rendering is actually available (setup's step 3, plugin/skills/setup/
SKILL.md) and replace this status line and the number/date in
preferences/hard-rules.md once it has.
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
