from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import time

app = Flask(__name__)
CORS(app)

GOOGLE_API_KEY = "AIzaSyAVG7VwIZ2Wg4tAYWt7ef_gbbz9TAdhBVo"
SEARCH_ENGINE_ID = "c373598a0f8b546f4"

def check_index(url):
    try:
        query = f"site:{url}"
        api_url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": GOOGLE_API_KEY,
            "cx": SEARCH_ENGINE_ID,
            "q": query,
            "num": 1
        }
        response = requests.get(api_url, params=params, timeout=10)
        data = response.json()

        if "error" in data:
            return {"url": url, "status": "error", "message": data["error"]["message"]}

        total_results = int(data.get("searchInformation", {}).get("totalResults", "0"))

        if total_results > 0:
            return {"url": url, "status": "indexed", "total_results": total_results}
        else:
            return {"url": url, "status": "not_indexed", "total_results": 0}

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

    if len(urls) > 100:
        return jsonify({"error": "Maximum 100 URLs per request"}), 400

    results = []
    for url in urls:
        url = url.strip()
        if not url:
            continue
        result = check_index(url)
        results.append(result)
        time.sleep(0.2)

    return jsonify({"results": results, "total": len(results)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
