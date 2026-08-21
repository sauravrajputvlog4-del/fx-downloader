import os
import sys
import uuid
import time
import json
import re
import glob
import threading
import shutil
import subprocess
import urllib.parse
from flask import Flask, render_template, request, jsonify, Response, send_file
from flask_cors import CORS

# Setup robust portable path handling
if getattr(sys, 'frozen', False):
    BUNDLE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    EXE_DIR = os.path.dirname(sys.executable)
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    EXE_DIR = BUNDLE_DIR

TEMPLATES_DIR = os.path.join(BUNDLE_DIR, 'templates')
STATIC_DIR = os.path.join(BUNDLE_DIR, 'static')
DOWNLOAD_DIR = os.path.join(EXE_DIR, 'downloads')
CONFIG_PATH = os.path.join(EXE_DIR, 'config.json')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Setup FFmpeg (Checks bundled binary first, then static-ffmpeg)
FFMPEG_BIN = None
for candidate in [
    os.path.join(EXE_DIR, 'ffmpeg.exe'),
    os.path.join(BUNDLE_DIR, 'ffmpeg.exe'),
    os.path.join(EXE_DIR, '_internal', 'ffmpeg.exe'),
    os.path.join(EXE_DIR, 'ffmpeg.EXE')
]:
    if os.path.exists(candidate):
        FFMPEG_BIN = candidate
        os.environ["PATH"] = os.path.dirname(candidate) + os.pathsep + os.environ.get("PATH", "")
        break

if not FFMPEG_BIN:
    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
        FFMPEG_BIN = shutil.which('ffmpeg')
    except Exception as e:
        print(f"static_ffmpeg: {e}")

if not FFMPEG_BIN:
    try:
        import imageio_ffmpeg
        FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()
        ffmpeg_dir = os.path.dirname(FFMPEG_BIN)
        if ffmpeg_dir not in os.environ.get("PATH", ""):
            os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
    except Exception as e:
        print(f"imageio_ffmpeg: {e}")

print(f"Active FFmpeg path: {FFMPEG_BIN}")

import yt_dlp

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
CORS(app)

BASE_DIR = BUNDLE_DIR

# Default Windows Downloads folder
DEFAULT_DOWNLOADS = os.path.join(os.path.expanduser('~'), 'Downloads')
if not os.path.exists(DEFAULT_DOWNLOADS):
    DEFAULT_DOWNLOADS = DOWNLOAD_DIR

def get_save_folder():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                folder = data.get('save_folder')
                if folder and os.path.exists(folder):
                    return folder
        except Exception:
            pass
    return DEFAULT_DOWNLOADS

def set_save_folder(folder_path):
    if os.path.exists(folder_path):
        try:
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump({'save_folder': folder_path}, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
    return False

# Initialize config if not present
if not os.path.exists(CONFIG_PATH):
    set_save_folder(DEFAULT_DOWNLOADS)

# In-memory download tasks tracker
tasks = {}
download_history = []

def format_bytes(bytes_val):
    if not bytes_val or bytes_val <= 0:
        return "Unknown size"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} TB"

def format_duration(seconds):
    if not seconds:
        return "00:00"
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

def sanitize_filename(name):
    """Sanitizes filename for Windows filesystem."""
    name = re.sub(r'[\\/*?:"<>|]', '_', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:120] if name else "video"

def clean_old_files():
    """Removes download staging files older than 2 hours."""
    now = time.time()
    try:
        for fname in os.listdir(DOWNLOAD_DIR):
            fpath = os.path.join(DOWNLOAD_DIR, fname)
            if os.path.isfile(fpath) and (now - os.path.getmtime(fpath)) > 7200:
                try:
                    os.remove(fpath)
                except Exception:
                    pass
    except Exception as e:
        print(f"Cleanup error: {e}")

