import unittest

from scripts.render_pdf import markdown_to_html

CSS = "body{}"


def html_for(md):
    return markdown_to_html(md, CSS)


class TestMarkdownToHtml(unittest.TestCase):
    def test_name_becomes_h1(self):
        self.assertIn("<h1>Jordan Rivera</h1>", html_for("# Jordan Rivera\n"))

    def test_section_and_role_headings(self):
        out = html_for("## Experience\n\n### Engineer, Acme — 2020\n")
        self.assertIn("<h2>Experience</h2>", out)
        self.assertIn("<h3>Engineer, Acme — 2020</h3>", out)

    def test_bullets_become_one_list(self):
        out = html_for("- first\n- second\n")
        self.assertEqual(out.count("<ul>"), 1)
        self.assertEqual(out.count("</ul>"), 1)
        self.assertIn("<li>first</li>", out)
        self.assertIn("<li>second</li>", out)

    def test_a_heading_closes_the_open_list(self):
        # Without this the second role's bullets nest inside the first role's
        # list, which renders as an indented sub-list and reads as subordinate
        # work rather than a separate job.
        out = html_for("- a\n\n### Next Role\n\n- b\n")
        self.assertEqual(out.count("<ul>"), 2)
        self.assertLess(out.index("</ul>"), out.index("<h3>"))

    def test_contact_line_is_a_paragraph(self):
        out = html_for("# Jordan Rivera\n\nSpringfield, IL · jordan@example.com\n")
        self.assertIn("<p>Springfield, IL · jordan@example.com</p>", out)

    def test_html_special_characters_are_escaped(self):
        # A bullet containing < or & must not become markup. "C++ & <T>" is
        # ordinary resume text.
        out = html_for("- Wrote C++ & <T> templates\n")
        self.assertIn("C++ &amp; &lt;T&gt;", out)
        self.assertNotIn("<T>", out)

    def test_inline_bold_and_italic_survive_escaping(self):
        out = html_for("- Shipped **fast** and _early_\n")
        self.assertIn("<strong>fast</strong>", out)
        self.assertIn("<em>early</em>", out)

    def test_underscores_inside_words_are_not_italics(self):
        # snake_case identifiers appear in real bullets.
        out = html_for("- Renamed max_lines to line_budget\n")
        self.assertNotIn("<em>", out)
        self.assertIn("max_lines", out)

    def test_blank_lines_do_not_create_empty_paragraphs(self):
        self.assertNotIn("<p></p>", html_for("# A\n\n\n\n## B\n"))

    def test_unsupported_heading_depth_raises(self):
        # Guessing is how a converter silently drops content.
        with self.assertRaises(ValueError):
            html_for("#### Too deep\n")

    def test_css_is_inlined(self):
        self.assertIn("body{}", html_for("# A\n"))


if __name__ == "__main__":
    unittest.main()
