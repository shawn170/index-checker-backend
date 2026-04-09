from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import concurrent.futures
import time

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
        google_url = f"https://www.google.com/search?q={requests.utils.quote(query)}&num=1&hl=en"
        api_url = f"http://api.scraperapi.com/?api_key={SCRAPER_API_KEY}&url={requests.utils.quote(google_url)}&render=false&country_code=us"

        response = requests.get(api_url, timeout=25)
        html = response.text

        if response.status_code != 200:
            return {"url": url, "status": "error", "message": f"HTTP {response.status_code}"}

        if "did not match any documents" in html or "No results found" in html or "no results" in html.lower():
            return {"url": url, "status": "not_indexed"}
        elif len(html) > 1000 and ("google" in html.lower() or "search" in html.lower()):
            return {"url": url, "status": "indexed"}
        else:
            return {"url": url, "status": "error", "message": "Could not verify"}

    except requests.exceptions.Timeout:
        return {"url": url, "status": "error", "message": "Timeout - try again"}
    except Exception as e:
        return {"url": url, "status": "error", "message": str(e)}


@app.route("/")
def home():
    return jsonify({"message": "Index Checker API is running at max speed!"})


@app.route("/check", methods=["POST"])
def check_urls():
    data = request.get_json()
    urls = data.get("urls", [])

    if not urls:
        return jsonify({"error": "No URLs provided"}), 400

    # Clean URLs
    clean_urls = [u.strip() for u in urls if u.strip()]

    if len(clean_urls) > 500:
        return jsonify({"error": "Maximum 500 URLs per request"}), 400

    # Process in batches of 5 (max free plan allows)
    # Each batch runs fully parallel
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
