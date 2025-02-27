from flask import Flask, render_template, request, jsonify, send_file
import http.client
import json
import os
import shutil
import yt_dlp
import re

app = Flask(__name__)
DOWNLOAD_FOLDER = "downloads"

API_HOST = "youtube-v31.p.rapidapi.com"
API_KEY = "56dfead9d0msh16dd2994a8f600dp12c061jsn103a13978d3f"  # 🔴 Replace with your actual API key!

# Ensure download folder exists
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Allowed YouTube URL patterns
YOUTUBE_REGEX = re.compile(
    r"^(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})"
)

# Function to extract video ID from a valid URL
def extract_video_id(youtube_url):
    match = YOUTUBE_REGEX.match(youtube_url)
    return match.group(1) if match else None

# Function to get related video links (limit the returned list to 5)
def get_related_videos(video_id, max_results=5):
    try:
        conn = http.client.HTTPSConnection(API_HOST)
        headers = {
            "x-rapidapi-key": API_KEY,
            "x-rapidapi-host": API_HOST,
        }
        conn.request("GET", f"/search?relatedToVideoId={video_id}&part=id,snippet&type=video&maxResults={max_results}", headers=headers)
        res = conn.getresponse()

        if res.status != 200:
            return []  # Return empty list if API call fails

        data = json.loads(res.read().decode("utf-8"))
        video_links = [
            {"title": item["snippet"]["title"], "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}"}
            for item in data.get("items", [])
        ]
        return video_links[:max_results]  # ensure only max_results are returned
    except Exception as e:
        print(f"Error fetching related videos: {e}")
        return []

# Function to download YouTube videos as MP3
def download_mp3(youtube_url):
    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(DOWNLOAD_FOLDER, "%(title)s.%(ext)s"),
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "64"}],
            "noplaylist": True,
            "quiet": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            return f"{info['title']}.mp3"
    except Exception as e:
        print(f"Error downloading {youtube_url}: {e}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_videos', methods=['POST'])
def get_videos():
    youtube_url = request.form.get('video_id')
    video_id = extract_video_id(youtube_url)

    if not video_id:
        return jsonify({"error": "Invalid YouTube URL. Please enter a correct link."}), 400

    videos = get_related_videos(video_id)
    return jsonify(videos)

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
