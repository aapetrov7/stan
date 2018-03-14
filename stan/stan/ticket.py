class Ticket(object):
    def __init__(self, tid, url):
        self.id = tid
        self.url = url

    def __str__(self):
        return self.id

    @property
    def link_name(self):
        return '<' + self.url + '|' + self.id + '>'
