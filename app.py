from flask import Flask, render_template, request, jsonify, send_file
import http.client
import json
import os
import yt_dlp
import shutil
import re

app = Flask(__name__)
DOWNLOAD_FOLDER = "downloads"

# Remove all files and subdirectories in the DOWNLOAD_FOLDER
try:
    shutil.rmtree(DOWNLOAD_FOLDER)
except FileNotFoundError:
    pass

# Recreate the DOWNLOAD_FOLDER
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

API_HOST = "youtube-v31.p.rapidapi.com"
API_KEY = "56dfead9d0msh16dd2994a8f600dp12c061jsn103a13978d3f"  # 🔴 Replace with your actual API key!

# YouTube URL validation regex
YOUTUBE_REGEX = re.compile(
    r"^(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})"
)

def extract_video_id(youtube_url):
    match = YOUTUBE_REGEX.match(youtube_url)
    return match.group(1) if match else None

def get_related_videos(video_id, max_results=5):
    """Fetches related videos from YouTube API"""
    try:
        conn = http.client.HTTPSConnection(API_HOST)
        headers = {"x-rapidapi-key": API_KEY, "x-rapidapi-host": API_HOST}
        conn.request("GET", f"/search?relatedToVideoId={video_id}&part=id,snippet&type=video&maxResults={max_results}", headers=headers)
        res = conn.getresponse()

        if res.status != 200:
            return []  # API error

        data = json.loads(res.read().decode("utf-8"))
        return [
            {"title": item["snippet"]["title"], "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}"}
            for item in data.get("items", [])
        ]
    except Exception as e:
        print(f"Error fetching related videos: {e}")
        return []

def download_mp3(youtube_url):
    """Downloads a YouTube video as MP3 with the correct title"""
    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "64"}],
            "noplaylist": True,
            "quiet": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            video_title = re.sub(r"[^a-zA-Z0-9 ]", "", info["title"])  # Remove special characters
            filename = f"{video_title}.mp3"
            ydl_opts["outtmpl"] = os.path.join(DOWNLOAD_FOLDER, filename)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtube_url])
            return filename
    except Exception as e:
        print(f"Error downloading {youtube_url}: {e}")
        return None

@app.route('/')
def index():
    try:
        shutil.rmtree(DOWNLOAD_FOLDER)
    except FileNotFoundError:
        pass
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
    return render_template('index.html')

@app.route('/get_videos', methods=['POST'])
def get_videos():
    youtube_url = request.form.get('video_id')
    video_id = extract_video_id(youtube_url)

    if not video_id:
        return jsonify({"error": "Invalid YouTube URL"}), 400

    videos = get_related_videos(video_id)
    return jsonify(videos)

@app.route('/stream_audio')
def stream_audio():
    youtube_url = request.args.get('url')

    if not youtube_url or not extract_video_id(youtube_url):
        return "Invalid YouTube URL", 400

    filename = download_mp3(youtube_url)
    if not filename:
        return "Failed to download", 500

    filepath = os.path.join(DOWNLOAD_FOLDER, filename)
    return send_file(filepath, as_attachment=False, mimetype="audio/mpeg")

@app.route('/download', methods=['POST'])
def download():
    urls = request.json.get('urls', [])
    if not urls:
        return jsonify({"error": "No videos selected"}), 400

    downloaded_files = []
    for url in urls:
        filename = download_mp3(url)
        if filename:
            downloaded_files.append(filename)

    if not downloaded_files:
        return jsonify({"error": "No files downloaded"}), 500

    zip_path = "downloads.zip"
    shutil.make_archive("downloads", 'zip', DOWNLOAD_FOLDER)
    return send_file(zip_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
