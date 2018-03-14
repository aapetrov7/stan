from stan import robot
from stan.ticket import Ticket
from stan.utils import (
    find_box_match,
    JIRA_TICKET_REGEX, STOPWORDS, clean_name, REFRESH_RATE, TICKET_LIFE_SPAN, CHOICES,
    VM_ME, DEPLOY_MESSAGE, SHIP_BUILDER_MESSAGE, LIST_ALL, FREE_SERVERS, UPDATE_FROM_HISTORY,
    UPDATE_BRANCHES, STILL_IN, humanize_time, TICKET_NOTIFY_TIME, BOX_DETAILS, HELP, RELEASE_BOX
)
import re
import difflib
import time, os, threading
from threading import Timer
from box import Box


def assign_boxes(boxes, user):
    mem = robot.get_from_memory('box_list')
    now = time.time()
    for b in boxes:
        box = mem.get(b, Box(b, user, now, None, now+TICKET_LIFE_SPAN))
        box.user = user
        box.free = False
        box.taken = now
        box.expires = now+TICKET_LIFE_SPAN
        mem[b] = box
    robot.put_to_memory('box_list', mem)


#@robot.respond(VM_ME)
@robot.hear(VM_ME)
def vm_me(res):
    boxes_rx = re.compile(r'(?<=vm me).*')
    rq = boxes_rx.findall(res.message.text)
    searching = [i.strip() for i in re.split(r'[&,]', rq[0])]
    both = 'ui' in searching and 'optic' in searching
    mem = robot.get_from_memory('box_list')
    free = [b for b in mem if mem[b].free]
    chosen = []
    for f in free:
        match = find_box_match(f, searching)
        if not match:
            continue
        # if we're looking for both ui and optic boxes and we found one of them
        if both and match in ['ui', 'optic']:
            # get the partner box
            p_box = f.replace('-ui', '') if match == 'ui' else f+'-ui'
            if p_box not in free:
                # partner is taken skip
                continue
            chosen.append(p_box)
            searching.remove('ui' if match != 'ui' else 'optic')
        chosen.append(f)    # add the box we just found to the chosen box list
        searching.remove(match)   # remove the box type we matched from the list of boxes we're still looking for
        if not searching:
            break
    if len(searching) == 0 and chosen:
        assign_boxes(chosen, res.message.user)  # mark chosen boxes as in use
        message = '\n'.join(chosen)
        robot.send(res.message.room, "I have assigned the following box{0} to you:\n{1}".format(
            'es' if len(chosen) > 1 else '', message))
        # tell user which boxes we assigned to them
        return
    robot.send(res.message.room, "I'm sorry but there were not enough free boxes to meet your request :(")


@robot.hear(UPDATE_BRANCHES)
def update_branches(res):
    res.robot.update_branches()


@robot.hear(BOX_DETAILS)
def status_of(res):
    box = res.message.text.replace('status of', '').lstrip().rstrip()
    table = res.robot.get_from_memory('box_list', [])
    if box in table:
        message = table[box].full_info()
    else:
        message = "I'm sorry but I don't have any information about {}".format(box)
    res.robot.send(res.message.room, message)


@robot.hear(DEPLOY_MESSAGE)
def handle_deploy_msg(res):
    user = res.message.user
    msg = res.message.text.split()
    boxes = [clean_name(w) for w in msg if w not in STOPWORDS]
    ticket = JIRA_TICKET_REGEX.findall(res.message.text)
    table = res.robot.get_from_memory("box_list", {})
    for box in boxes:
        if 'prod' in box:
            continue
        taken = float(res.message.id)
        table[box] = Box(box, user, taken, ticket, taken + TICKET_LIFE_SPAN)
    res.robot.put_to_memory("box_list", table)


