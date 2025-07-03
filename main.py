import os
import random
import time
import schedule
import tempfile
from datetime import datetime
from instagrapi import Client
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# جلب بيانات البيئة
IG_USERNAME = os.getenv("IG_USERNAME")
IG_PASSWORD = os.getenv("IG_PASSWORD")
SERVICE_ACCOUNT_JSON = os.getenv("SERVICE_ACCOUNT_JSON")
INSTAGRAM_SESSION_FILE = os.getenv("INSTAGRAM_SESSION_FILE")

if not (SERVICE_ACCOUNT_JSON and (INSTAGRAM_SESSION_FILE or (IG_USERNAME and IG_PASSWORD))):
    raise Exception("❌ تأكد من تعيين IG_USERNAME و IG_PASSWORD أو INSTAGRAM_SESSION_FILE و SERVICE_ACCOUNT_JSON في البيئة")

# إعداد Google Drive
with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as tmp_file:
    tmp_file.write(SERVICE_ACCOUNT_JSON)
    tmp_file.flush()
    SERVICE_ACCOUNT_FILE = tmp_file.name

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)

POSTED_LOG = "posted_from_drive.txt"

POST_CAPTIONS = [
    "🚀 انطلق بقوة كل يوم!",
    "🎯 هذا الفيديو فيه درس كبير.",
    "💡 شاركنا رأيك في التعليقات!",
    "🔥 محتوى مميز جدًا!"
]

STORY_CAPTIONS = [
    "✨ شاهد هذا الآن!",
    "🔥 لحظات لا تفوّت!",
    "🚀 المحتوى مستمر!",
    "📌 شوف الستوري الجديد!"
]

def load_posted():
    if not os.path.exists(POSTED_LOG):
        return set()
    with open(POSTED_LOG, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f.readlines())

def save_posted(filename):
    with open(POSTED_LOG, "a", encoding="utf-8") as f:
        f.write(filename + "\n")

def get_videos_from_drive():
    query = "mimeType contains 'video/' and trashed = false"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    return results.get("files", [])

def download_video(file):
    request = drive_service.files().get_media(fileId=file['id'])
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        downloader = MediaIoBaseDownload(tmp, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return tmp.name

def publish_post(client, file):
    caption = random.choice(POST_CAPTIONS)
    tmp_path = download_video(file)
    try:
        print(f"⬆️ نشر ريلز: {file['name']} مع وصف: {caption}")
        client.clip_upload(tmp_path, caption)
        save_posted(file['name'])
    except Exception as e:
        print(f"❌ فشل نشر {file['name']}: {e}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def publish_story(client, file):
    caption = random.choice(STORY_CAPTIONS)
    tmp_path = download_video(file)
    try:
        print(f"⬆️ نشر ستوري: {file['name']} مع وصف: {caption}")
        client.video_upload_to_story(tmp_path, caption)
        save_posted(file['name'])
    except Exception as e:
        print(f"❌ فشل ستوري: {file['name']}: {e}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def login_instagram():
    client = Client()
    print("🔐 تسجيل الدخول إلى إنستغرام...")
    if INSTAGRAM_SESSION_FILE and os.path.exists(INSTAGRAM_SESSION_FILE):
        try:
            client.load_settings(INSTAGRAM_SESSION_FILE)
            # login بدون باراميتر سيستخدم الجلسة
            client.login()
            print("✅ تم تسجيل الدخول باستخدام الجلسة.")
            return client
        except Exception as e:
            print(f"⚠️ فشل استخدام الجلسة: {e}")
    # تسجيل الدخول بالطريقة التقليدية
    client.login(IG_USERNAME, IG_PASSWORD)
    print("✅ تم تسجيل الدخول باستخدام اسم المستخدم وكلمة المرور.")
    return client

def main():
    client = login_instagram()
    posted = load_posted()

    def pick_available_videos(n=1):
        all_files = get_videos_from_drive()
        available = [f for f in all_files if f['name'].lower().endswith('.mp4') and f['name'] not in posted]
        random.shuffle(available)
        return available[:n]

    def publish_two_posts():
        print("🟢 بدء نشر منشورين...")
        for file in pick_available_videos(2):
            publish_post(client, file)
            posted.add(file['name'])
            time.sleep(random.randint(30, 60))

    def publish_daily_story():
        print("🔵 نشر ستوري...")
        files = pick_available_videos()
        if not files:
            print("🚫 لا توجد فيديوهات متاحة.")
            return
        publish_story(client, files[0])
        posted.add(files[0]['name'])

    def publish_story_then_one_post():
        publish_daily_story()
        print("⏳ انتظار 2 دقائق...")
        time.sleep(2 * 60)
        publish_two_posts()

    # جدولة النشر (بتوقيت UTC)
    schedule.every().monday.at("11:30").do(publish_two_posts)
    schedule.every().tuesday.at("11:30").do(publish_two_posts)
    schedule.every().wednesday.at("11:30").do(publish_two_posts)
    schedule.every().thursday.at("11:30").do(publish_two_posts)
    schedule.every().friday.at("11:30").do(publish_two_posts)

    schedule.every().monday.at("17:30").do(publish_two_posts)
    schedule.every().tuesday.at("17:30").do(publish_two_posts)
    schedule.every().wednesday.at("17:30").do(publish_two_posts)
    schedule.every().thursday.at("17:30").do(publish_two_posts)
    schedule.every().friday.at("17:30").do(publish_two_posts)
    schedule.every().day.at("17:030").do(publish_two_posts)
    schedule.every().day.at("08:30").do(publish_daily_story)

    print("⏰ السكربت يعمل الآن تلقائيًا. اضغط Ctrl+C للإيقاف.")

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        print("🛑 تم إيقاف السكربت.")

if __name__ == "__main__":
    main()
