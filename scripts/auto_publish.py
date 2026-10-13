import os, json, urllib.request, urllib.error, html, re, time
from urllib.parse import quote
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "articles"
INDEX = ROOT / "articles.json"
ARTICLES.mkdir(exist_ok=True)

key = os.environ.get("GEMINI_API_KEY")
if not key:
    raise SystemExit("ERROR: GEMINI_API_KEY secret missing")

topics = [
    ("earning", "Practical online earning skills for beginners"),
    ("ai", "Useful AI tools and technology explained for beginners"),
    ("mobile", "Useful Android mobile tips and privacy"),
    ("video", "How beginners can create AI videos"),
    ("cricket", "Cricket rules, skills and beginner guides"),
    ("football", "Football rules, skills and beginner guides"),
    ("news", "How to check news and avoid online misinformation")
]

today = datetime.now(timezone.utc).date()
stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

def generate(language, category, topic):
    if language == "bn":
        instruction = "Write natural, simple Bengali for readers in India."
        langname = "Bengali"
    else:
        instruction = "Write clear, simple English for beginners."
        langname = "English"

    prompt = f"""
You are a careful, helpful website editor writing an original article.
Language: {langname}
Topic: {topic}
Category: {category}
{instruction}

Write a genuinely useful, topic-specific article for beginners.
Do not translate the other language version.
Target approximately 650-900 words, with 8-10 substantial paragraphs.
Every paragraph must provide different, relevant information.
Never pad the article with repeated generic advice.

Include these elements where relevant:
1. A clear introduction explaining the exact topic and who it helps.
2. Important concepts explained in simple language.
3. Specific steps readers can actually follow.
4. A realistic example or practical scenario.
5. Common mistakes and how to avoid them.
6. Benefits, limitations, costs or requirements where relevant.
7. Safety, privacy or scam warnings where appropriate.
8. A useful conclusion with a practical next step.

CATEGORY-SPECIFIC RULES:
- Earning: explain real methods, skills, beginner steps, likely costs
  and risks. Never promise income or invent earnings figures.
- Mobile/technology: give concrete settings, steps or examples.
  Explain that menu names can differ by device and Android version.
- AI: explain what a tool can do, its limitations and how to use it
  responsibly. Never invent features or claim a tool is free without
  reliable grounds.
- Cricket/football/sports: explain rules, tactics or skills using
  evergreen information. Do not invent live scores or results.
- News/current affairs: never invent events, dates, quotes or statistics.
  If reliable current information is unavailable, do not pretend it is
  verified; prefer a clearly useful evergreen topic instead.

Use precise examples related to the topic, not vague phrases such as
"learn the basics" or "practise regularly" unless you explain exactly
what the reader should learn or practise.
Do not fabricate facts, sources, prices, statistics or guarantees.
Avoid keyword stuffing and misleading titles.
Create a natural, specific title that accurately describes the article.
Return ONLY valid JSON in this exact format:
{{"title":"Specific article title","paragraphs":["paragraph 1","paragraph 2","paragraph 3","paragraph 4","paragraph 5","paragraph 6","paragraph 7","paragraph 8"]}}
"""

    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 5000
        }
    }).encode()

    models = [
        "gemini-flash-latest",
        "gemini-3-flash-preview",
        "gemini-3.8-flash"
    ]
    errors = []

    for model in models:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            + model + ":generateContent"
        )
        for attempt in range(3):
            req = urllib.request.Request(
                url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": key
                },
                method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=120) as response:
                    data = json.loads(response.read().decode())

                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
                result = json.loads(text)

                paragraphs = result.get("paragraphs")
                if not result.get("title") or not isinstance(paragraphs, list):
                    raise ValueError("Generated article is incomplete")

                paragraphs = [
                    str(x).strip() for x in paragraphs
                    if isinstance(x, str) and x.strip()
                ]
                word_count = len(" ".join(paragraphs).split())

                if len(paragraphs) < 6 or word_count < 450:
                    raise ValueError(
                        f"Article too short: {word_count} words, "
                        f"{len(paragraphs)} paragraphs"
                    )

                result["paragraphs"] = paragraphs
                print("AI model succeeded:", model,
                      "| words:", word_count,
                      "| paragraphs:", len(paragraphs))
                return result

            except urllib.error.HTTPError as e:
                errors.append(f"{model}: HTTP {e.code}")
                print("AI model error:", model, "HTTP", e.code)

                if e.code in (429, 500, 502, 503, 504):
                    if e.code != 429 and attempt < 2:
                        time.sleep(2 ** (attempt + 1))
                        continue
                break

            except (urllib.error.URLError, TimeoutError) as e:
                errors.append(f"{model}: {e}")
                print("Connection error:", model)
                if attempt < 2:
                    time.sleep(2 ** (attempt + 1))
                    continue
                break

            except (KeyError, IndexError, ValueError) as e:
                errors.append(f"{model}: invalid response ({e})")
                print("Invalid AI response:", model)
                if attempt < 2:
                    time.sleep(2 ** (attempt + 1))
                    continue
                break

    print("Gemini unavailable; skipping this article:", language, category)
    return None


