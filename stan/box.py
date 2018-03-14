import datetime, time
from dateutil.parser import parse
from stan.utils import humanize_time
from stan import robot
import re


class Box(object):
    def __init__(self, id, usr, taken, ticket, expires):
        self.id = id
        self.user = usr
        self.taken = taken
        self.free = False
        self.expires = expires
        self.ticket = ticket
        self.branch = 'Unknown'

    def __str__(self):
        return self.id

    def emojize_status(self, ticket=None):
        ok = ':cookie:'                 # old but still in use
        suspicious = ':cheese_wedge:'   # hasn't been released but is not actively used
        fresh = ':pickle:'              # was created recently
        now = datetime.datetime.now()
        taken = datetime.datetime.fromtimestamp(self.taken)
        if not ticket:
            if (now - taken).days < 2:
                return fresh
            else:
                return suspicious
        ticket_updated = parse(ticket.fields.updated)
        r = re.compile(r'(?<=isStale":)[a-z]+')
        dev = r.findall(ticket.fields.customfield_11800)
        if dev:
            git_stale = bool(dev[0])
        else:
            git_stale = True
        if (now - taken).days < 2:
            return fresh
        elif (now - ticket_updated).days > 3 and (now - taken).days > 2 and git_stale:
            return suspicious
        else:
            return ok

    def full_info(self):
        info = 'Box {}:\n'.format(self.id)
        if self.free:
            info += 'Status: Currently Free\n'
        else:
            t = robot.get_ticket(self.ticket.id) if self.ticket else None
            date_format = '%H:%M %d/%m/%y'
            info += 'Status: Currently Occupied {}\n'.format(self.emojize_status(t)) + \
                    'Used by: {}\n'.format(self.user.name) +\
                    'Taken since: {}\n'.format(datetime.datetime.fromtimestamp(self.taken).strftime(date_format)) +\
                    'Will be automatically vacated in: {}\n'.format(humanize_time(self.expires-time.time())) +\
                    'Ticket: {}\n'.format(self.ticket.link_name if self.ticket else 'Currently not known')
            if t:
                info += 'Ticket status: {}\n'.format(t.fields.status)
                info += 'Ticket last updated: {}\n'.format(parse(t.fields.updated).strftime(date_format))
            info += 'Branch: {}\n'.format(self.branch)
        return info

