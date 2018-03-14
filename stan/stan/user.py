class User(object):
    def __init__(self, _id, full_data, is_bot=False):
        self.id = _id
        self.name = full_data.real_name
        self.is_bot = is_bot

    def __str__(self):
        return self.name

