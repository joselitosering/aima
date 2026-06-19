"""
linkedin_poster.py — Posts an AIMA article to the AIMA LinkedIn company page.

Posts as urn:li:organization:{ORG_ID} so all three writers (Joselito, Dawn,
Kenji) share a single branded channel. Persona attribution is written into
the post commentary. Cover image is uploaded directly via LinkedIn Assets API
to guarantee the visual is always shown.

Requires scopes: w_organization_social
"""

import os, json, re, urllib.request, urllib.error, mimetypes
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
    "kenji":    "Kenji · Contributing Writer, AIMA",
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
    title_m = re.search(r"<title[^>]*>(.*?)</title>", html_content, re.IGNORECASE | re.DOTALL)
    title   = title_m.group(1).strip() if title_m else \
              filename.replace(".html","").replace("-"," ").title()

    desc_m = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']',
                       html_content, re.IGNORECASE)
    if not desc_m:
        desc_m = re.search(r'<meta\s+content=["\'](.*?)["\']\s+name=["\']description["\']',
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
        body = re.sub(r"<[^>]+>", " ", html_content)
        body = re.sub(r"\s+", " ", body).strip()
        description = (body[:300] + "...") if len(body) > 300 else body

    if not source_url:
        source_url = "https://github.com/joselitosering/aima"

    return title, description[:700], source_url


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

    # -- Upload cover image --------------------------------------------------
    image_url = extract_og_image(article["content"])
    asset_urn = None

    if image_url:
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

    if persona == "dawn":
        commentary = (
            f"📖 {title}\n\n"
            f"{description}\n\n"
            f"Who benefits from this — and who never got asked?\n\n"
            f"Read the full piece: {source_url}\n\n"
            f"{hashtags}\n\n"
            f"By {byline}"
        )
    elif persona == "kenji":
        commentary = (
            f"🚀 {title}\n\n"
            f"{description}\n\n"
            f"The frontier is closer than the headlines suggest.\n\n"
            f"Read the full piece: {source_url}\n\n"
            f"{hashtags}\n\n"
            f"By {byline}"
        )
    else:
        commentary = (
            f"📖 {title}\n\n"
            f"{description}\n\n"
            f"Read the full article: {source_url}\n\n"
            f"{hashtags}\n\n"
            f"By {byline}"
        )

    # -- Build post payload --------------------------------------------------
    author_urn = f"urn:li:organization:{ORG_ID}"

    if asset_urn:
        media_obj            = {"status": "READY", "media": asset_urn, "title": {"text": title[:200]}}
        share_media_category = "IMAGE"
    else:
        media_obj            = {"status": "READY", "originalUrl": source_url,
                                "title": {"text": title}, "description": {"text": description}}
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
        with urllib.request.urlopen(req) as resp:
            result  = json.loads(resp.read())
            post_id = result.get("id", "unknown")
            print(f"  Posted to AIMA page: '{title}' | ID: {post_id} | Mode: {share_media_category} | By: {byline}")
            return post_id
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"  LinkedIn API error {e.code}: {error_body}")
        raise
