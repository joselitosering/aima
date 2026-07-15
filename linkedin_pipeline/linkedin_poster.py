"""
linkedin_poster.py — Posts an AIMA article to the AIMA LinkedIn company page.

Posts as urn:li:organization:{ORG_ID} so all three writers (Joselito, Dawn,
Kenji) share a single branded channel. Persona attribution is written into
the post commentary. Cover image is uploaded directly via LinkedIn Assets API
to guarantee the visual is always shown.

Requires scopes: w_organization_social
"""

import os, json, re, urllib.request, urllib.error, urllib.parse, mimetypes
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN", "").strip()
MEMBER_ID    = os.getenv("LINKEDIN_MEMBER_ID", "").strip()   # kept for image upload owner fallback
ORG_ID       = os.getenv("LINKEDIN_ORG_ID", "").strip()

LINKEDIN_API        = "https://api.linkedin.com/v2/ugcPosts"
LINKEDIN_ASSETS_API = "https://api.linkedin.com/v2/assets?action=registerUpload"
AIMA_COMPANY_PAGE   = "https://www.linkedin.com/company/aimaproductions"

# Persona display names for bylines (update as writers create LinkedIn profiles)
PERSONA_BYLINES = {
    "joselito": "Joselito Sering · Editor-in-Chief, AIMA",
    "dawn":     "Dawn Ginhaua · Cultural Critic & Educator, AIMA",
    "kenji":    "Kenji Nakamoto · Contributing Writer, AIMA",
}

# Hashtag library — brand anchors + audience/topic tags per keyword
BRAND_TAGS = ["#AIMA", "#AIForGood"]

HASHTAG_MAP = {
    "ai society":          ["#AISociety", "#TechForGood", "#DigitalInclusion", "#FutureOfWork"],
    "ai ethics":           ["#AIEthics", "#ResponsibleAI", "#TechEthics", "#HumanCenteredAI"],
    "ai healthcare":       ["#HealthTech", "#AIinHealthcare", "#MedicalAI", "#DigitalHealth"],
    "medicine":            ["#HealthTech", "#AIinHealthcare", "#MedicalAI", "#DigitalHealth"],
    "creative":            ["#CreativeTech", "#AIArt", "#ContentCreators", "#DigitalCreativity"],
    "media":               ["#MediaIndustry", "#DigitalMedia", "#ContentStrategy", "#Journalism"],
    "policy":              ["#AIPolicy", "#TechPolicy", "#DigitalGovernance", "#Regulation"],
    "workforce":           ["#FutureOfWork", "#AIWorkforce", "#JobMarket", "#CareerDevelopment"],
    "education":           ["#EdTech", "#AIinEducation", "#LearningAndDevelopment", "#SkillsGap"],
    "finance":             ["#FinTech", "#AIinFinance", "#WealthManagement", "#InvestmentTech"],
    "philanthropy":        ["#SocialImpact", "#Philanthropy", "#GenerationalWealth", "#ImpactInvesting"],
    "global south":        ["#GlobalSouth", "#DigitalEquity", "#EmergingMarkets", "#TechInclusion"],
    "philippines":         ["#Philippines", "#PhilippinesTech", "#SEAsia", "#AseanTech"],
    "music":               ["#MusicIndustry", "#MusicTech", "#IndependentArtist", "#AIMusic"],
    "video":               ["#VideoProduction", "#FilmIndustry", "#ContentCreation", "#Filmmaking"],
    "agent":               ["#AIAgents", "#Automation", "#GenAI", "#LLM"],
    "hallucination":       ["#AIEthics", "#ResponsibleAI", "#MachineLearning", "#GenAI"],
    "bias":                ["#AIBias", "#FairAI", "#AlgorithmicFairness", "#DEI"],
    "climate":             ["#ClimateAI", "#Sustainability", "#GreenTech", "#ClimateChange"],
    "security":            ["#CyberSecurity", "#AIThreat", "#DigitalSafety", "#InfoSec"],
    "startup":             ["#Startups", "#Entrepreneurship", "#VentureCapital", "#Innovation"],
    "surveillance":        ["#SurveillanceCapitalism", "#DigitalRights", "#Privacy", "#DataJustice"],
    "labor":               ["#FutureOfWork", "#LaborRights", "#WorkerProtection", "#AIAndLabor"],
    "inequality":          ["#DigitalDivide", "#TechEquity", "#SocialJustice", "#EconomicInequality"],
    "misinformation":      ["#MediaLiteracy", "#Misinformation", "#DigitalTrust", "#InformationIntegrity"],
    "accountability":      ["#CorporateAccountability", "#AIGovernance", "#TechPolicy", "#Transparency"],
    "feminist":            ["#WomenInTech", "#GenderEquity", "#FeministTech", "#InclusiveAI"],
    "aerospace":           ["#SpaceTech", "#Aerospace", "#SpaceExploration", "#NewSpace"],
    "robotics":            ["#Robotics", "#Automation", "#AutonomousSystems", "#RoboticsFuture"],
    "blockchain":          ["#Blockchain", "#Web3", "#DecentralizedTech", "#DeFi"],
    "manufacturing":       ["#AdvancedManufacturing", "#Industry40", "#3DPrinting", "#SmartFactory"],
    "cybernetics":         ["#Cybernetics", "#BrainComputerInterface", "#Bioengineering", "#HumanAugmentation"],
    "space":               ["#SpaceTech", "#SpaceExploration", "#Aerospace", "#FutureOfSpace"],
    "biotech":             ["#Biotech", "#Biotechnology", "#LifeSciences", "#SyntheticBiology"],
    "clean energy":        ["#CleanEnergy", "#Renewables", "#EnergyTransition", "#ClimateAction"],
    "food":                ["#FoodTech", "#Agritech", "#FutureOfFood", "#SustainableFood"],
}


