"""Maya — Visual Director (CC subagent).

Receives Quill's article copy path + spec from Marco.
Generates 2 header images via Higgsfield AI, selects the stronger one,
merges copy + image into the article skeleton, and stages the files.
"""

import json

from agents.base import call_cc_agent, read_file, log
from agents.prompts import MAYA_PROMPT


def run(article_path: str, spec: dict) -> str:
    """
    Generate images, select best, merge into article skeleton.
    Stages img files + merged HTML (no push).
    Returns the merged article path.
    """
    slug = spec["slug"]
    number = spec.get("number", 0)
    og_image = spec["og_image"]
    title = spec["title"]
    mood = spec.get("mood", "analytical")

    try:
        article_copy = read_file(article_path)
    except FileNotFoundError:
        raise RuntimeError(f"[maya] Article copy not found at: {article_path}")

    user_input = f"""\
ARTICLE SPEC:
{json.dumps(spec, indent=2)}

ARTICLE COPY PATH: {article_path}

ARTICLE COPY (first 500 chars for context):
{article_copy[:500]}...

INSTRUCTIONS:
1. Generate 2 header images via Higgsfield AI (model: nano_banana_pro, ratio: 16:9)
   - Base prompts on: "{title}" with mood "{mood}"
   - Vary the visual angle between the two
   - Resize each to 1200×630 JPG via PIL

2. Save primary image to:   {og_image}
   Save alternate image to: img/alt-img/aima-{number:03d}-{slug.replace(f'aima-{number:03d}-', '')}-alt.jpg

3. Merge the article copy at {article_path} with the primary image into the full article skeleton.
   - Wire og:image meta tag to: {og_image}
   - Apply stat grid, pullquote, glossary, section spacing
   - DO NOT edit article copy

4. Stage files (NO push):
   git add {og_image}
   git add img/alt-img/aima-{number:03d}-{slug.replace(f'aima-{number:03d}-', '')}-alt.jpg
   git add {article_path}

Return the merged article path: {article_path}\
"""

    log.info(f"[maya] generating images + merging article: {slug}")
    call_cc_agent("maya", MAYA_PROMPT, user_input)

    log.info(f"[maya] merge complete: {article_path}")
    return article_path