def ensure_premiere_pro_compatibility(file_path):
    """Ensures video is encoded in standard H.264 (AVC) + AAC with YUV420p
    so Adobe Premiere Pro, Final Cut, DaVinci Resolve, and media players import
    both video & audio tracks seamlessly without dropping the video.
    """
    if not file_path or not os.path.exists(file_path):
        return file_path

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in ['.mp4', '.mkv', '.webm', '.mov']:
        return file_path

    if not FFMPEG_BIN or not os.path.exists(FFMPEG_BIN):
        return file_path

    try:
        probe_cmd = [FFMPEG_BIN, '-i', file_path]
        probe_res = subprocess.run(probe_cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        log = probe_res.stderr.lower()

        # Check if already h264/avc1 video and aac/mp4a audio
        has_h264 = ('video: h264' in log) or ('video: avc1' in log)
        has_aac = ('audio: aac' in log) or ('audio: mp4a' in log)

        # If it's VP9/AV1 or Opus/other audio, transcode to standard Premiere-friendly H.264+AAC
        if not (has_h264 and has_aac):
            print(f"[Premiere Fix] Transcoding {os.path.basename(file_path)} to H.264 + AAC for Adobe Premiere Pro compatibility...")
            temp_output = os.path.join(os.path.dirname(file_path), f"fixed_{os.path.basename(file_path)}")
            
            conv_cmd = [
                FFMPEG_BIN, '-y',
                '-i', file_path,
                '-c:v', 'libx264',
                '-preset', 'veryfast',
                '-crf', '18',
                '-pix_fmt', 'yuv420p',
                '-c:a', 'aac',
                '-b:a', '320k',
                '-movflags', '+faststart',
                temp_output
            ]
            subprocess.run(conv_cmd, check=True, capture_output=True)
            
            if os.path.exists(temp_output) and os.path.getsize(temp_output) > 1000:
                os.replace(temp_output, file_path)
                print(f"[Premiere Fix] Successfully encoded in H.264 + AAC: {file_path}")
    except Exception as e:
        print(f"[Premiere Fix] Warning during codec optimization: {e}")

    return file_path

def sanitize_url(raw_url):
    """Cleans playlist and tracking params for ultra-fast single video resolution."""
    raw_url = raw_url.strip()
    yt_match = re.search(r'(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/|youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})', raw_url)
    if yt_match:
        video_id = yt_match.group(1)
        return f"https://www.youtube.com/watch?v={video_id}"
    return raw_url

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/settings', methods=['GET'])
def get_settings():
    return jsonify({
        'success': True,
        'save_folder': get_save_folder()
    })

@app.route('/api/select-folder', methods=['POST'])
def select_folder():
    def open_picker():
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            folder = filedialog.askdirectory(
                initialdir=get_save_folder(),
                title="Select Save Location for Fx Downloader"
            )
            root.destroy()
            return folder
        except Exception as e:
            print(f"Folder picker error: {e}")
            return None

    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(open_picker)
        chosen_folder = future.result()

    if chosen_folder and os.path.exists(chosen_folder):
        set_save_folder(chosen_folder)
        return jsonify({'success': True, 'save_folder': chosen_folder})
    
    return jsonify({'success': False, 'save_folder': get_save_folder()})

@app.route('/api/open-folder', methods=['POST'])
def open_folder():
    folder = get_save_folder()
    try:
        if os.path.exists(folder):
            os.startfile(folder)
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    return jsonify({'success': False, 'error': 'Folder not found'}), 404

def extract_with_fallbacks(base_opts, target_url, download=False):
    """Tries multiple client profiles to bypass YouTube cloud datacenter bot blocks."""
    strategies = [
        ['ios', 'android', 'mweb'],
        ['android_creator', 'ios'],
        ['tv_embedded', 'web_creator'],
        ['web', 'default']
    ]
    last_exception = None
    for clients in strategies:
        opts = dict(base_opts)
        opts['extractor_args'] = {'youtube': {'player_client': clients}}
        opts['http_headers'] = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1'
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                res = ydl.extract_info(target_url, download=download)
                if res:
                    return res
        except Exception as e:
            last_exception = e
            continue
    raise last_exception or Exception("Could not extract media with any client strategy.")

@app.route('/api/info', methods=['POST'])
def get_video_info():
    data = request.get_json() or {}
    raw_url = data.get('url', '').strip()

    if not raw_url:
        return jsonify({'success': False, 'error': 'Please provide a valid video URL.'}), 400

    url = sanitize_url(raw_url)

    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'extract_flat': False,
        'socket_timeout': 25,
    }
    if FFMPEG_BIN:
        ydl_opts['ffmpeg_location'] = FFMPEG_BIN

    try:
        info = extract_with_fallbacks(ydl_opts, url, download=False)
        if not info:
            return jsonify({'success': False, 'error': 'Could not extract video information.'}), 400

            if 'entries' in info and info['entries']:
                info = [e for e in info['entries'] if e][0]

            title = info.get('title', 'Unknown Video')
            thumbnail = info.get('thumbnail')
            duration = info.get('duration')
            uploader = info.get('uploader') or info.get('channel') or info.get('creator') or 'Unknown Creator'
            view_count = info.get('view_count')
            webpage_url = info.get('webpage_url', url)
            extractor = info.get('extractor_key', 'Universal')

            # Parse formats
            raw_formats = info.get('formats', [])
            video_resolutions = {}

            target_heights = [2160, 1440, 1080, 720, 480, 360]
            resolution_labels = {
                2160: '4K Ultra HD (2160p)',
                1440: '2K Quad HD (1440p)',
                1080: 'Full HD (1080p HD)',
                720: 'HD (720p)',
                480: 'SD (480p)',
                360: 'SD (360p)'
            }

            for f in raw_formats:
                height = f.get('height')
                filesize = f.get('filesize') or f.get('filesize_approx')
                fps = f.get('fps')
                vcodec = f.get('vcodec')
                acodec = f.get('acodec')
                ext = f.get('ext', 'mp4')

                if height and height > 0:
                    matched_h = None
                    for th in target_heights:
                        if height >= th - 30 and height <= th + 30:
                            matched_h = th
                            break
                    if not matched_h:
                        matched_h = height

                    if matched_h not in video_resolutions or (filesize and filesize > (video_resolutions[matched_h].get('raw_size') or 0)):
                        label = resolution_labels.get(matched_h, f"{matched_h}p")
                        if fps and fps >= 50:
                            label += f" {int(fps)}fps"

                        video_resolutions[matched_h] = {
                            'height': matched_h,
                            'target_height': str(matched_h),
                            'format_id': f.get('format_id'),
                            'label': label,
                            'quality_tag': '4K UHD' if matched_h >= 2160 else ('2K QHD' if matched_h >= 1440 else ('1080p FHD' if matched_h >= 1080 else ('720p HD' if matched_h >= 720 else f'{matched_h}p'))),
                            'ext': 'mp4',
                            'fps': fps,
                            'filesize_str': format_bytes(filesize) if filesize else 'Best Quality',
                            'raw_size': filesize or 0,
                            'has_audio': acodec != 'none' and bool(acodec)
                        }

            sorted_video_options = sorted(video_resolutions.values(), key=lambda x: x['height'], reverse=True)

            sorted_audio_options = [
                {'format_id': 'bestaudio_mp3_320', 'label': 'MP3 Studio Master (320 kbps)', 'ext': 'mp3', 'quality': '320kbps', 'tag': '320 kbps'},
                {'format_id': 'bestaudio_mp3_192', 'label': 'MP3 Standard Quality (192 kbps)', 'ext': 'mp3', 'quality': '192kbps', 'tag': '192 kbps'},
                {'format_id': 'bestaudio_m4a', 'label': 'M4A / AAC Lossless Audio', 'ext': 'm4a', 'quality': 'Original', 'tag': 'AAC'}
            ]

            if not sorted_video_options:
                sorted_video_options.append({
                    'height': 1080,
                    'target_height': 'best',
                    'format_id': 'bestvideo+bestaudio/best',
                    'label': 'Highest Available Resolution (MP4)',
                    'quality_tag': 'Max Quality',
                    'ext': 'mp4',
                    'filesize_str': 'Auto / Best',
                    'raw_size': 0,
                    'has_audio': True
                })

            response_payload = {
                'success': True,
                'title': title,
                'thumbnail': thumbnail,
                'duration': duration,
                'duration_str': format_duration(duration),
                'uploader': uploader,
                'view_count': f"{view_count:,}" if view_count else None,
                'url': webpage_url,
                'platform': extractor,
                'video_options': sorted_video_options,
                'audio_options': sorted_audio_options
            }

            return jsonify(response_payload)

    except Exception as e:
        return jsonify({'success': False, 'error': f"Failed to fetch video: {str(e)}"}), 500


