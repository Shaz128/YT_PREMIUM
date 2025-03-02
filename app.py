from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
import http.client
import json
import os
import yt_dlp
import shutil
import re
import concurrent.futures  # For parallel downloads
import imageio_ffmpeg as ffmpeg
import subprocess

app = Flask(__name__)

# Download Folder
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

API_HOST = "youtube-v31.p.rapidapi.com"
API_KEY = "YOUR_RAPIDAPI_KEY"  # Replace with your actual API key!

YOUTUBE_REGEX = re.compile(
    r"^(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})"
)


def extract_video_id(youtube_url):
    match = YOUTUBE_REGEX.match(youtube_url)
    return match.group(1) if match else None


def get_related_videos(video_id, max_results=5):
    try:
        conn = http.client.HTTPSConnection(API_HOST)
        headers = {"x-rapidapi-key": API_KEY, "x-rapidapi-host": API_HOST}
        conn.request(
            "GET",
            f"/search?relatedToVideoId={video_id}&part=id,snippet&type=video&maxResults={max_results}",
            headers=headers,
        )
        res = conn.getresponse()

        if res.status != 200:
            return []

        data = json.loads(res.read().decode("utf-8"))
        return [
            {
                "title": item["snippet"]["title"],
                "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}",
            }
            for item in data.get("items", [])
        ]
    except Exception as e:
        print(f"Error fetching related videos: {e}")
        return []


def download_mp3(youtube_url):
    try:
        ffmpeg_path = ffmpeg.get_ffmpeg_exe()
        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "128"}
            ],
            "noplaylist": True,
            "quiet": False,
            "ffmpeg_location": ffmpeg_path,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            video_title = re.sub(r"[^a-zA-Z0-9 ]", "", info["title"])
            filename = f"{video_title}.mp3"
            ydl_opts["outtmpl"] = os.path.join(DOWNLOAD_FOLDER, filename)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtube_url])
            return filename
    except Exception as e:
        print(f"Error downloading {youtube_url}: {e}")
        return None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/player")
def player():
    return render_template("player.html")


@app.route("/list_audio")
def list_audio():
    try:
        if not os.path.exists(DOWNLOAD_FOLDER):
            return jsonify([])

        files = [f for f in os.listdir(DOWNLOAD_FOLDER) if f.endswith(".mp3")]
        return jsonify(files)
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/play_audio/<filename>")
def play_audio(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename)


@app.route("/get_videos", methods=["POST"])
def get_videos():
    youtube_url = request.form.get("video_id")
    video_id = extract_video_id(youtube_url)

    if not video_id:
        return jsonify({"error": "Invalid YouTube URL"}), 400

    videos = get_related_videos(video_id)
    return jsonify(videos)


@app.route("/download", methods=["POST"])
def download():
    if not request.is_json:
        return jsonify({"error": "Invalid request format. Expected JSON."}), 400

    urls = request.json.get("urls", [])
    if not urls:
        return jsonify({"error": "No videos selected"}), 400

    downloaded_files = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results = executor.map(download_mp3, urls)

    for filename in results:
        if filename:
            downloaded_files.append(filename)

    if not downloaded_files:
        return jsonify({"error": "No files downloaded"}), 500

    zip_path = "downloads.zip"
    shutil.make_archive("downloads", "zip", DOWNLOAD_FOLDER)
    return send_file(zip_path, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
