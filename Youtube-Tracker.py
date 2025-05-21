import requests
import pandas as pd
import os
import datetime

# === KONFIGURATION ===
API_KEY = os.environ.get("YOUTUBE_API_KEY")
CHANNEL_ID = "UCV9sD9OqGJzmeuC8Kbx4qLQ"
NUM_TRACKED_VIDEOS = 3
EXCEL_FILE = "jp_views.xlsx"
TRACK_INTERVALS = [1, 5, 12, 24, 48]  # in Stunden

# === YouTube API-URLs ===
SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEO_URL = "https://www.googleapis.com/youtube/v3/videos"

def get_latest_video_ids():
    params = {
        "key": API_KEY,
        "channelId": CHANNEL_ID,
        "part": "snippet",
        "order": "date",
        "maxResults": 10
    }
    res = requests.get(SEARCH_URL, params=params).json()
    print("Verwendeter API Key:", API_KEY)
    print("API RESPONSE:", res)
    videos = [item for item in res["items"] if item["id"]["kind"] == "youtube#video"]
    return [v["id"]["videoId"] for v in videos[:10]]

def get_video_details(video_ids):
    params = {
        "key": API_KEY,
        "id": ",".join(video_ids),
        "part": "statistics,snippet"
    }
    res = requests.get(VIDEO_URL, params=params).json()
    details = []
    for item in res["items"]:
        published_at = item["snippet"]["publishedAt"]
        published_time = datetime.datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ")
        published_time = published_time.replace(tzinfo=datetime.timezone.utc)
        views = int(item["statistics"].get("viewCount", 0))
        details.append({
            "video_id": item["id"],
            "title": item["snippet"]["title"],
            "published_at": published_time,
            "current_views": views
        })
    return details

def load_data():
    if os.path.exists(EXCEL_FILE):
        return pd.read_excel(EXCEL_FILE)
    else:
        return pd.DataFrame(columns=["video_id", "title", "published_at", "timestamp", "hours_since_upload", "views"])

def save_data(df):
    df.to_excel(EXCEL_FILE, index=False)

def main():
    now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    df = load_data()
    known_ids = df["video_id"].unique()
    
    latest_video_ids = get_latest_video_ids()
    new_video_ids = [vid for vid in latest_video_ids if vid not in known_ids]

    video_ids_to_track = list(known_ids[-NUM_TRACKED_VIDEOS:])
    video_ids_to_track += new_video_ids[:NUM_TRACKED_VIDEOS - len(video_ids_to_track)]
    video_ids_to_track = list(set(video_ids_to_track))

    video_data = get_video_details(video_ids_to_track)

    for video in video_data:
        age_hours = (now - video["published_at"]).total_seconds() / 3600

        for target_hour in TRACK_INTERVALS:
            exists = (
                (df["video_id"] == video["video_id"]) &
                (df["hours_since_upload"].round(2) == round(target_hour, 2))
            ).any()

            if not exists and age_hours >= target_hour:
                df = pd.concat([df, pd.DataFrame([{
                    "video_id": video["video_id"],
                    "title": video["title"],
                    "published_at": video["published_at"],
                    "timestamp": now,
                    "hours_since_upload": target_hour,
                    "views": video["current_views"]
                }])], ignore_index=True)

    save_data(df)

if __name__ == "__main__":
    main()
