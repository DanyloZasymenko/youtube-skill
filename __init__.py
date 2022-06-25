import os.path

from mycroft import MycroftSkill, intent_file_handler
from mycroft.util.format import pronounce_number
from mycroft.util.parse import extract_number
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


class VideoValidationException(Exception):
    """This is not really for errors, just a handy way to tidy up the initial checks."""

    pass


class Youtube(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)

    @intent_file_handler('open.video.intent')
    def handle_open_video(self, message):
        query = message.data.get('query')
        self.log.info(f"The query is {query}")

        results = self.search_videos(query)

        self.speak_dialog('found-results', data={
            'query': query,
            'results': self.speak_results(results)
        })
        self.log.info(f"Found results {self.speak_results(results)}")
        video_ordinal = self.request_video_ordinal(results)
        self.log.info(f"The video ordinal is {video_ordinal}")
        video = results[video_ordinal - 1]
        self.save_audio(video['video_url'])
        self.log.info(f"Playing video {video['title']} - {video['video_url']}")
        play_proc = play_wav(str(self.get_file_path(video)))
        play_proc.wait()


    def get_file_path(self, video):
        return f"{SAVE_PATH}/{video['title']}.wav"

    def request_video_ordinal(self, results):
        def validate_ordinal(string):
            extracted_ordinal = None
            extract = extract_number(string, ordinals=True, lang=self.lang)
            if extract is not None:
                extracted_ordinal = extract[0]
            return extracted_ordinal is not None

        response = self.get_response("ask-which-open", validator=validate_ordinal)
        if response is not None:
            raise VideoValidationException("No response to request for video to open.")
        else:
            number = extract_number(response, ordinals=True)
            if number is None:
                raise VideoValidationException("No video specified")
            if number > len(results):
                raise VideoValidationException("Number is too large")

        return number

    def speak_results(self, results):
        speak_results = []
        for i in range(results):
            speak_results.append(pronounce_number(i) + ' ' + results['title'])
        return speak_results

    def search_videos(self, arg, number_of_results=10):
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