@robot.hear(FREE_SERVERS)
def list_free_servers(res):
    """Shows only the servers that are free"""
    res.robot.send(res.message.room, "Checking this may take a while")
    clean_up_boxes(True)
    table = res.robot.get_from_memory("box_list", {})
    free_boxes = "Ok I checked these boxes are free:\n"
    found = False
    for b in sorted(table.iterkeys()):
        if table[b].free:
            free_boxes += b + '\n'
            found = True
    if not found:
        free_boxes = "There are no free boxes right now"
    res.robot.send(res.message.room, free_boxes)


@robot.hear(UPDATE_FROM_HISTORY)
def update_from_history(res):
    res.robot.send(res.message.room, "Hold on I'm reading your messages")
    res.robot.update_from_history(res.message.room)
    res.robot.send(res.message.room, "Update complete")


def give_me_a_server(res):
    pass


@robot.hear(LIST_ALL)
def show_servers(res):
    """Shows all servers with their status"""
    table = res.robot.get_from_memory("box_list", {})
    servers = ""
    for s in sorted(table.iterkeys()):
        serv = table.get(s)
        message = s + ': '
        if not serv.free:
            message += str(serv.user)
            if serv.ticket:
                ticket = serv.ticket
                message += ' - ' + (str(ticket) if type(ticket) is not Ticket else ticket.link_name)
            else:
                message += ' Ticket not known yet'
        else:
            message += 'Free'
        servers += message + '\n'
    if not servers:
        servers = "I have no idea what boxes there are out there right now type *update from history* to help me update my box list"
    res.robot.send(res.message.room, servers)


@robot.hear(SHIP_BUILDER_MESSAGE)
def handle_shipbuilder(res):
    if not res.message.user.is_bot and not os.environ.get('DEBUG', True):
        return
    hash_p = re.compile(r'(?<=\()[a-z0-9]+(?=\))')
    server_name = re.compile(r'[a-z]{3,}[0-9](-?([a-z]+)?)+')
    commit = hash_p.findall(res.message.text)
    server = server_name.findall(res.message.text)
    server = server[0] if server else ''
    target = res.message.text.split(' ')[1]
    target = clean_name(target)
    table = res.robot.get_from_memory("box_list", {})
    candidates = difflib.get_close_matches(target, table.keys())
    if len(candidates) > 0:
        c = candidates[0]
    else:
        return
    if commit:
        branch = robot.get_ticket_from_commit(commit=commit[0], repo='optic' if 'ui' not in server else 'optic-ui')
        if not branch:
            table[c].branch = commit[0]
        else:
            ticket = branch.split('/')
            ticket = ticket[1] if len(ticket) > 0 else ticket[0]
            try:
                t = robot.get_ticket(ticket)
                ticket = Ticket(ticket, str(t.permalink()))
            except:
                pass
            table[c].ticket = ticket
            table[c].branch = branch
        res.robot.put_to_memory("box_list", table)


@robot.hear(RELEASE_BOX)
def free_box(res):
    table = robot.get_from_memory('box_list', {})
    box = res.message.text.split()[1]
    b = table.get(box, Box(box, None, None, None, None))
    b.free = True
    table[box] = b
    robot.put_to_memory('box_list', table)
    robot.send(res.message.room, "{0} is now free to use!!".format(box))


@robot.hear(STILL_IN)
def still_in(res):
    rem = robot.get_from_memory('removables', [])
    user = res.message.room
    username = str(res.message.user)
    if username in rem:
        reply = res.message.text
        b = rem[username]['box'][0]
        usr = rem[username]
        table = robot.get_from_memory('box_list', {})
        has_expired = usr['expires'][0] < time.time()
        del rem[username]
        if re.match(r'(y([eash]+)?)', reply) and str(table[b].user) == username and not has_expired:
            table[b].expires = time.time() + TICKET_LIFE_SPAN
            robot.send(user, "Ok I'll keep {0} for you for another {1}".format(b, humanize_time(TICKET_LIFE_SPAN)))
        elif re.match(r'(n([opeah]+)?)', reply):
            table[b].free = True
            robot.send(user, "OK I'll free up {} and let others know that they can use it".format(b))
        else:
            robot.send(user, '{} has already been freed up'.format(b))
        robot.put_to_memory('box_list', table)
        robot.put_to_memory('removables', rem)