def generate_topic_image(category, topic, stamp):
    image_dir = ARTICLES / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    image_file = image_dir / f"{category}-{stamp}.jpg"

    fallbacks = {
        "earning": "https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=1200&q=80",
        "ai": "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&w=1200&q=80",
        "mobile": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=1200&q=80",
        "video": "https://images.unsplash.com/photo-1492619375914-88005aa9e8fb?auto=format&fit=crop&w=1200&q=80",
        "cricket": "https://images.unsplash.com/photo-1531415074968-036ba1b575da?auto=format&fit=crop&w=1200&q=80",
        "football": "https://images.unsplash.com/photo-1574629810360-7efbbe195018?auto=format&fit=crop&w=1200&q=80",
        "news": "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=1200&q=80",
    }

    api_key = os.environ.get("POLLINATIONS_API_KEY")
    if api_key:
        seed = sum((category + topic + stamp).encode("utf-8"))
        prompt = (
            f"Create a distinct editorial illustration showing {topic}. "
            f"Category: {category}. Make the main subject clearly recognizable "
            "and specific to this topic. Landscape composition, blog header, "
            "no text, no letters, no watermark."
        )
        url = (
            "https://gen.pollinations.ai/image/"
            + quote(prompt, safe="")
            + f"?model=flux&width=768&height=512&seed={seed}"
        )
        try:
            req = urllib.request.Request(
                url, headers={"Authorization": "Bearer " + api_key}
            )
            with urllib.request.urlopen(req, timeout=120) as response:
                content_type = response.headers.get("Content-Type", "")
                data = response.read()
            if content_type.startswith("image/") and data:
                image_file.write_bytes(data)
                print("Generated image:", image_file.name)
                return "images/" + image_file.name
            print("Image API returned non-image data; trying fallback")
        except Exception as e:
            print("Image generation failed; trying fallback:", e)

    fallback_url = fallbacks.get(category, fallbacks["earning"])
    try:
        req = urllib.request.Request(
            fallback_url, headers={"User-Agent": "AI-Path-Bangla/1.0"}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            content_type = response.headers.get("Content-Type", "")
            data = response.read()
        if content_type.startswith("image/") and data:
            image_file.write_bytes(data)
            print("Downloaded category fallback:", image_file.name)
            return "images/" + image_file.name
    except Exception as e:
        print("Fallback download failed:", e)

    return fallback_url

try:
    existing = json.loads(INDEX.read_text(encoding="utf-8"))
except (FileNotFoundError, json.JSONDecodeError):
    existing = []

# Daily rotation: one category and one language per run.
day_number = today.toordinal()
category, topic = topics[day_number % len(topics)]
language = "bn" if day_number % 2 == 0 else "en"
print("Today's article:", language, category, topic)

article = generate(language, category, topic)

if article:
    normalized_title = re.sub(
        r"[^\w]", "", str(article.get("title", "")).casefold(),
        flags=re.UNICODE
    )
    existing_titles = {
        re.sub(r"[^\w]", "", str(item.get("title", "")).casefold(),
               flags=re.UNICODE)
        for item in existing
    }

    if not normalized_title or normalized_title in existing_titles:
        print("Skipping duplicate/empty title:", article.get("title", ""))
    else:
        filename = f"article-{language}-{stamp}.html"
        title = html.escape(str(article["title"]))
        paragraphs = "\n".join(
            "<p>" + html.escape(str(p)) + "</p>"
            for p in article["paragraphs"]
        )

        image_path = generate_topic_image(category, topic, stamp)
        image_url = "../articles/" + image_path if image_path.startswith("images/") else image_path
        image_html = (
            '<img src="' + html.escape(image_url, quote=True) +
            '" alt="' + html.escape(str(article["title"]), quote=True) +
            '" style="width:100%;height:auto;border-radius:12px;margin:16px 0">'
        )

        langname = "bn" if language == "bn" else "en"
        page = f"""<!DOCTYPE html>
<html lang="{langname}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} | AI Path Bangla</title>
<meta name="description" content="{title}">
<style>
body{{font-family:Arial,sans-serif;line-height:1.8;max-width:800px;margin:24px auto;padding:16px;color:#20283a}}
a{{color:#087d61}}article{{background:#fff;padding:18px}}
</style>
</head>
<body><a href="../index.html">Home / হোম</a>
<article><h1>{title}</h1>
<small>Category: {html.escape(category)} | Language: {language}</small>
{image_html}
{paragraphs}
</article></body></html>"""
        (ARTICLES / filename).write_text(page, encoding="utf-8")
        existing.insert(0, {
            "title": str(article["title"]),
            "file": filename,
            "lang": language,
            "category": category,
            "date": str(today)
        })
        print("Created:", filename)

    INDEX.write_text(
        json.dumps(existing[:200], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )
    print("Article list updated.")
else:
    print("No article created; existing article list left unchanged.")