# ── Metadata extraction ──────────────────────────────────────────────────────

def extract_metadata(html_content, filename, html_url):
    # Prefer og:title (always the clean headline). Fall back to <title> with HTML
    # comments stripped FIRST — the skeleton's authoring comment contains the
    # literal text "<title> tag", which made the old <title>…</title> DOTALL
    # regex start inside that comment and capture the whole checklist as the
    # title (garbled #25 LinkedIn post, 2026-07-14). Decode entities so e.g.
    # "America&#x27;s" posts as "America's", and drop the " — AIMA Magazine" suffix.
    import html as _html
    og_m = re.search(r'<meta\s+property=["\']og:title["\']\s+content="([^"]*)"',
                     html_content, re.IGNORECASE) or \
           re.search(r'<meta\s+content="([^"]*)"\s+property=["\']og:title["\']',
                     html_content, re.IGNORECASE)
    if og_m:
        title = og_m.group(1).strip()
    else:
        no_comments = re.sub(r"<!--.*?-->", "", html_content, flags=re.DOTALL)
        title_m = re.search(r"<title[^>]*>(.*?)</title>", no_comments, re.IGNORECASE | re.DOTALL)
        title   = title_m.group(1).strip() if title_m else \
                  filename.replace(".html","").replace("-"," ").title()
    title = _html.unescape(title)
    title = re.sub(r"\s*[—\-|]\s*AIMA(?:\s+Magazine)?\s*$", "", title).strip()

    # Use quote-specific patterns so apostrophes in content don't truncate early.
    # Try name= first (most common), then reversed attribute order.
    desc_m = re.search(r'<meta\s+name=["\']description["\']\s+content="([^"]*)"',
                       html_content, re.IGNORECASE)
    if not desc_m:
        desc_m = re.search(r"<meta\s+name=[\"']description[\"']\s+content='([^']*)'",
                           html_content, re.IGNORECASE)
    if not desc_m:
        desc_m = re.search(r'<meta\s+content="([^"]*)"\s+name=["\']description["\']',
                           html_content, re.IGNORECASE)
    if not desc_m:
        desc_m = re.search(r"<meta\s+content='([^']*)'\s+name=[\"']description[\"']",
                           html_content, re.IGNORECASE)

    can_m      = re.search(r'<link\s+rel=["\']canonical["\']\s+href=["\'](.*?)["\']',
                           html_content, re.IGNORECASE)
    source_url = can_m.group(1).strip() if can_m else html_url

    # LinkedIn posts always link to the production domain
    source_url = re.sub(
        r'https?://joselitosering\.github\.io/aima/',
        'https://aima.productions/',
        source_url
    )

    if desc_m:
        description = desc_m.group(1).strip()
    else:
        body = re.sub(r"<!--.*?-->", "", html_content, flags=re.DOTALL)
        body = re.sub(r"<[^>]+>", " ", body)
        body = re.sub(r"\s+", " ", body).strip()
        description = (body[:300] + "...") if len(body) > 300 else body
    description = _html.unescape(description)   # entities → text, so no "&#x27;" in the post

    if not source_url:
        source_url = "https://github.com/joselitosering/aima"

    return title, description[:700], source_url


