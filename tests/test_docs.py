"""Offline documentation checks. No network, no device, no repository writes.

These catch the failure that made the first device comparison unusable: a cell
citing a source key that nothing defines.
"""

import hashlib
from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlsplit


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
        pages = [page for page in sorted((ROOT / "docs").rglob("*.md"))
                 if "archive" not in page.parts]
        pages += sorted(COMPARISONS.glob("*.md"))
        for page in pages:
            for target in MARKDOWN_LINK.findall(page.read_text()):
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                path = (page.parent / target.split("#", 1)[0]).resolve()
                self.assertTrue(path.exists(), f"{page.relative_to(ROOT)} links to missing {target}")


class FrontDoorTests(unittest.TestCase):
    """Keep the beginner routes connected without checking archived dead links."""

    def test_entrypoint_links_and_heading_fragments_resolve(self):
        pages = (
            "README.md", "docs/README.md", "docs/guides/getting-started.md",
            "control/web/README.md", "tools/device/lab-pi5/README.md",
        )
        for name in pages:
            page = ROOT / name
            for target in MARKDOWN_LINK.findall(page.read_text()):
                url = urlsplit(target)
                if url.scheme or url.netloc:
                    continue
                path = (page.parent / unquote(url.path)).resolve() if url.path else page
                with self.subTest(page=name, target=target):
                    self.assertTrue(path.exists(), f"{name} links to missing {target}")
                    if url.fragment and path.suffix == ".md":
                        self.assertIn(unquote(url.fragment), self.heading_ids(path))

    @staticmethod
    def heading_ids(page):
        # Scoped to these guides' plain ATX headings; skip fenced examples.
        ids = set()
        fenced = False
        for line in page.read_text().splitlines():
            if line.startswith("```"):
                fenced = not fenced
            if fenced:
                continue
            match = re.match(r"^#{1,6}\s+(.+?)(?:\s+#+)?$", line)
            if match:
                slug = re.sub(r"[^\w\- ]", "", match[1].lower()).replace(" ", "-")
                unique = slug
                suffix = 0
                while unique in ids:
                    suffix += 1
                    unique = f"{slug}-{suffix}"
                ids.add(unique)
        return ids

    def test_readme_routes_to_getting_started_and_preserved_history(self):
        links = MARKDOWN_LINK.findall((ROOT / "README.md").read_text())
        self.assertIn("docs/guides/getting-started.md", links)
        self.assertIn("docs/archive/readme-research-before-2026-11-15.md", links)

    def test_historical_readme_section_is_preserved(self):
        # Original README at ac2298c, from "# Historical research notes" onward.
        # Only trailing whitespace is normalized; wording/URLs must not drift.
        text = (ROOT / "docs/archive/readme-research-before-2026-11-15.md").read_text()
        section = text.split("# Historical research notes", 1)[1]
        normalized = "\n".join(line.rstrip() for line in section.splitlines()) + "\n"
        self.assertEqual(
            hashlib.sha256(normalized.encode()).hexdigest(),
            "1cbe7520a5d95f3d2b63e9bbc07bbe8d1d571a63a0441ca17109b7603aa205eb",
        )


IMAGE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")


class AssetTests(unittest.TestCase):
    """An image that does not exist renders as a broken box and nothing else.

    Pictures are committed beside the document that shows them, so a moved or
    renamed file is a documentation bug the reader sees first. Check every
    image reference in docs/ and models/, and every local link in models/.
    """

    def pages(self):
        for folder in (ROOT / "docs", ROOT / "models"):
            for page in sorted(folder.rglob("*.md")):
                if ".local" in page.parts:
                    continue
                yield page

    def test_every_referenced_image_exists(self):
        checked = 0
        for page in self.pages():
            for target in IMAGE.findall(page.read_text()):
                if target.startswith(("http://", "https://", "data:")):
                    continue
                checked += 1
                path = (page.parent / target.split("#", 1)[0]).resolve()
                self.assertTrue(
                    path.exists(),
                    f"{page.relative_to(ROOT)} embeds missing image {target}",
                )
        self.assertGreater(checked, 0, "no image references found; the check is idle")

    def test_model_folder_links_resolve(self):
        for page in sorted((ROOT / "models").rglob("*.md")):
            for target in MARKDOWN_LINK.findall(page.read_text()):
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                path = (page.parent / target.split("#", 1)[0]).resolve()
                self.assertTrue(
                    path.exists(),
                    f"{page.relative_to(ROOT)} links to missing {target}",
                )

    def test_committed_images_are_referenced(self):
        """No orphan renders: an asset folder is for pictures a page shows."""
        for assets in sorted(ROOT.glob("models/**/assets")):
            text = ""
            for page in assets.parent.rglob("*.md"):
                text += page.read_text()
            for image in sorted(assets.iterdir()):
                if image.is_file():
                    self.assertIn(
                        image.name,
                        text,
                        f"{image.relative_to(ROOT)} is committed but no page shows it",
                    )


if __name__ == "__main__":
    unittest.main()
