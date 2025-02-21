from flask import Flask, render_template, request, jsonify
import yt_dlp
import os
import requests

app = Flask(__name__)

# 🔹 Your YouTube Data API Key
YOUTUBE_API_KEY = "AIzaSyD1eTG59YLjaq9VYD8Vl2so86eh4-eLKIU"

# 🔹 Folder to Save Downloads
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def get_video_info(video_url):
    """Extracts video ID and fetches title using YouTube Data API."""
    video_id = video_url.split("v=")[-1].split("&")[0]
    api_url = f"https://www.googleapis.com/youtube/v3/videos?id={video_id}&key={YOUTUBE_API_KEY}&part=snippet"
    response = requests.get(api_url)
    if response.status_code == 200:
        data = response.json()
        if "items" in data and len(data["items"]) > 0:
            title = data["items"][0]["snippet"]["title"]
            return video_id, title
    return None, None

@app.route("/")
def home():
    """Render the main page."""
    return render_template("index.html")

@app.route("/download", methods=["POST"])
def download_mp3():
    """Download a YouTube video as MP3."""
    data = request.json
    youtube_url = data.get("url")

    if not youtube_url:
        return jsonify({"error": "No URL provided"}), 400

    video_id, title = get_video_info(youtube_url)
    if not title:
        return jsonify({"error": "Could not retrieve video details. Check API Key or video availability."}), 400

    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(DOWNLOAD_FOLDER, f"{title}.mp3"),
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "noplaylist": True,
            "quiet": False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])

        return jsonify({"success": True, "file": f"{title}.mp3"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/list_downloads", methods=["GET"])
def list_downloads():
    """Return a list of all downloaded MP3 files."""
    try:
        files = [f for f in os.listdir(DOWNLOAD_FOLDER) if f.endswith(".mp3")]
        return jsonify({"files": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