def add_utm(url, article_name, content="org_post"):
    """
    Append UTM parameters to a URL for GA4 attribution.
      utm_source   = linkedin
      utm_medium   = social
      utm_campaign = article slug (filename without .html)
      utm_content  = org_post | personal_reshare
    Safe to call on URLs that may already have a query string.
    """
    slug = article_name.replace(".html", "").replace(".htm", "")
    params = urllib.parse.urlencode({
        "utm_source":   "linkedin",
        "utm_medium":   "social",
        "utm_campaign": slug,
        "utm_content":  content,
    })
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{params}"


def generate_hashtags(html_content, title, description):
    cat_m = re.search(
        r'<meta\s+name=["\']article:category["\']\s+content=["\'](.*?)["\']',
        html_content, re.IGNORECASE
    )
    category = cat_m.group(1).strip().lower() if cat_m else ""
    searchable = f"{category} {title} {description}".lower()

    matched = []
    for keyword, tags in HASHTAG_MAP.items():
        if keyword in searchable:
            matched.extend(tags)

    seen = set(); result = []
    for tag in matched:
        if tag not in seen:
            seen.add(tag); result.append(tag)
        if len(result) >= 8:
            break
    for tag in BRAND_TAGS:
        if tag not in seen:
            result.append(tag)
    return " ".join(result)


def extract_persona(html_content):
    """Return 'dawn', 'kenji', 'joselito', or None from article:persona meta tag."""
    m = re.search(
        r'<meta\s+name=["\']article:persona["\']\s+content=["\'](.*?)["\']',
        html_content, re.IGNORECASE
    )
    return m.group(1).strip().lower() if m else None


def extract_og_image(html_content):
    m = re.search(
        r'<meta\s+property=["\']og:image["\']\s+content=["\'](.*?)["\']',
        html_content, re.IGNORECASE
    )
    if not m:
        m = re.search(
            r'<meta\s+content=["\'](.*?)["\']\s+property=["\']og:image["\']',
            html_content, re.IGNORECASE
        )
    return m.group(1).strip() if m else None



def extract_hook(html_content, max_sentences=2, max_chars=420):
    """
    Pull the first 1-2 sentences of the article lead paragraph.
    Targets <p class="article-lead"> first (guaranteed hook), then falls back
    to the first general <p> with > 120 chars.
    Skips script, style, nav, header, footer, and aside blocks first.
    """
    clean = re.sub(r'<(script|style|nav|header|footer|aside)[^>]*>.*?</\1>', '',
                   html_content, flags=re.DOTALL | re.IGNORECASE)

    # Prefer the explicit article-lead paragraph over generic scanning
    lead_m = re.search(
        r'<p[^>]*class=["\'][^"\']*article-lead[^"\']*["\'][^>]*>(.*?)</p>',
        clean, re.DOTALL | re.IGNORECASE
    )
    paragraphs = ([lead_m.group(1)] if lead_m else []) + \
                 re.findall(r'<p[^>]*>(.*?)</p>', clean, re.DOTALL | re.IGNORECASE)
    for p in paragraphs:
        text = re.sub(r'<[^>]+>', '', p).strip()
        text = re.sub(r'&#?\w+;', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) < 120:
            continue
        # Split on sentence boundaries, keep first N sentences up to max_chars
        parts = re.split(r'(?<=[.!?])\s+(?=[A-Z\u201c\u2018\u0022])', text)
        hook = ''
        for s in parts[:max_sentences]:
            candidate = (hook + ' ' + s).strip() if hook else s
            if len(candidate) <= max_chars:
                hook = candidate
            else:
                break
        if hook:
            return hook
    return None

