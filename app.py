from flask import Flask, render_template, request, jsonify, send_file
import http.client
import json
import os
import yt_dlp
import shutil
import re
import concurrent.futures  # For parallel downloads

app = Flask(__name__)
DOWNLOAD_FOLDER = "downloads"

# Clear and recreate download folder
shutil.rmtree(DOWNLOAD_FOLDER, ignore_errors=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

API_HOST = "youtube-v31.p.rapidapi.com"
API_KEY = "56dfead9d0msh16dd2994a8f600dp12c061jsn103a13978d3f"  # Replace with your actual API key!

# YouTube URL validation regex
YOUTUBE_REGEX = re.compile(
    r"^(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})"
)


def extract_video_id(youtube_url):
    """Extracts the video ID from a YouTube URL"""
    match = YOUTUBE_REGEX.match(youtube_url)
    return match.group(1) if match else None


def get_related_videos(video_id, max_results=5):
    """Fetch related YouTube videos asynchronously"""
    try:
        conn = http.client.HTTPSConnection(API_HOST)
        headers = {"x-rapidapi-key": API_KEY, "x-rapidapi-host": API_HOST}
        conn.request(
            "GET",
            f"/search?relatedToVideoId={video_id}&part=id,snippet&type=video&maxResults={max_results}",
            headers=headers)
        res = conn.getresponse()

        if res.status != 200:
            return []  # API error

        data = json.loads(res.read().decode("utf-8"))
        return [{
            "title":
            item["snippet"]["title"],
            "url":
            f"https://www.youtube.com/watch?v={item['id']['videoId']}"
        } for item in data.get("items", [])]
    except Exception as e:
        print(f"Error fetching related videos: {e}")
        return []


def download_mp3(youtube_url):
    """Downloads a YouTube video as MP3 using yt-dlp"""
    try:
        ydl_opts = {
            "format":
            "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "128"
            }],  # Faster, better quality
            "noplaylist":
            True,
            "quiet":
            True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            video_title = re.sub(r"[^a-zA-Z0-9 ]", "",
                                 info["title"])  # Clean filename
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
    """Renders the HTML page and clears old downloads"""
    shutil.rmtree(DOWNLOAD_FOLDER, ignore_errors=True)
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
    return render_template('index.html')


@app.route('/get_video_title', methods=['POST'])
def get_video_title():
    youtube_url = request.form.get('video_id')
    video_id = extract_video_id(youtube_url)

    if not video_id:
        return jsonify({"error": "Invalid YouTube URL"}), 400

    try:
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            return jsonify({"title": info["title"]})
    except Exception as e:
        print(f"Error fetching video title: {e}")
        return jsonify({"error": "Unable to fetch title"}), 500


@app.route('/get_videos', methods=['POST'])
def get_videos():
    """Fetch related YouTube videos asynchronously"""
    youtube_url = request.form.get('video_id')
    video_id = extract_video_id(youtube_url)

    if not video_id:
        return jsonify({"error": "Invalid YouTube URL"}), 400

    videos = get_related_videos(video_id)
    return jsonify(videos)


@app.route('/download', methods=['POST'])
def download():
    """Download selected videos in parallel and return a ZIP file"""
    if not request.is_json:
        return jsonify({"error":
                        "Invalid request format. Expected JSON."}), 400

    urls = request.json.get('urls', [])
    if not urls:
        return jsonify({"error": "No videos selected"}), 400

    downloaded_files = []

    # Use ThreadPoolExecutor for parallel downloading
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results = executor.map(download_mp3, urls)

    for filename in results:
        if filename:
            downloaded_files.append(filename)

    if not downloaded_files:
        return jsonify({"error": "No files downloaded"}), 500

    zip_path = "downloads.zip"
    shutil.make_archive("downloads", 'zip', DOWNLOAD_FOLDER)
    return send_file(zip_path, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)
