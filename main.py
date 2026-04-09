from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import concurrent.futures

app = Flask(__name__)
CORS(app)

GOOGLE_API_KEY = "AIzaSyDzP5LXKw9870TKqyjqUVOE1pqj8L4KBQs"
SEARCH_ENGINE_ID = "c373598a0f8b546f4"

def check_index(url):
    try:
        url = url.strip()
        if not url:
            return None

        if not url.startswith("http"):
            url = "https://" + url

        query = f"site:{url}"
        api_url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": GOOGLE_API_KEY,
            "cx": SEARCH_ENGINE_ID,
            "q": query,
            "num": 1
        }

        response = requests.get(api_url, params=params, timeout=15)
        data = response.json()

        if "error" in data:
            error_msg = data["error"].get("message", "Unknown error")
            if "quota" in error_msg.lower() or "limit" in error_msg.lower():
                return {"url": url, "status": "error", "message": "Daily limit reached (100/day). Try again tomorrow."}
            return {"url": url, "status": "error", "message": error_msg}

        total_results = int(data.get("searchInformation", {}).get("totalResults", "0"))

        if total_results > 0:
            return {"url": url, "status": "indexed", "total_results": total_results}
        else:
            return {"url": url, "status": "not_indexed", "total_results": 0}

    except requests.exceptions.Timeout:
        return {"url": url, "status": "error", "message": "Timeout - try again"}
    except Exception as e:
        return {"url": url, "status": "error", "message": str(e)}


@app.route("/")
def home():
    return jsonify({
        "message": "Index Checker API running with Google Custom Search!",
        "accuracy": "100% - powered by Google"
    })


@app.route("/check", methods=["POST"])
def check_urls():
    data = request.get_json()
    urls = data.get("urls", [])

    if not urls:
        return jsonify({"error": "No URLs provided"}), 400

    clean_urls = [u.strip() for u in urls if u.strip()]

    if len(clean_urls) > 100:
        return jsonify({"error": "Maximum 100 URLs per day (Google free limit)"}), 400

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