# ── LinkedIn image upload ────────────────────────────────────────────────────

def _register_upload():
    """Register an image upload. Owner is the AIMA company page."""
    owner = f"urn:li:organization:{ORG_ID}" if ORG_ID else f"urn:li:person:{MEMBER_ID}"
    body = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": owner,
            "serviceRelationships": [
                {"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}
            ]
        }
    }
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(LINKEDIN_ASSETS_API, data=payload, method="POST")
    req.add_header("Authorization",             f"Bearer {ACCESS_TOKEN}")
    req.add_header("Content-Type",              "application/json")
    req.add_header("X-Restli-Protocol-Version", "2.0.0")

    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())

    http_req   = result["value"]["uploadMechanism"].get(
        "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest", {}
    )
    upload_url = http_req["uploadUrl"]
    asset_urn  = result["value"]["asset"]
    return upload_url, asset_urn


def _upload_image_bytes(upload_url, image_bytes, content_type="image/jpeg"):
    req = urllib.request.Request(upload_url, data=image_bytes, method="PUT")
    req.add_header("Authorization", f"Bearer {ACCESS_TOKEN}")
    req.add_header("Content-Type",  content_type)
    with urllib.request.urlopen(req) as resp:
        return resp.status


def upload_cover_image(image_url):
    print(f"  Downloading cover image: {image_url}")
    image_req = urllib.request.Request(image_url)
    image_req.add_header("User-Agent", "AIMA-Pipeline/1.0")
    with urllib.request.urlopen(image_req, timeout=30) as resp:
        image_bytes  = resp.read()
        content_type = resp.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()

    print(f"  Registering LinkedIn image upload ({len(image_bytes)//1024}KB, {content_type})...")
    upload_url, asset_urn = _register_upload()
    print(f"  Uploading image to LinkedIn...")
    status = _upload_image_bytes(upload_url, image_bytes, content_type)
    print(f"  Upload complete (HTTP {status}). Asset: {asset_urn}")
    return asset_urn



# ── Post to LinkedIn company page ────────────────────────────────────────────

