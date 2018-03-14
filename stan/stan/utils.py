import re
import pickle, os

GREET_MESSAGE = "HI! I'M MR MEESEEKS! LOOK AT ME!"
JIRA_TICKET_REGEX = re.compile(r'[A-Z,a-z]{1,10}-?[A-Za-z]+-\d+')
STOPWORDS = ["going", "deploying", "to", "and", "then", "on", "again", "&"]
SUB_APPS = ['ui', 'aperture', 'river', 'alfred', 'macula', 'retina']
COMPONENTS = SUB_APPS + ['optic']
REFRESH_RATE = 60 if os.environ.get('DEBUG', True) else 3600
TICKET_LIFE_SPAN = 600 if os.environ.get('DEBUG', True) else 172800
TICKET_NOTIFY_TIME = 300 if os.environ.get('DEBUG', True) else 86400
VM_ME = r'vm (me)?'
DEPLOY_MESSAGE = r'ing (to|on)'
FREE_SERVERS = [r'.*?free|available.*?', r'.*?use']
UPDATE_FROM_HISTORY = r'update (from )?history'
LIST_ALL = '.*?all (staging\s)?(servers|boxes|stgs).*?'
SHIP_BUILDER_MESSAGE = r'deployed'
UPDATE_BRANCHES = r'.*?pushed to branch.*?'
STILL_IN = r'(y([eash]+)?)|(n([opeah]+)?)'
BOX_DETAILS = r'status of'
HELP = r'help'
RELEASE_BOX = r'release'
CHOICES = r'(\d,?)+'
EXCLUDED_MESSAGES = [UPDATE_FROM_HISTORY, LIST_ALL, UPDATE_BRANCHES, STILL_IN] + FREE_SERVERS
INCLUDED_MESSAGES = [SHIP_BUILDER_MESSAGE, DEPLOY_MESSAGE]
UPDATE_BRANCHES_RATE = 3600


def __abs_path__(fl):
    curr_dir = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
    abs_file_path = os.path.join(curr_dir, fl)
    return abs_file_path


def load_bot_memory():
    mem = None
    if not os.path.isfile(__abs_path__("memory.pickle")):
        return {}
    try:
        with open(__abs_path__("memory.pickle"), 'rb') as f:
            mem = pickle.load(f)
    except:
        return {}
    return mem


def save_memory(mem):
    with open(__abs_path__("memory.pickle"), 'wb') as f:
        pickle.dump(mem, f, -1)


def clean_name(name):
    return name.replace('-optic', '').replace('-intelligence', '')


def humanize_time(time):
    days, rem = divmod(time, 86400)
    hours, remainder = divmod(time, 3600)
    minutes, seconds = divmod(remainder, 60)
    if days > 0:
        return "{0} day{1}".format(int(days), 's' if days > 1 else '')
    elif hours > 0:
        return '{0} hour{1}'.format(int(hours), 's' if hours > 1 else '')
    elif minutes > 0:
        return '{0} minute{1}'.format(int(minutes), 's' if minutes > 1 else '')
    return "{0} second{1}".format(int(seconds), 's' if seconds > 1 else '')


def find_box_match(box, options):
    for o in options:
        if o == 'optic' and 'ui' not in box and box not in SUB_APPS:
            return o #optic
        elif o == 'ui' and 'ui' in box:
            return o #ui
        elif o in box:
            return o
    return None

