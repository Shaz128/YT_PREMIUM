from flask import Flask, render_template, request, jsonify
import yt_dlp
import os

app = Flask(__name__)

# Download folder setup
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

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

    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(DOWNLOAD_FOLDER, "%(title)s.%(ext)s"),
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "64",
                }
            ],
            "noplaylist": True,
            "cookiefile": "cookies.txt",
            "quiet": False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            file_name = f"{info['title']}.mp3"

        return jsonify({"success": True, "file": file_name})

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