def post_to_linkedin(article):
    if not ACCESS_TOKEN:
        raise ValueError("LINKEDIN_ACCESS_TOKEN not set — run linkedin_auth.py first.")
    if not ORG_ID:
        raise ValueError("LINKEDIN_ORG_ID not set — add it to .env (numeric company page ID).")

    title, description, source_url = extract_metadata(
        article["content"], article["name"], article["html_url"]
    )
    source_url = add_utm(source_url, article["name"], content="org_post")

    # -- Upload cover image --------------------------------------------------
    image_url = extract_og_image(article["content"])
    asset_urn = None

    if image_url:
        # og:image may be a relative path (e.g. "img/articles/...") — resolve to absolute.
        if image_url and not image_url.startswith("http"):
            image_url = "https://aima.productions/" + image_url.lstrip("/")
        try:
            asset_urn = upload_cover_image(image_url)
        except Exception as e:
            print(f"  WARNING: Image upload failed ({e}). Falling back to ARTICLE post.")
    else:
        print("  No og:image found — posting without image.")

    # -- Build commentary with persona byline --------------------------------
    persona  = extract_persona(article["content"])
    byline   = PERSONA_BYLINES.get(persona or "joselito", PERSONA_BYLINES["joselito"])
    hashtags = generate_hashtags(article["content"], title, description)

    hook = extract_hook(article["content"])
    body = hook if hook and len(hook) > 80 else description
    body = body[:500]   # cap to prevent oversized commentary

    if persona == "dawn":
        body_para = f"{body} Who benefits from this — and who never got asked?"
        cta       = f"Read the full cultural analysis: {source_url}"
    elif persona == "kenji":
        body_para = f"{body} The frontier is closer than the headlines suggest."
        cta       = f"Full breakdown: {source_url}"
    else:
        body_para = f"{body} The data, the sources, and the full argument are at the link."
        cta       = f"Read the full investigation: {source_url}"

    commentary = (
        f"\U0001F4D6 {title}\n\n"
        f"{body_para}\n\n"
        f"{cta}\n\n"
        f"{hashtags}\n\n"
        f"By {byline}"
    )
    commentary = commentary[:3900]  # LinkedIn hard limit is 4000

    # -- Build post payload --------------------------------------------------
    author_urn = f"urn:li:organization:{ORG_ID}"

    if asset_urn:
        media_obj            = {"status": "READY", "media": asset_urn, "title": {"text": title[:200]}}
        share_media_category = "IMAGE"
    else:
        media_obj            = {"status": "READY", "originalUrl": source_url,
                                "title":       {"text": title},
                                "description": {"text": description[:700]}}
        share_media_category = "ARTICLE"

    body = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary":    {"text": commentary},
                "shareMediaCategory": share_media_category,
                "media": [media_obj]
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }

    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(LINKEDIN_API, data=payload, method="POST")
    req.add_header("Authorization",             f"Bearer {ACCESS_TOKEN}")
    req.add_header("Content-Type",              "application/json")
    req.add_header("X-Restli-Protocol-Version", "2.0.0")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result  = json.loads(resp.read())
            ugc_id  = result.get("id", "")
            print(f"  Posted to company page | UGC ID: {ugc_id} | Mode: {share_media_category}")
            share_urn = _resolve_share_urn(ugc_id)
            return share_urn or ugc_id
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"  LinkedIn API error {e.code}: {error_body}")
        raise


def _resolve_share_urn(ugc_id):
    """
    Convert a ugcPost URN to the corresponding share URN needed for resharing.

    Race condition fix: previously grabbed the most-recently-modified org post,
    which returned the wrong URN during batch posting sessions.

    LinkedIn ugcPost and share URNs share the same numeric suffix:
      urn:li:ugcPost:7474175107142266880 -> urn:li:share:7474175107142266880

    We verify against /rest/posts by matching the numeric suffix, then fall back
    to direct numeric conversion if the API call fails or no match is found.
    """
    import time, urllib.parse

    # Extract numeric part from ugcPost URN (e.g. "7474175107142266880")
    ugc_numeric      = ugc_id.split(":")[-1] if ":" in ugc_id else ugc_id
    direct_share_urn = f"urn:li:share:{ugc_numeric}"

    time.sleep(2)
    org_urn = urllib.parse.quote(f"urn:li:organization:{ORG_ID}", safe="")
    url = (
        f"https://api.linkedin.com/rest/posts"
        f"?q=author&author={org_urn}&count=5&sortBy=LAST_MODIFIED"
    )
    req = urllib.request.Request(url)
    req.add_header("Authorization",             f"Bearer {ACCESS_TOKEN}")
    req.add_header("LinkedIn-Version",          "202506")
    req.add_header("X-Restli-Protocol-Version", "2.0.0")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data     = json.loads(resp.read())
            elements = data.get("elements", [])
            # Match by numeric suffix — race-condition-safe during batch posting
            for el in elements:
                share_id = el.get("id", "")
                if share_id.endswith(ugc_numeric):
                    print(f"  Resolved share URN (matched): {share_id}")
                    return share_id
            # Numeric match not found — use direct conversion
            print(f"  Resolved share URN (direct): {direct_share_urn}")
            return direct_share_urn
    except Exception as e:
        print(f"  Warning: /rest/posts query failed ({e}) — using direct URN")
        return direct_share_urn