def background_downloader(task_id, raw_url, download_type, target_quality, format_id):
    tasks[task_id] = {
        'status': 'starting',
        'percent': 0,
        'speed': '0 KB/s',
        'eta': '--',
        'downloaded_bytes': 0,
        'total_bytes': 0,
        'filename': '',
        'file_id': '',
        'custom_title': '',
        'saved_path': '',
        'save_folder': get_save_folder(),
        'error': None
    }

    clean_old_files()
    url = sanitize_url(raw_url)

    file_uuid = str(uuid.uuid4())[:8]
    output_template = os.path.join(DOWNLOAD_DIR, f"dl_{file_uuid}.%(ext)s")

    def progress_hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes') or 0
            percent = 0
            if total > 0:
                percent = round((downloaded / total) * 100, 1)
            elif '_percent_str' in d:
                try:
                    percent = float(d['_percent_str'].replace('%', '').strip())
                except:
                    percent = 45

            speed_val = d.get('speed')
            speed_str = format_bytes(speed_val) + "/s" if speed_val else d.get('_speed_str', 'Downloading...')
            eta_val = d.get('eta')
            eta_str = f"{eta_val}s" if eta_val else d.get('_eta_str', '--')

            tasks[task_id]['status'] = 'downloading'
            tasks[task_id]['percent'] = min(percent, 95)
            tasks[task_id]['speed'] = speed_str
            tasks[task_id]['eta'] = eta_str
            tasks[task_id]['downloaded_bytes'] = downloaded
            tasks[task_id]['total_bytes'] = total

        elif d['status'] == 'finished':
            tasks[task_id]['status'] = 'processing'
            tasks[task_id]['percent'] = 98
            tasks[task_id]['speed'] = 'Converting & Merging...'
            tasks[task_id]['eta'] = 'Almost done'

    ydl_opts = {
        'outtmpl': output_template,
        'progress_hooks': [progress_hook],
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'overwrites': True,
        'retries': 5,
        'fragment_retries': 5,
        'socket_timeout': 30,
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android', 'android_creator', 'web_creator', 'mweb']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1'
        }
    }

    if FFMPEG_BIN:
        ydl_opts['ffmpeg_location'] = FFMPEG_BIN

    if download_type == 'audio':
        bitrate = '320'
        if '192' in target_quality or '192' in format_id:
            bitrate = '192'
        elif '128' in target_quality or '128' in format_id:
            bitrate = '128'

        if 'm4a' in format_id or target_quality == 'm4a':
            ydl_opts.update({
                'format': 'bestaudio[ext=m4a]/bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'm4a',
                }]
            })
        else:
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': bitrate,
                }]
            })
    else:
        clean_q = target_quality.lower().replace('p', '').strip()
        if clean_q.isdigit():
            h = int(clean_q)
            ydl_opts.update({
                'format': f'bestvideo[height<={h}][vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={h}]+bestaudio/best[height<={h}]/best',
                'merge_output_format': 'mp4',
            })
        elif '4k' in clean_q or '2160' in clean_q:
            ydl_opts.update({
                'format': 'bestvideo[height<=2160][vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=2160]+bestaudio/best',
                'merge_output_format': 'mp4'
            })
        elif '2k' in clean_q or '1440' in clean_q:
            ydl_opts.update({
                'format': 'bestvideo[height<=1440][vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[height<=1440][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1440]+bestaudio/best',
                'merge_output_format': 'mp4'
            })
        else:
            ydl_opts.update({
                'format': 'bestvideo[vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best',
                'merge_output_format': 'mp4'
            })

    try:
        tasks[task_id]['status'] = 'downloading'
        tasks[task_id]['percent'] = 5

        info_dict = extract_with_fallbacks(ydl_opts, url, download=True)
        if 'entries' in info_dict and info_dict['entries']:
            info_dict = [e for e in info_dict['entries'] if e][0]

            candidates = [
                f for f in glob.glob(os.path.join(DOWNLOAD_DIR, f"dl_{file_uuid}.*"))
                if not f.endswith('.part') and not f.endswith('.ytdl') and not re.search(r'\.f\d+\.', os.path.basename(f))
            ]

            actual_file = candidates[0] if candidates else None

            if not actual_file or not os.path.exists(actual_file):
                all_uuid_files = glob.glob(os.path.join(DOWNLOAD_DIR, f"dl_{file_uuid}*"))
                if all_uuid_files:
                    actual_file = all_uuid_files[0]

            if not actual_file or not os.path.exists(actual_file):
                raise Exception("The requested video stream could not be converted on disk.")

            # Ensure 100% Adobe Premiere Pro / Video Editor compatibility (H.264 + AAC)
            if download_type == 'video':
                tasks[task_id]['speed'] = 'Optimizing for Premiere Pro...'
                actual_file = ensure_premiere_pro_compatibility(actual_file)

            file_id = os.path.basename(actual_file)
            ext = os.path.splitext(actual_file)[1].replace('.', '') or ('mp3' if download_type == 'audio' else 'mp4')
            raw_title = info_dict.get('title', 'video')
            clean_display_name = f"{sanitize_filename(raw_title)}.{ext}"

            # Auto-save direct copy into user's chosen folder
            chosen_save_folder = get_save_folder()
            direct_destination = os.path.join(chosen_save_folder, clean_display_name)
            try:
                shutil.copy2(actual_file, direct_destination)
            except Exception as e:
                print(f"Direct copy error: {e}")

            tasks[task_id]['status'] = 'completed'
            tasks[task_id]['percent'] = 100
            tasks[task_id]['speed'] = 'Ready'
            tasks[task_id]['eta'] = 'Done'
            tasks[task_id]['filename'] = clean_display_name
            tasks[task_id]['custom_title'] = clean_display_name
            tasks[task_id]['file_id'] = file_id
            tasks[task_id]['saved_path'] = direct_destination
            tasks[task_id]['save_folder'] = chosen_save_folder

            download_history.insert(0, {
                'id': task_id,
                'title': raw_title,
                'file_id': file_id,
                'custom_title': clean_display_name,
                'thumbnail': info_dict.get('thumbnail'),
                'type': download_type,
                'quality': target_quality or 'High Quality',
                'size': format_bytes(os.path.getsize(actual_file)),
                'saved_path': direct_destination,
                'timestamp': time.strftime("%H:%M:%S")
            })
            if len(download_history) > 25:
                download_history.pop()

    except Exception as e:
        tasks[task_id]['status'] = 'error'
        tasks[task_id]['error'] = str(e)
        print(f"Download task error: {e}")


