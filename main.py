from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import concurrent.futures

app = Flask(__name__)
CORS(app)

SERP_API_KEY = "768e4a39e00bed46e1227db7045e8ca4331fd6dd011b37220c28cb130bb2f021"

def check_index(url):
    try:
        url = url.strip()
        if not url:
            return None

        if not url.startswith("http"):
            url = "https://" + url

        params = {
            "engine": "google",
            "q": f"site:{url}",
            "api_key": SERP_API_KEY,
            "num": 1,
            "hl": "en",
            "gl": "us"
        }

        response = requests.get("https://serpapi.com/search", params=params, timeout=30)
        data = response.json()

        # Check for API errors
        if "error" in data:
            error_msg = data["error"]
            if "rate" in error_msg.lower() or "limit" in error_msg.lower():
                return {"url": url, "status": "error", "message": "Daily limit reached (250/day)"}
            return {"url": url, "status": "error", "message": error_msg}

        # Check organic results
        organic_results = data.get("organic_results", [])
        search_info = data.get("search_information", {})
        total_results = search_info.get("total_results", 0)

        if organic_results or total_results > 0:
            return {
                "url": url,
                "status": "indexed",
                "total_results": total_results
            }
        else:
            return {
                "url": url,
                "status": "not_indexed",
                "total_results": 0
            }

    except requests.exceptions.Timeout:
        return {"url": url, "status": "error", "message": "Timeout - try again"}
    except Exception as e:
        return {"url": url, "status": "error", "message": str(e)}


@app.route("/")
def home():
    return jsonify({
        "message": "Index Checker API running with SerpAPI!",
        "accuracy": "100% - powered by Google via SerpAPI",
        "daily_limit": "250 searches/day"
    })


@app.route("/check", methods=["POST"])
def check_urls():
    data = request.get_json()
    urls = data.get("urls", [])

    if not urls:
        return jsonify({"error": "No URLs provided"}), 400

    clean_urls = [u.strip() for u in urls if u.strip()]

    if len(clean_urls) > 250:
        return jsonify({"error": "Maximum 250 URLs per day (SerpAPI free limit)"}), 400

    # Run 5 checks at the same time for speed
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(check_index, clean_urls))
        results = [r for r in results if r is not None]

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
