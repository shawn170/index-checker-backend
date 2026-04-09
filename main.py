from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import concurrent.futures
import urllib.parse

app = Flask(__name__)
CORS(app)

SCRAPER_API_KEY = "1d68d63f34fba53568ebe148b8aa5b15"

def check_index(url):
    try:
        url = url.strip()
        if not url:
            return None

        # Add https if missing
        if not url.startswith("http"):
            url = "https://" + url

        query = f"site:{url}"
        encoded_query = urllib.parse.quote(query)
        google_url = f"https://www.google.com/search?q={encoded_query}&num=10&hl=en&gl=us"

        # Use ScraperAPI with extra options for better accuracy
        api_url = (
            f"http://api.scraperapi.com/"
            f"?api_key={SCRAPER_API_KEY}"
            f"&url={urllib.parse.quote(google_url)}"
            f"&render=false"
            f"&country_code=us"
            f"&device_type=desktop"
        )

        response = requests.get(api_url, timeout=30)
        html = response.text.lower()

        # NOT INDEXED signals — very specific phrases Google uses
        not_indexed_signals = [
            "did not match any documents",
            "no results found for",
            "your search did not match",
            "no results found",
            "0 results",
        ]

        # INDEXED signals — things that only appear when results exist
        indexed_signals = [
            "class=\"g\"",
            "data-ved",
            "<h3",
            "class=\"rc\"",
            "/url?q=",
            "class=\"yuRUbf\"",
        ]

        # Check for CAPTCHA or block
        captcha_signals = [
            "captcha",
            "unusual traffic",
            "verify you're a human",
            "i'm not a robot",
            "recaptcha",
        ]

        # If CAPTCHA detected, retry once
        if any(signal in html for signal in captcha_signals):
            return {"url": url, "status": "error", "message": "Google blocked - try again later"}

        # Check not indexed first
        if any(signal in html for signal in not_indexed_signals):
            return {"url": url, "status": "not_indexed"}

        # Check indexed signals
        indexed_count = sum(1 for signal in indexed_signals if signal in html)
        if indexed_count >= 2:
            return {"url": url, "status": "indexed"}

        # If page loaded but unclear
        if len(html) > 2000:
            # Extra check — see if the URL's domain appears in results
            domain = url.split("/")[2] if "/" in url else url
            domain = domain.replace("https://", "").replace("http://", "").replace("www.", "")
            if domain in html:
                return {"url": url, "status": "indexed"}
            else:
                return {"url": url, "status": "not_indexed"}

        return {"url": url, "status": "error", "message": "Could not determine - page too short"}

    except requests.exceptions.Timeout:
        return {"url": url, "status": "error", "message": "Timeout - try again"}
    except Exception as e:
        return {"url": url, "status": "error", "message": str(e)}


@app.route("/")
def home():
    return jsonify({"message": "Index Checker API is running!"})


@app.route("/check", methods=["POST"])
def check_urls():
    data = request.get_json()
    urls = data.get("urls", [])

    if not urls:
        return jsonify({"error": "No URLs provided"}), 400

    clean_urls = [u.strip() for u in urls if u.strip()]

    if len(clean_urls) > 500:
        return jsonify({"error": "Maximum 500 URLs per request"}), 400

    results = []
    batch_size = 5

    for i in range(0, len(clean_urls), batch_size):
        batch = clean_urls[i:i + batch_size]
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            batch_results = list(executor.map(check_index, batch))
            results.extend([r for r in batch_results if r is not None])

    indexed = sum(1 for r in results if r["status"] == "indexed")
    not_indexed = sum(1 for r in results if r["status"] == "not_indexed")
    errors = sum(1 for r in results if r["status"] == "error")

    return jsonify({
        "results": results,
        "total": len(results),
        "indexed": indexed,
        "not_indexed": not_indexed,
        "errors": errors
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
