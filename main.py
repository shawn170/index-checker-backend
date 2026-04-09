from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import time
 
app = Flask(__name__)
CORS(app)
 
SCRAPER_API_KEY = "1d68d63f34fba53568ebe148b8aa5b15"
 
def check_index(url):
    try:
        query = f"site:{url}"
        google_url = f"https://www.google.com/search?q={requests.utils.quote(query)}&num=1"
 
        api_url = f"http://api.scraperapi.com/?api_key={SCRAPER_API_KEY}&url={requests.utils.quote(google_url)}"
 
        response = requests.get(api_url, timeout=30)
        html = response.text
 
        if "did not match any documents" in html or "No results found" in html:
            return {"url": url, "status": "not_indexed"}
        elif len(html) > 500 and "google" in html.lower():
            return {"url": url, "status": "indexed"}
        else:
            return {"url": url, "status": "error", "message": "Could not verify"}
 
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
        time.sleep(0.5)
 
    return jsonify({"results": results, "total": len(results)})
 
 
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