@robot.respond(HELP)
def help(res):
    message = '*help* - lists all available commands\n' \
              '*list all boxes* - gives a list with a short summary of the status of each staging server\n' \
              '*status of (box name)* - gives the full status of a staging box\n' \
              '*list free servers* - gives a list of all boxes that are currently vacant\n' \
              '*update from history* - discover all servers and their status using the chat history of the current channel\n' \
              '*release (box name)* - sets the specified box to free'
    res.robot.send(res.message.room, message)


@robot.respond(CHOICES)
def picked(res):
    pickles = [int(p) for p in res.message.text.split(',')]
    rem = robot.get_from_memory('removables', [])
    table = robot.get_from_memory('box_list', {})
    user = res.message.room
    username = str(res.message.user)
    if username not in rem:
        return
    item = rem[username]
    boxes = item['boxes']
    expires = item['expires']
    now = time.time()
    extended = []
    for p in xrange(len(boxes)):
        is_picked = p in pickles
        has_expired = expires[p] < now
        b = boxes[p]
        if str(table[b].user) == username and not has_expired and is_picked:
            table[b].expires = time.time() + TICKET_LIFE_SPAN
            extended.append(b)
        else:
            table[b].free = True
    if extended:
        res.robot.send(user, "I'll keep {0} for you for another {1}".format(','.join(extended), humanize_time(TICKET_LIFE_SPAN)))
    else:
        res.robot.send("I'm sorry but all your boxes have been freed already")
    del rem[username]
    robot.put_to_memory('box_list', table)
    robot.put_to_memory('removables', rem)


def box_cleaner_notify_user(items):
    mem = robot.get_from_memory('removables', {})
    for i in items:
        boxes = items[i]['box']
        user = items[i]['user']
        if len(boxes) == 1:
            rem_time = items[i]['expires'][0]
            box = boxes[0]
            msg = "Oowee looks like your box will be removed in {}".format(humanize_time(rem_time))
            robot.send(user.id, msg,
                       attachments=[{'text': "Are you still using {}? (y/n)".format(box),
                                     "fallback": "Are you still using {}? (y/n)".format(box)
                                     }], is_im=True)
            mem[user.name] = {'box': [box], 'expires': [time.time()+rem_time]}
        else:
            msg = "Oowee the following boxes, which you're using, will automatically expire:\n"
            rem_times = items[i]['expires']
            expires2 = []
            now = time.time()
            for j, box in enumerate(boxes):
                msg += '({0}) {1} - {2}'.format(j, box, humanize_time(rem_times[j]))
                expires2.append(now+rem_times[j])
            submsg = "Please enter the indices of the boxes which you're still using separated by commas (1,2,3...)"
            robot.send(user.id, msg,
                       attachments=[{'text': submsg,
                                     "fallback": submsg
                                     }], is_im=True)
            mem[user.name] = {'box': boxes, 'expires': expires2}
    robot.put_to_memory('removables', mem)


def clean_up_boxes(func_call=False):
    if not func_call:
        Timer(REFRESH_RATE, clean_up_boxes).start()
    table = robot.get_from_memory("box_list", {})
    notifiable_users = {}
    for b in table:
        box = table.get(b)
        if box.free:
            continue
        now = time.time()
        if robot.ticket_is_closed(box.ticket) or box.expires <= now:
            table[b].free = True
        elif (box.expires - TICKET_NOTIFY_TIME) <= now:
            notifiable_users[box.user.id] = {'box': [b],
                                             'expires': [box.expires - now],
                                             'user': box.user}
    if notifiable_users:
        box_cleaner_notify_user(notifiable_users)
    robot.put_to_memory("box_list", table)

if __name__ == "__main__":
    try:
        print ("Bot starting...")
        Timer(REFRESH_RATE, clean_up_boxes).start()
        robot.run()
    except Exception as e:
        print(e)
    finally:
        for t in threading.enumerate():
            if isinstance(t, threading._Timer):
                t.cancel()
        robot.shutdown()