@app.route('/api/download', methods=['POST'])
def start_download():
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    download_type = data.get('type', 'video')
    quality = str(data.get('quality', '1080')).strip()
    format_id = str(data.get('format_id', '')).strip()

    if not url:
        return jsonify({'success': False, 'error': 'Missing URL parameter.'}), 400

    task_id = str(uuid.uuid4())

    thread = threading.Thread(
        target=background_downloader,
        args=(task_id, url, download_type, quality, format_id),
        daemon=True
    )
    thread.start()

    return jsonify({'success': True, 'task_id': task_id})


@app.route('/api/progress/<task_id>', methods=['GET'])
def get_progress(task_id):
    def event_stream():
        while True:
            task = tasks.get(task_id)
            if not task:
                yield f"data: {json.dumps({'status': 'not_found'})}\n\n"
                break

            yield f"data: {json.dumps(task)}\n\n"

            if task['status'] in ['completed', 'error']:
                break
            time.sleep(0.4)

    return Response(event_stream(), mimetype='text/event-stream')


@app.route('/api/task-status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({'status': 'not_found'}), 404
    return jsonify(task)


@app.route('/api/get-file/<file_id>', methods=['GET'])
def get_file(file_id):
    safe_file_id = os.path.basename(file_id)
    file_path = os.path.join(DOWNLOAD_DIR, safe_file_id)

    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found or has been cleaned up.'}), 404

    custom_name = request.args.get('name')
    if not custom_name:
        for item in download_history:
            if item.get('file_id') == safe_file_id:
                custom_name = item.get('custom_title')
                break

    if not custom_name:
        for t in tasks.values():
            if t.get('file_id') == safe_file_id:
                custom_name = t.get('custom_title')
                break

    if not custom_name:
        custom_name = safe_file_id

    return send_file(
        file_path,
        as_attachment=True,
        download_name=custom_name
    )


@app.route('/api/history', methods=['GET'])
def get_history():
    return jsonify({'success': True, 'history': download_history})


@app.route('/api/clear-history', methods=['POST'])
def clear_history():
    global download_history
    download_history = []
    clean_old_files()
    return jsonify({'success': True})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Fx Downloader Server running on http://127.0.0.1:{port}...")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
