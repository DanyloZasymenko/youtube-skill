from mycroft import MycroftSkill, intent_file_handler


class Youtube(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)

    @intent_file_handler('youtube.intent')
    def handle_youtube(self, message):
        name = message.data.get('name')
        number = ''
        search_results = ''
        title = ''

        self.speak_dialog('youtube', data={
            'name': name,
            'search_results': search_results,
            'title': title,
            'number': number
        })


def create_skill():
    return Youtube()

