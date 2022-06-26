import os.path

from mycroft import MycroftSkill, intent_file_handler
from mycroft.util import play_wav
from requests import get
from youtube_dl import YoutubeDL

ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
SAVE_PATH = os.path.join(ROOT_PATH, 'files')
SAVE_AUDIO_OPTIONS = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'wav',
        'preferredquality': '192'
    }],
    'postprocessor_args': [
        '-ar', '16000'
    ],
    'prefer_ffmpeg': True,
    'keepvideo': True,
    'outtmpl': SAVE_PATH + '/%(title)s.%(ext)s'
}
SEARCH_OPTIONS = {
    'format': 'bestaudio',
    'noplaylist': 'True'
}


class Youtube(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)

    @intent_file_handler('open.video.intent')
    def handle_open_video(self, message):
        query = message.data.get('query')
        self.log.info(f"The query is {query}")
        self.speak_dialog('searching', data={
            'query': query
        })

        video = self.recursive_search(query, 1)
        self.log.info(f"Playing video {video['title']} - {video['video_url']}")
        self.save_audio(video['video_url'])
        play_proc = play_wav(str(self.get_file_path(video)))
        play_proc.wait()

    def recursive_search(self, query, count):
        self.log.info(f"Searching attempt {count}")
        result = self.search_videos(query, 1)[0]

        self.speak_dialog('found-results', data={
            'query': query,
            'results': result['title']
        })
        self.log.info(f"Found result {result}")
        user_response = self.get_response("ask-for-open-confirmation", num_retries=1)

        yes_words = self.translate_list("yes")

        if not user_response or not any(i.strip() in user_response for i in yes_words):
            return self.recursive_search(query, count + 1)
        else:
            return result

    def get_file_path(self, video):
        return f"{SAVE_PATH}/{video['title']}.wav"

    def search_videos(self, arg, number_of_results=5):
        def format_data(video):
            return {
                'channel': video['uploader'],
                'channel_url': video['uploader_url'],
                'title': video['title'],
                'description': video['description'],
                'video_url': video['webpage_url'],
                'duration': video['duration'],  # in seconds
                'upload_date': video['upload_date'],  # YYYYDDMM
                'thumbnail': video['thumbnail']
            }

        with YoutubeDL(SEARCH_OPTIONS) as ydl:
            try:
                get(arg)
            except:
                videos = ydl.extract_info(f"ytsearch{number_of_results}:{arg}", download=False)['entries']
            else:
                videos = ydl.extract_info(arg, download=False)

        return [format_data(video) for video in videos]

    def save_audio(self, url):
        with YoutubeDL(SAVE_AUDIO_OPTIONS) as ydl:
            ydl.download([url])


def create_skill():
    return Youtube()
