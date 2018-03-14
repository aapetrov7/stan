import re


class Matcher(object):
    def match(self, message):
        pass


class RegexMatcher(Matcher):
    def __init__(self, pattern):
        self.regex = re.compile(pattern, re.IGNORECASE)

    def match(self, message):
        message = re.sub(r'<.*> ', ' ', message)
        if message:
            return self.regex.findall(message)


class RobotNameMatcher(Matcher):
    def __init__(self, wrapped, robot):
        self.wrapped = wrapped
        self.robot = robot

    def match(self, message):
        if not message:
            return

        tokens = message.lower().split(' ')
        if not tokens:
            return

        name = self.robot.at_bot.lower()
        first_token = tokens[0]

        if first_token == name:
            return self.wrapped.match(message)