def _truncate_to_sentence(text, max_chars=280):
    """Truncate to the last complete sentence within max_chars."""
    if len(text) <= max_chars:
        return text
    chunk = text[:max_chars]
    m = re.search(r'^(.*[.!?])\s', chunk + ' ', re.DOTALL)
    return m.group(1).rstrip() if m else chunk.rstrip('., ')


def _personal_cta(title, source_url):
    """Return a CTA keyed to the article topic."""
    t = title.lower()
    if "digital nomad" in t or "nomad economy" in t or "ai labor" in t:
        return (
            "Worth the read if you've ever wondered who's actually doing "
            "the work that makes AI look autonomous."
            f"\n\nRead: {source_url}"
        )
    if "music" in t or "compos" in t:
        return (
            "Worth the 9 minutes if you work in music, media, or AI "
            "-- or if a song has ever moved you in a way you couldn't explain."
            f"\n\nRead: {source_url}"
        )
    if "global south" in t or "gap" in t:
        return f"Worth the read if you care about who actually benefits when the AI economy arrives.\n\nRead: {source_url}"
    if "hallucin" in t:
        return f"Worth understanding before the next time someone tells you 'the AI confirmed it.'\n\nRead: {source_url}"
    if "agent" in t or "rogue" in t:
        return f"Worth understanding if you're building with or deploying AI agents.\n\nRead: {source_url}"
    return f"Worth the read.\n\nRead: {source_url}"


