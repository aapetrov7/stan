import traceback

from .adapters.slack.adapter import SlackAdapter
from .events import EventBus
from .listener import Listener
from .matchers import RegexMatcher, RobotNameMatcher
from .messages import Message
from github import Github
from jira import JIRA
import os, time

from utils import save_memory, load_bot_memory, JIRA_TICKET_REGEX, UPDATE_BRANCHES_RATE


class Robot(object):
    def __init__(self, name='stan', **kwargs):
        self.name = name
        self._load_adapter()
        self._listeners = []
        self._memory = load_bot_memory()
        self._bus = EventBus()
        git_token = os.environ.get("GIT_LOGIN")
        git_pass = os.environ.get("GIT_PASS")
        jira_uname = os.environ.get("JIRA_NAME")
        jira_pass = os.environ.get("JIRA_PASS")
        options = {'server': "https://threatstream.atlassian.net"}
        self.git = Github(git_token, git_pass)
        self.jira = JIRA(basic_auth=(jira_uname, jira_pass), options=options)
        self.at_bot = "<@" + self.adapter.bot_id + ">"
        print ("updating branches")
        if 'optic' not in self._memory and 'optic-ui' not in self._memory:
            self.update_branches()
        if not os.environ.get('DEBUG', True):
            print ("updating boxes")
            self.adapter.update_from_history('devops-console')

    def update_branches(self):
        repos = ['optic', 'optic-ui']
        rfs = {}
        for repo in repos:
            r = self.git.get_repo('threatstream/'+repo)
            branches = r.get_branches()
            for branch in branches:
                rfs[branch.commit.sha] = branch.name
            self._memory[repo] = rfs
        self._memory['last_update'] = time.time()

    def _load_adapter(self):
        self.adapter = SlackAdapter(self)

    def run(self):
        print("Bot started")
        self.adapter.run()

    def shutdown(self):
        save_memory(self._memory)
        self.adapter.close()

    def send(self, room, text, attachments=None, is_im=False):
        fake_message = Message(None, room, None)
        self.adapter.send(fake_message, text, attachments, is_im)

    def reply(self, user, room, text):
        fake_message = Message(user, room, None)
        self.adapter.reply(fake_message, text)

    def on(self, type):
        def wrapper(f):
            self._bus.subscribe(type, f)
            return f

        return wrapper

    def emit(self, type, data=None):
        self._bus.publish(type, data)

    def receive(self, message):
        for listener in self._listeners:
            try:
                if listener(message):
                    return
            except:
                traceback.print_exc()
        self.send(message.room, "Boy you got me there I don't know what that means try typing *help*")


    def respond(self, pattern):
        def wrapper(f):
            if type(pattern) == list:
                for p in pattern:
                    self._add_listener(RobotNameMatcher(RegexMatcher(p), self), f)
            else:
                matcher = RegexMatcher(pattern)
                wrapper = RobotNameMatcher(matcher, self)
                self._add_listener(wrapper, f)

        return wrapper

    def hear(self, pattern):
        def wrapper(f):
            if type(pattern) == list:
                for p in pattern:
                    self._add_listener(RegexMatcher(p), f)
            else:
                self._add_listener(RegexMatcher(pattern), f)
            return f

        return wrapper

    def listen(self, matcher):
        def wrapper(f):
            self._add_listener(matcher, f)
            return f

        return wrapper

    def _add_listener(self, matcher, func):
        listener = Listener(self, matcher, func)
        self._listeners.append(listener)

    def put_to_memory(self, key, data):
        self._memory[key] = data

    def get_from_memory(self, key, default=None):
        return self._memory.get(key, default)

    def _time_to_update(self):
        now = time.time()
        last_update = self._memory.get('last_update', now)
        return now - last_update >= UPDATE_BRANCHES_RATE

    def get_ticket_from_commit(self, repo, commit):
        try:
            r = self.git.get_repo('threatstream/'+repo)
            refs = self.get_from_memory(repo)
            sha = r.get_commit(sha=commit)
            if not sha:
                return ""
            sha = sha.sha
            match = refs.get(sha)
            if not match and self._time_to_update():
                self.update_branches()
                match = refs.get(sha)
            return match
        except Exception as e:
            print (e)
        return ""

    def get_ticket(self, ticket):
        if not ticket or not JIRA_TICKET_REGEX.match(str(ticket)):
            return None
        return self.jira.issue(ticket)

    def ticket_is_closed(self, ticket):
        ticket = self.get_ticket(ticket)
        if not ticket:
            return False
        return ticket.fields.status == 'closed'

    def update_from_history(self, channel):
        self.adapter.update_from_history(channel)


def get_ticket(ticket):
    if not ticket or not JIRA_TICKET_REGEX.match(str(ticket)):
        return None
    jira_uname = os.environ.get("JIRA_NAME")
    jira_pass = os.environ.get("JIRA_PASS")
    options = {'server': "https://threatstream.atlassian.net"}
    jira = JIRA(basic_auth=(jira_uname, jira_pass), options=options)
    return jira.issue(ticket)
