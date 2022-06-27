import os.path
import re
import urllib.parse
import urllib.request

import vlc
from mycroft import MycroftSkill, intent_file_handler
from mycroft.skills.intent_service import AdaptIntent
from mycroft.util.format import nice_duration
from mycroft.skills.audioservice import AudioService
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
    'noplaylist': True,
    'cachedir': False
}


class NoResponseException(Exception):
    pass


class Youtube(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)
        self.search_results = []
        self.play_words = []
        self.pause_words = []
        self.stop_words = []
        self.next_words = []
        self.prev_words = []
        self.yes_words = []
        self.audio_service = None
        self.is_playing = False
        self.is_paused = False
        self.current_video_index = None

    def initialize(self):
        self.audio_service = AudioService(self.bus)
        self.play_words = self.translate_list('play')
        self.pause_words = self.translate_list('pause')
        self.stop_words = self.translate_list('stop')
        self.next_words = self.translate_list('next')
        self.prev_words = self.translate_list('prev')
        self.yes_words = self.translate_list('yes')

    @intent_file_handler('open.video.intent')
    def handle_open_video(self, message):
        query = message.data.get('query')
        self.is_playing = False
        self.is_paused = False
        self.current_video_index = None
        self.log.info(f"The query is {query}")
        self.speak_dialog('searching', data={
            'query': query
        })

        self.search_results = self.search_videos(query)
        result_count = len(self.search_results)

        if result_count == 0:
            self.speak_dialog('no-results-found', data={
                'query': query
            })
            return

        self.speak_dialog('found-results-count', data={
            'count': result_count,
            'query': query
        })

        count, video = self.look_through_results()
        self.current_video_index = count
        self.log.info(f"Playing video with index {count}: {video['title']} - {video['video_url']}")
        self._handle_play_video(video)

    # @intent_file_handler(AdaptIntent().optionally("query").require("next").optionally("video"))
    # def handle_next_video(self):
    #     self._handle_next_video()

    @intent_file_handler('next.video.intent')
    def handle_next_video_padatious(self):
        self._handle_next_video()

    # @intent_file_handler(AdaptIntent().optionally("query").require("prev").optionally("video"))
    # def handle_prev_video(self):
    #     self._handle_prev_video()

    @intent_file_handler('prev.video.intent')
    def handle_prev_video_padatious(self):
        self._handle_prev_video()

    # @intent_file_handler(AdaptIntent().require("pause").optionally("video"))
    # def handle_pause_video(self):
    #     self._handle_pause_video()

    @intent_file_handler('pause.video.intent')
    def handle_pause_video_padatious(self):
        self._handle_pause_video()

    # @intent_file_handler(AdaptIntent().require("stop").optionally("video"))
    # def handle_stop_video(self):
    #     self._handle_stop_video()

    @intent_file_handler('stop.video.intent')
    def handle_stop_video_padatious(self):
        self._handle_stop_video()

    # @intent_file_handler(AdaptIntent().require("play").optionally("video"))
    # def handle_play_video(self):
    #     self._handle_play_video()

    @intent_file_handler('play.video.intent')
    def handle_play_video_padatious(self):
        self._handle_play_video()

    def _handle_next_video(self):
        self.log.info("Handle next video")
        self._handle_stop_video()

        if not self.search_results or not self.current_video_index:
            self.log.info("No playlist available! Doing nothing")
        else:
            next_video_index = self.current_video_index + 1
            if next_video_index == len(self.search_results):
                next_video_index = 0

            self.log.info(f"Next video index is {next_video_index}")
            self.current_video_index = next_video_index
            self._handle_play_video(self.search_results[next_video_index])

    def _handle_prev_video(self):
        self.log.info("Handle prev video")
        self._handle_stop_video()

        if not self.search_results or not self.current_video_index:
            self.log.info("No playlist available! Doing nothing")
        else:
            prev_video_index = self.current_video_index - 1
            if self.current_video_index == 0:
                prev_video_index = len(self.search_results) - 1

            self.log.info(f"Prev video index is {prev_video_index}")
            self.current_video_index = prev_video_index
            self._handle_play_video(self.search_results[prev_video_index])

    def _handle_play_video(self, video):
        if not self.is_playing:
            if self.is_paused:
                self.log.info("Resume the video")
                self.audio_service.resume()
            else:
                self.log.info("Play the video")
                self.audio_service.play(video['audio_url'])
            self.is_playing = True
            self.is_paused = False
        else:
            self.log.info("The video is already playing! Doing nothing")

    def _handle_pause_video(self):
        if not self.is_playing or self.is_paused:
            self.log.info("No playing video! Doing nothing")
        else:
            self.log.info("Pausing the video")
            self.is_playing = False
            self.is_paused = True
            self.audio_service.pause()

    def _handle_stop_video(self):
        if self.audio_service is not None:
            self.log.info("Stopping the video")
            self.is_playing = False
            self.is_paused = False
            self.audio_service.stop()
        else:
            self.log.info("No media player found! Doing nothing")

    def look_through_results(self, count=0):
        video = self.get_video_info(self.search_results[count])
        self.speak_dialog('video-info', data={
            'title': video['title'],
            'channel': video['channel']
        })

        if self.recursive_ask_for_confirm():
            return count, video
        else:
            return self.look_through_results(count + 1)

    def recursive_ask_for_confirm(self, count=0):
        user_response = self.get_response("ask-for-open-confirmation")

        if count == 2:
            self.log.info("Reached max number of attempts to confirm video start! Stopping")
            raise NoResponseException("Reached max number of attempts to confirm video start!")

        if not user_response:
            self.log.info("No user response. Ask again")
            return self.recursive_ask_for_confirm(count + 1)
        elif any(i.strip() in user_response for i in self.play_words) \
                or any(i.strip() in user_response for i in self.yes_words):
            self.log.info("Opening this video")
            return True
        elif any(i.strip() in user_response for i in self.next_words):
            self.log.info("Go to the next video")
            return False
        else:
            self.log.info("Can not understand response! Stopping")
            raise NoResponseException("Can not understand response!")

    def get_file_path(self, video):
        return f"{SAVE_PATH}/{video['title']}.wav"

    def search_videos(self, name):
        query_string = urllib.parse.urlencode({"search_query": name})
        format_url = urllib.request.urlopen("https://www.youtube.com/results?" + query_string)
        search_results = re.findall(r"watch\?v=(\S{11})", format_url.read().decode())
        return [f"https://www.youtube.com/watch?v={result}" for result in search_results]

    def get_video_info(self, url):
        self.log.info(f"Getting info for video {url}")
        with YoutubeDL(SEARCH_OPTIONS) as ydl:
            result = ydl.extract_info(url, process=False, download=False)

        return self.format_data(result)

    def format_data(self, video):
        return {
            'channel': video['channel'],
            'channel_url': video['channel_url'],
            'title': video['title'],
            'description': video['description'],
            'video_url': video['webpage_url'],
            'duration': video['duration'],  # in seconds
            'upload_date': video['upload_date'],  # YYYYDDMM
            'view_count': video['view_count'],
            'like_count': video['like_count'],
            'audio_url': self.get_audio_url(video)
        }

    def get_audio_url(self, video):
        formats = video['formats']

        r = max(formats, key=lambda x: x.get('abr', -1))
        return r['url']

    def save_audio(self, url):
        with YoutubeDL(SAVE_AUDIO_OPTIONS) as ydl:
            ydl.download([url])


def create_skill():
    return Youtube()
