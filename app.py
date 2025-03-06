from flask import Flask, render_template, request, jsonify, send_file
import http.client
import json
import os
from urllib.parse import unquote
import yt_dlp
import shutil
import time
import re
import concurrent.futures  # For parallel downloads
import imageio_ffmpeg as ffmpeg
import subprocess
import threading

app = Flask(__name__)
DOWNLOAD_FOLDER = "downloads"
WEBM_FOLDER = "RECOMMEND_DOWNLOAD"
download_in_progress = threading.Lock()

try:
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
    print("FFmpeg is installed and working:\n", result.stdout)
except FileNotFoundError:
    print("FFmpeg is NOT installed or not found in PATH.")

shutil.rmtree(DOWNLOAD_FOLDER, ignore_errors=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

API_HOST = "youtube-v31.p.rapidapi.com"
API_KEY = "56dfead9d0msh16dd2994a8f600dp12c061jsn103a13978d3f"  # Replace with your actual API key!

YOUTUBE_REGEX = re.compile(
    r"^(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})"
)
#####################################################################

def extract_video_idp(youtube_url):
    """Extracts video ID from YouTube URL"""
    match = YOUTUBE_REGEX.match(youtube_url)
    return match.group(1) if match else None

def get_related_videosp(video_id, max_results=5):
    """Fetch related YouTube videos"""
    try:
        conn = http.client.HTTPSConnection(API_HOST)
        headers = {"x-rapidapi-key": API_KEY, "x-rapidapi-host": API_HOST}
        conn.request("GET", f"/search?relatedToVideoId={video_id}&part=id,snippet&type=video&maxResults={max_results}", headers=headers)
        res = conn.getresponse()

        if res.status != 200:
            return []

        data = json.loads(res.read().decode("utf-8"))
        return [{
            "title": item["snippet"]["title"],
            "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}"
        } for item in data.get("items", [])]
    except Exception as e:
        print(f"Error fetching related videos: {e}")
        return []

def clear_folder():
    # Check if the folder exists
    if os.path.exists(WEBM_FOLDER):
        # If the folder exists, clear its contents
        for filename in os.listdir(WEBM_FOLDER):
            file_path = os.path.join(WEBM_FOLDER, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")
    else:
        # If the folder doesn't exist, create it
        os.makedirs(WEBM_FOLDER)


def download_webmp(youtube_url, video_title):
    try:
        safe_title = sanitize_filename(video_title)
        ffmpeg_path = ffmpeg.get_ffmpeg_exe()       
        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "128"
                }
            ],
            "cookies": os.path.abspath("cookies.txt"),  # Ensure absolute path
            "noplaylist": True,
            "quiet": False,
            "ffmpeg_location": ffmpeg_path,
            "outtmpl": os.path.join(WEBM_FOLDER, f"{safe_title}.%(ext)s")  # Fix misplaced comma
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
        print(f"Downloaded: {youtube_url} as {video_title}.mp3")
    
    except Exception as e:
        print(f"Error downloading {youtube_url}: {e}")

def start_background_downloadp(video_list):
    """Starts downloading all related videos in the background"""
    for video in video_list:
        download_webmp(video["url"], video["title"])
        time.sleep(1)  # Small delay to prevent system overload

@app.route("/player")
def indexp():
    """Render HTML page"""
    clear_folder()
    return render_template("player.html")

@app.route("/get_videosp", methods=["POST"])
def get_videosp():
    """Fetch related videos and start background downloads"""
    youtube_url = request.form.get("video_id")
    video_id = extract_video_idp(youtube_url)
    if not video_id:
        return jsonify({"error": "Invalid YouTube URL"}), 400

    videos = get_related_videosp(video_id)
    threading.Thread(target=start_background_downloadp, args=(videos,), daemon=True).start()
    return jsonify(videos)

@app.route("/list_audiop")
def list_audiop():
    """Returns a list of available .webm files"""
    files = [f for f in os.listdir(WEBM_FOLDER) if f.endswith(".mp3")]
    return jsonify(files)
@app.route("/cleartrackp", methods=['POST'])
def clear_tracks_endpoint():
    clear_folder()  # Call the clear_tracks function

def sanitize_filename(title):
    """Removes invalid filename characters from a video title."""
    return re.sub(r'[\\/*?:"<>|]', "", title) 
#clear_folder
@app.route("/stream_audio/<filename>")
def stream_audiop(filename):
    """Streams an audio file"""
    filename = unquote(filename)  # Replace %20 with spaces
    file_path = os.path.join(WEBM_FOLDER, filename)
    try:
        return send_file(file_path, mimetype="audio/mp3", as_attachment=False)
    except Exception as e:
        return jsonify({"error": str(e)}),500



####################################################################
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
            headers=headers)
        res = conn.getresponse()

        if res.status != 200:
            return []

        data = json.loads(res.read().decode("utf-8"))
        return [{
            "title": item["snippet"]["title"],
            "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}"
        } for item in data.get("items", [])]
    except Exception as e:
        print(f"Error fetching related videos: {e}")
        return []


def download_mp3(youtube_url):
    try:
        ffmpeg_path = ffmpeg.get_ffmpeg_exe()
        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "128"
                }
            ],
            "cookies": "cookies.txt",  # Add this line
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


@app.route('/')
def index():
    shutil.rmtree(DOWNLOAD_FOLDER, ignore_errors=True)
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
    return render_template('index.html')

@app.route('/get_videos', methods=['POST'])
def get_videos():
    youtube_url = request.form.get('video_id')
    video_id = extract_video_id(youtube_url)

    if not video_id:
        return jsonify({"error": "Invalid YouTube URL"}), 400

    try:
        with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            video_title = info.get("title", "Unknown Title")  # Fallback in case title is missing
    except Exception as e:
        print(f"Error fetching video title: {e}")
        video_title = "Unknown Title"


    videos = get_related_videos(video_id)
    print(videos)
    videos.insert(0, {"title": video_title, "url": youtube_url})  # Insert original video with actual title
    return jsonify(videos)

@app.route('/download_video')
def download_video():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"error": "No video URL provided"}), 400

    # Simulate download delay
    import time
    time.sleep(2)  # Simulating download time

    return jsonify({"status": "Downloaded", "url": video_url})

@app.route('/download', methods=['POST'])
def download():
    if not request.is_json:
        return jsonify({"error": "Invalid request format. Expected JSON."}), 400

    if download_in_progress.locked():
        return jsonify({"error": "A download is already in progress. Please wait."}), 429

    urls = request.json.get('urls', [])
    if not urls:
        return jsonify({"error": "No videos selected"}), 400

    downloaded_files = []
    with download_in_progress:
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
