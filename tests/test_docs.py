"""Offline documentation checks. No network, no device, no repository writes.

These catch the failure that made the first device comparison unusable: a cell
citing a source key that nothing defines.
"""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parent.parent
COMPARISONS = ROOT / "docs/comparisons"

# A cell citation is the key inside brackets, optionally followed by a label
# letter: [S3], [S3 D], [T]. A bare [S3] inside running prose counts too.
KEY = re.compile(r"\[((?:S\d+)|T)(?=[\s\]]|$)")
REGISTER_ROW = re.compile(r"^\|\s*((?:S\d+)|T)\s*\|", re.M)
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def register_keys(text: str) -> set[str]:
    return set(REGISTER_ROW.findall(text))


def cited_keys(text: str) -> set[str]:
    return set(KEY.findall(text))


class SourceRegisterTests(unittest.TestCase):
    def setUp(self):
        self.sources = (COMPARISONS / "sources.md").read_text()

    def test_sources_page_exists_and_has_rows(self):
        self.assertTrue(self.sources.strip())
        self.assertGreaterEqual(len(register_keys(self.sources)), 1)

    def test_every_cited_key_is_defined(self):
        defined = register_keys(self.sources)
        for page in sorted(COMPARISONS.glob("*.md")):
            if page.name == "sources.md":
                continue
            missing = sorted(cited_keys(page.read_text()) - defined)
            self.assertEqual(missing, [], f"{page.name} cites undefined keys {missing}")

    def test_every_register_entry_has_a_url_and_a_date(self):
        for line in self.sources.splitlines():
            if not REGISTER_ROW.match(line):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            key = cells[0]
            # A key is either a URL or a repository-relative link to a record.
            self.assertTrue(
                any("http://" in c or "https://" in c or "](" in c for c in cells[1:]),
                f"{key} has no URL or link",
            )
            self.assertTrue(
                any(re.fullmatch(r"\d{4}-\d{2}-\d{2}", c) for c in cells),
                f"{key} has no read date",
            )

    def test_register_keys_are_unique(self):
        keys = REGISTER_ROW.findall(self.sources)
        duplicates = {k for k in keys if keys.count(k) > 1}
        self.assertEqual(duplicates, set())


class RelativeLinkTests(unittest.TestCase):
    def test_local_markdown_links_resolve(self):
        for page in sorted(COMPARISONS.glob("*.md")):
            for target in MARKDOWN_LINK.findall(page.read_text()):
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                path = (page.parent / target.split("#", 1)[0]).resolve()
                self.assertTrue(path.exists(), f"{page.name} links to missing {target}")


if __name__ == "__main__":
    unittest.main()
