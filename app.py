from flask import Flask, render_template, request, jsonify, send_file
import http.client
import json
import os
import yt_dlp
import shutil
import re
import threading
import math
import zipfile

app = Flask(__name__)

# Folders for downloads
MP3_FOLDER = "downloads"
ZIP_FILE = "downloads.zip"

# YouTube API setup
API_HOST = "youtube-v31.p.rapidapi.com"
API_KEY = "56dfead9d0msh16dd2994a8f600dp12c061jsn103a13978d3f"

# Regex to extract video ID
YOUTUBE_REGEX = re.compile(r"^(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})")

# Ensure directory exists
os.makedirs(MP3_FOLDER, exist_ok=True)

def extract_video_id(youtube_url):
    match = YOUTUBE_REGEX.match(youtube_url)
    return match.group(1) if match else None

def get_related_videos(video_id, max_results=5):
    try:
        conn = http.client.HTTPSConnection(API_HOST)
        headers = {"x-rapidapi-key": API_KEY, "x-rapidapi-host": API_HOST}
        conn.request("GET", f"/search?relatedToVideoId={video_id}&part=id,snippet&type=video&maxResults={max_results}", headers=headers)
        res = conn.getresponse()
        if res.status != 200:
            return []
        data = json.loads(res.read().decode("utf-8"))
        return [{"title": item["snippet"]["title"], "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}", "id": item['id']['videoId']} for item in data.get("items", [])]
    except Exception as e:
        print(f"Error fetching related videos: {e}")
        return []

def sanitize_filename(title):
    return re.sub(r'[\\/*?:"<>|]', "", title)

def download_mp3(youtube_url, video_title):
    try:
        safe_title = sanitize_filename(video_title)
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(MP3_FOLDER, f"{safe_title}.%(ext)s"),
            "noplaylist": True,
            "quiet": True,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
    except Exception as e:
        print(f"Error downloading {youtube_url}: {e}")

def start_background_download(video_list, num_threads=4):
    if not video_list:
        return
    chunk_size = math.ceil(len(video_list) / num_threads)
    chunks = [video_list[i:i + chunk_size] for i in range(0, len(video_list), chunk_size)]
    threads = []
    for chunk in chunks:
        thread = threading.Thread(target=download_chunk, args=(chunk,))
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()

def download_chunk(video_chunk):
    for video in video_chunk:
        download_mp3(video["url"], video["title"])

def zip_downloaded_files():
    with zipfile.ZipFile(ZIP_FILE, "w") as zipf:
        for root, _, files in os.walk(MP3_FOLDER):
            for file in files:
                zipf.write(os.path.join(root, file), file)

def clear_folder():
    if os.path.exists(MP3_FOLDER):
        for filename in os.listdir(MP3_FOLDER):
            file_path = os.path.join(MP3_FOLDER, filename)
            try:
                os.unlink(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")
    os.makedirs(MP3_FOLDER, exist_ok=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/download")
def download_page():
    return render_template("download.html")

@app.route("/get_videosp", methods=["POST"])
def get_videos():
    youtube_url = request.form.get("video_id")
    video_id = extract_video_id(youtube_url)
    if not video_id:
        return jsonify([])
    videos = get_related_videos(video_id)
    threading.Thread(target=start_background_download, args=(videos,), daemon=True).start()
    return jsonify(videos)

@app.route("/list_audiop")
def list_audio():
    files = [f for f in os.listdir(MP3_FOLDER) if f.endswith(".mp3")]
    return jsonify(files)

@app.route("/cleartrackp", methods=['POST'])
def clear_tracks_endpoint():
    clear_folder()
    return "Folder cleared"

@app.route("/stream_audio/<filename>")
def stream_audio(filename):
    file_path = os.path.join(MP3_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, mimetype="audio/mp3", as_attachment=False)
    return jsonify({"error": "File not found"}), 404

@app.route("/get_videos_download", methods=["POST"])
def get_videos_download():
    youtube_url = request.form.get("video_id")
    video_id = extract_video_id(youtube_url)
    if not video_id:
        return jsonify([])
    videos = get_related_videos(video_id)
    return jsonify(videos)

@app.route("/start_download", methods=["POST"])
def start_download():
    selected_videos = request.json.get("videos", [])
    if not selected_videos:
        return jsonify({"error": "No videos selected"}), 400
    download_chunk(selected_videos)
    zip_downloaded_files()
    return send_file(ZIP_FILE, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
