from os import environ as env
import time, re

from ...adapter import Adapter
from ...messages import Message
from ...user import User
from ...utils import INCLUDED_MESSAGES, GREET_MESSAGE
from slackclient import SlackClient
from HTMLParser import HTMLParser


class SlackAdapter(Adapter):
    def __init__(self, robot):
        super(SlackAdapter, self).__init__(robot)

        token = env.get('SLACK_TOKEN')
        if not token:
            raise RuntimeError("Missing environment variable SLACK_TOKEN")

        self.bot_id = None
        self.client = SlackClient(token)
        self.is_running = True
        self.im_channels = {}
        self._initialize()
        self.parser = HTMLParser()

    def send(self, message, text, attachments=None, is_im=False):
        if not message.room:
            return
        chan = message.room
        if is_im:
            c = self.im_channels.get(chan)
            if not c:
                self._init_im_channels()
                c = self.im_channels.get(chan)
                if not c:
                    return
            chan = c
        self._send_message(chan, text, attachments)

    def reply(self, message, text):
        if not self._is_direct_message(message.room):
            text = u'<@{}>: {}'.format(message.user.id, text)

        self._send_message(message.room, text)

    def close(self):
        self.is_running = False

    def run(self):
        if not self.client.rtm_connect():
            # TODO: use logger once implemented
            print "error: unable to connect to RTM service"
            return

        self._loop_forever()

    def _loop_forever(self):
        while self.is_running:
            events = self.client.rtm_read()
            if events:
                self._dispatch(events)
            try:
                time.sleep(0.3)
            except:
                return

    def _legacy_get_own_info(self):
        api_call = self.client.api_call("users.list")
        if api_call.get('ok'):
            users = api_call.get('members')
            for user in users:
                if 'name' in user and user.get('name') == self.robot.name:
                    return user

    def _init_im_channels(self):
        im_channels = self.client.api_call('im.list')
        if im_channels.get('ok'):
            for c in im_channels['ims']:
                self.im_channels[c['user']] = c['id']

    def _initialize(self):
        name = self.client.server.username
        user = self._find_user(name)

        if not user:
            user = self._legacy_get_own_info()
            self.bot_id = user.get('id')
        else:
            self.bot_id = user.id
            self.robot.name = user.name

        self._init_im_channels()
        #self.robot.emit('connected')

    def _dispatch(self, events):
        for event in events:
            type = event.get('type')
            if not type:
                continue
            is_bot = False
            # Ignore any events sent by the bot
            user_id = event.get('user')
            if user_id:
                user = self._find_user(user_id)
            else:
                is_bot = True
                user_id = event.get('bot_id')
                user = event.get('username')
            if user_id and user_id == self.bot_id:
                continue

            message = None
            if type == 'message' or type == 'bot_message':
                subtype = event.get('subtype') or 'message'
                if subtype == 'message':
                    message = self._adapt_message(User(user_id, user, is_bot), event)
            elif type == 'channel_joined':
                self._send_message(event['channel'].get('id'), GREET_MESSAGE)

            if message:
                self.receive(message)

    def _adapt_message(self, user, event):
        channel_id = event.get('channel')
        text = self.parser.unescape(event['text'])
        ts = event['ts']

        if channel_id and self._is_direct_message(channel_id):
            text = u'{}'.format(text)

        # TODO: chat threads
        return Message(user, channel_id, text, ts, event)

    def _send_message(self, channel_id, text, attachments=None):
        self.client.api_call("chat.postMessage", channel=channel_id, text=text, attachments=attachments)

    def _find_user(self, name_or_id):
        return self.client.server.users.find(name_or_id)

    @staticmethod
    def _is_direct_message(channel_id):
        return (channel_id or '').startswith('D')

    def update_from_history(self, channel, days_ago=14):
        if not any(c.isdigit() for c in channel):
            channels = self.client.api_call('conversations.list')
            chan = filter(lambda x: x[u'name'] == channel, channels[u'channels'])
            if not chan:
                return
            chan = chan[0][u'id']
        else:
            chan = channel
        now = time.time()
        start_date = now - (86400.0 * days_ago)
        messages = []
        not_done = True
        while not_done:
            msgs = self.client.api_call('conversations.history', channel=chan, oldest=start_date, latest=now, limit=200)
            if msgs['ok']:
                messages += msgs['messages']
                now = msgs['messages'][-1]['ts']
            not_done = msgs['has_more']
        if messages:
            def filter_f(m):
                uid = m.get('user', self.bot_id)
                text = m.get('text', '').lower()
                ok = uid != self.bot_id and any(re.match(p, text) for p in INCLUDED_MESSAGES)
                return ok
            filtered = filter(filter_f, messages)
            self._dispatch(sorted(filtered, key=lambda x:x['ts']))