def _extract_stat(html_content: str, max_chars: int = 200) -> str | None:
    """
    Pull a key statistic or data point from the article body.
    Looks for sentences containing a number + % or $ or explicit stat phrasing.
    Returns the first clean sentence found, or None.
    """
    clean = re.sub(r'<(script|style|nav|header|footer|aside)[^>]*>.*?</\1>', '',
                   html_content, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', clean)
    text = re.sub(r'&#?\w+;', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    # Sentence tokenise
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z“‘"\d])', text)
    stat_re = re.compile(
        r'(\$[\d,.]+|\d[\d,.]*\s*%|[\d,.]+\s*(billion|million|trillion|thousand)|'
        r'\d+\s+(in|out of)\s+\d+)',
        re.IGNORECASE
    )
    for s in sentences:
        s = s.strip()
        if stat_re.search(s) and 40 < len(s) <= max_chars:
            return s
    return None


def _extract_pullquote(html_content: str, max_chars: int = 280) -> str | None:
    """
    Pull text from a <blockquote> or element with class containing 'pullquote'/'quote'.
    Falls back to None if none found.
    """
    m = re.search(
        r'<(?:blockquote|[^>]+class=["\'][^"\']*(?:pullquote|pull-quote|quote)[^"\']*["\'])[^>]*>'
        r'(.*?)</(?:blockquote|[a-z]+)>',
        html_content, re.DOTALL | re.IGNORECASE
    )
    if not m:
        return None
    text = re.sub(r'<[^>]+>', '', m.group(1))
    text = re.sub(r'\s+', ' ', text).strip()
    if 40 < len(text) <= max_chars:
        return text
    return None


# Five distinct hook patterns for the personal reshare.
# Selected deterministically by hashing the article filename so the same
# article always gets the same pattern (crash-retry safe) but different
# articles across consecutive days get different structures.
_HOOK_PATTERNS = [
    # Pattern 0 — Lead sentence drop (direct from article)
    lambda hook, stat, quote, title, desc, url, tldr: (
        f"{hook or desc}\n\n{tldr}\n\n{url}"
    ),
    # Pattern 1 — Stat first, then context
    lambda hook, stat, quote, title, desc, url, tldr: (
        f"{stat or hook or desc}\n\n"
        f"That's one of the data points from a new piece I published on {title}.\n\n"
        f"{tldr}\n\n{url}"
    ),
    # Pattern 2 — Question framing
    lambda hook, stat, quote, title, desc, url, tldr: (
        f"What happens when {title.lower()}?\n\n"
        f"{hook or desc}\n\n"
        f"{tldr}\n\n{url}"
    ),
    # Pattern 3 — Pullquote / blockquote drop
    lambda hook, stat, quote, title, desc, url, tldr: (
        f'"{quote or hook or desc}"\n\n'
        f"— from my latest: {title}\n\n"
        f"{tldr}\n\n{url}"
    ),
    # Pattern 4 — Stakes opener
    lambda hook, stat, quote, title, desc, url, tldr: (
        f"This matters more than most people realize.\n\n"
        f"{hook or desc}\n\n"
        f"{tldr}\n\n{url}"
    ),
]


def _article_tldr(title: str, description: str, hook: str | None) -> str:
    """Short TL;DR line — persona-neutral, derived from description or fallback."""
    # Use first sentence of description if distinct from hook
    if description and len(description) > 60:
        first = re.split(r'(?<=[.!?])\s+', description.strip())[0]
        if first and first != hook:
            return f"TL;DR — {first}"
    return f"TL;DR — {title}. Full argument at the link."


def build_personal_commentary(title, description, source_url, persona="joselito", html_content=None):
    """
    Build a personal reshare commentary with an article-specific hook.

    Extracts a real hook (lead sentence, stat, or pullquote) from the article HTML
    and rotates across 5 structural patterns keyed by article filename hash —
    deterministic per article, varied across consecutive posts.

    Persona-aware: Dawn = critical/cultural; Kenji = technical; Joselito = rotating patterns.
    """
    tags = generate_hashtags(html_content, title, description) if html_content else "#AIMA #AIForGood"

    if persona == "dawn":
        hook = extract_hook(html_content) if html_content else None
        stat = _extract_stat(html_content) if html_content else None
        intro = (
            f"I've been sitting with this one.\n\n"
            f"{stat or hook or _truncate_to_sentence(description, 280)}"
        )
        tldr = (
            "TL;DR — The institutions calling this 'ethical AI' are the ones "
            "designing the systems that aren't."
        )
        cta = f"Read the full take: {source_url}"
        commentary = f"{intro}\n\n{tldr}\n\n{cta}\n\n{tags}"

    elif persona == "kenji":
        hook = extract_hook(html_content) if html_content else None
        stat = _extract_stat(html_content) if html_content else None
        intro = (
            f"This is the story nobody's telling about what's actually possible.\n\n"
            f"{stat or hook or _truncate_to_sentence(description, 280)}"
        )
        tldr = (
            "TL;DR — The technology is further along than the headlines admit, "
            "and closer to real people's lives than the hype suggests."
        )
        cta = f"Full breakdown: {source_url}"
        commentary = f"{intro}\n\n{tldr}\n\n{cta}\n\n{tags}"

    else:
        # Joselito — rotate across 5 patterns based on article filename hash
        hook   = extract_hook(html_content, max_sentences=2) if html_content else None
        stat   = _extract_stat(html_content) if html_content else None
        quote  = _extract_pullquote(html_content) if html_content else None
        desc_s = _truncate_to_sentence(description, 280)
        tldr   = _article_tldr(title, description, hook)

        # Derive pattern index from article slug in source_url (stable across retries)
        slug_seed = re.sub(r'[^a-z0-9]', '', source_url.lower())
        pattern_idx = hash(slug_seed) % len(_HOOK_PATTERNS)
        pattern_fn  = _HOOK_PATTERNS[pattern_idx]

        body = pattern_fn(
            hook  or desc_s,
            stat  or desc_s,
            quote or hook or desc_s,
            title, desc_s, source_url, tldr,
        )
        commentary = f"{body}\n\n{tags}"

    # Preserve newlines and tabs; strip other non-printable control chars
    commentary = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', commentary)
    return commentary[:3000]


def _personal_hook(title):
    """Return an opening hook line keyed to the article topic."""
    t = title.lower()
    if "music" in t or "compos" in t:
        return (
            "Last year I heard a song that made me feel something. "
            "I found out afterward no human wrote it.\n"
            "That moment sent me to my desk to write this piece."
        )
    if "hallucin" in t:
        return "Every time I hear 'AI said so,' I think about this."
    if "global south" in t or "gap" in t:
        return "The people building the future are not the ones most affected by it."
    if "digital nomad" in t or "nomad economy" in t or "ai labor" in t:
        return (
            "There are two kinds of people working in the global AI economy right now.\n\n"
            "One earns $124,000 a year from a beach in Bali. "
            "The other earns $1.50 an hour to make sure the AI doesn't say anything horrifying.\n\n"
            "Both of them are part of the same machine."
        )
    if "arbitrage" in t or "labor" in t or "workforce" in t:
        return "The economics of who does the invisible work — and who gets paid for the visible result — haven't changed. Only the job titles have."
    if "agent" in t or "rogue" in t:
        return "I've spent months watching AI systems make decisions nobody authorized."
    if "creative" in t or "production" in t:
        return "I built a music video for $5,000 that used to cost $200,000. Here's what that actually means."
    return "I wrote this because I couldn't stop thinking about it."


def _personal_tldr(title):
    """Return a TLDR line keyed to the article topic."""
    t = title.lower()
    if "music" in t or "compos" in t:
        return (
            "TL;DR — AI can learn the shape of longing. "
            "It cannot know what longing cost. "
            "That gap — between statistical technique and lived intention — "
            "is the only thing separating a generative model from a composer. "
            "And it turns out to be the only thing that ever mattered about music."
        )
    if "hallucin" in t:
        return (
            "TL;DR — AI doesn't lie. It confabulates with total confidence. "
            "The difference is more dangerous than it sounds."
        )
    if "global south" in t:
        return (
            "TL;DR — The AI revolution is being built on the assumption that "
            "everyone starts from the same place. They don't."
        )
    if "digital nomad" in t or "nomad economy" in t or "ai labor" in t:
        return (
            "TL;DR — The same technology that was supposed to eliminate global inequality "
            "has invented more sophisticated names for the same old arrangement: "
            "the poor do the invisible work, and the rich own the visible product. "
            "43 million nomads, $940B in economic value, and a Nairobi data labeler earning $1.50/hr — "
            "all part of the same economy."
        )
    if "arbitrage" in t or "labor" in t:
        return "TL;DR — Someone is always doing the work that makes the AI look autonomous. Follow the money to find out who."
    return "TL;DR — The data, the argument, and the implications are in the link."


def reshare_to_personal(share_urn, title, commentary=None):
    """
    Reshare a company page post to Joselito's personal profile.
    Requires w_member_social scope. Returns the personal reshare URN.
    Pass commentary= to override the default generic text.
    """
    if not MEMBER_ID:
        print("  WARNING: LINKEDIN_MEMBER_ID not set -- skipping personal reshare.")
        return None

    text = commentary if commentary else f"New from the AIMA team — {title}"
    body = {
        "author":         f"urn:li:person:{MEMBER_ID}",
        "commentary":     text[:3000],
        "lifecycleState": "PUBLISHED",
        "visibility":     "PUBLIC",
        "distribution": {
            "feedDistribution":               "MAIN_FEED",
            "thirdPartyDistributionChannels": []
        },
        "reshareContext": {
            "parent": share_urn
        }
    }

    payload = json.dumps(body).encode("utf-8")
    url     = "https://api.linkedin.com/rest/posts"
    req     = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Authorization",             f"Bearer {ACCESS_TOKEN}")
    req.add_header("Content-Type",              "application/json")
    req.add_header("LinkedIn-Version",          "202506")
    req.add_header("X-Restli-Protocol-Version", "2.0.0")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            reshare_id = resp.headers.get("x-restli-id", "")
            if not reshare_id:
                result     = json.loads(resp.read() or b"{}")
                reshare_id = result.get("id", "")
            print(f"  Reshared to personal profile: {reshare_id}")
            return reshare_id
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"  Personal reshare failed {e.code}: {error_body[:300]}")
        return None
    except Exception as e:
        print(f"  Personal reshare error: {e}")
        return None
