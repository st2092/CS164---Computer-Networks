#client -> sender
import socket   #for sockets
import sys  #for exit
import select
import string
from thread import *

ERROR = -1
LOGIN = 0
SEE_OFFLINE = 1
EDIT_SUBSCRIPTION = 2
POST_MESSAGE = 3
LOG_OUT = 4
HASH_TAG_SEARCH = 5
DISPLAY_REAL_TIME_MSGS = 6
SHOW_FOLLOWERS = 7
user_name = ''
MAX_LENGTH = 140
 
real_time_msgs_buf = []
in_main_menu = False
######################
# create packet
######################
def make_packet (action_num, user, data, current_progress):
    pkt = (action_num, user, data, current_progress)
    return pkt
 
######################
# dispay list
######################
def display_list (list_to_show):
    if (list_to_show[0] == ''):
        print 'None'
        return
    j = 1
    for i in list_to_show:
        print j,')', i
        j = j + 1
    return
 
##############################
# display real time messages
##############################
def display_real_time_msgs (real_time_msgs_buffer):
    #print 'In display real time message function. The buffer content is :'
    #print real_time_msgs_buf
    if (len(real_time_msgs_buffer) > 0):
        print '\nRecent updates from your subscription(s):'
    for msg in real_time_msgs_buffer:
        print msg[0] #source/origin
        print '\t', msg[1] #msg
        print '\t', msg[2] #hashtag(s) if any
    return
 
######################
# display prompt
######################
def display_prompt ():
    print '+----------------------------------------------+'
    print '|       0) Login                               |'
    print '|       1) See Offline Messages                |'
    print '|       2) Edit Subscriptions                  |'
    print '|       3) Post a Message                      |'
    print '|       4) Log out                             |'
    print '|       5) Hashtag Search                      |'
    print '|       7) Display followers                   |'
    print '|    ** enter "back" between any action to     |'
    print '|       go back to menu **                     |'
    print '+----------------------------------------------+'
 
######################
# login action
######################
def login_action (port, host, socket):
    global current_state, states_list
    user = raw_input ('Username: ')
    if (user == 'back'):
        current_state = states_list[0] #go back to menu
        return
    pw = raw_input ('Password: ')
    if (pw == 'back'):
        current_state = states_list[0] #go back to menu
        return
    #create packet
    packet = make_packet (LOGIN, user, pw, -1)
    #send packet
    #print 'Sending packet:', packet, 'to', (host, port)
    socket.sendto (str(packet), (host, port))
    return
 
######################
# log out action
######################
def logout_action (port, host, socket, logout_type):
    '''
    Logout type:
    0 - normal (user logout via actual command)
    1 - other means such as system interrupts (e.g. ctrl-c)
    '''
    #create packet
    packet = make_packet (LOG_OUT, user_name, logout_type, -1)
    #send packet
    #print 'Sending packet:', packet, 'to', (host, port)
    socket.sendto (str(packet), (host, port))
    return
 
##############################
# create offline user msg list
##############################
def print_dictionary (dictionary, type_of_display, specific_username):
    #type of display:
    # 0) all
    # 1) specific user
    i = 1
    if type_of_display == 0:
        for user in dictionary:
            print user
            for msg in dictionary[user]:
                print '\t', msg
                if (i % 2 == 0):
                    print
                i = i + 1
            i = 1
    elif type_of_display == 1:
        print specific_username
        for msg in dictionary[specific_username]:
            print '\t', msg
            if (i % 2 == 0):
                print
            i = i + 1
    return
 
def create_offline_user_msg_dict (list_of_offline_msgs):
    offline_user_dict = {}
    #list format: l[0] = origin, l[1] = msg, l[2] = hashtags
    #             l[3] = origin, l[4] = msg, l[5] = hashtags and so on...
    # Thus, mod 3 of with index incrementing will be right
    # index % 3 = 
    # 0: username
    # 1: msg
    # 2: hashtag(s)
    index = 0
    current_username = ''
    for user_msg in list_of_offline_msgs:
        if (index % 3 == 0) and not(user_msg in offline_user_dict): #if have not seen this username yet add to dict
            offline_user_dict[user_msg] = []
            current_username = user_msg
        elif (index % 3 == 0) and (user_msg in offline_user_dict):
        #key (username) is already in dict then we just append msg + hashtag(s) to list for that key
            current_username = user_msg
        elif (index % 3 == 1): #msg
            offline_user_dict[current_username].append(user_msg)
        elif (index % 3 == 2): #hashtags
            offline_user_dict[current_username].append(user_msg)
        index = index + 1
    return offline_user_dict
 
##############################
# see offline messages action
##############################
def see_offline_msgs_action (port, host, socket):
    global current_state, states_list, real_time_msgs_buf
    if (unread_message_count <= 0):
        print '\nYou have no unread message(s).'
        current_state = states_list[0]
        return
    #initiate see offline messages
    #send init pkt
    see_offline_msgs_init = make_packet (SEE_OFFLINE, user_name, 'see_offline_msgs_init', 1)
    socket.sendto (str(see_offline_msgs_init), (host, port))
     
    #wait for response from server
    #server response will be all the offline msgs since last log off
    #we will do the sorting on client side
    inputs = [socket]
    outputs = []
    timeout = 1
    process_status = 0
    while not(process_status):
        readable, writeable, expectional = select.select(inputs, outputs, inputs, timeout)
        for temp_socket in readable:
            received_data = temp_socket.recvfrom(1024)
            received_packet = received_data[0]
            address = received_data[1]
            #print 'Received packet: ', received_packet
            action, user, data = extract_data(received_packet, 1)
            if (int(action) == DISPLAY_REAL_TIME_MSGS):
                real_time_msgs_buf.append(data)
                continue
            elif (int(action) == SEE_OFFLINE):
                #print 'Data extracted in see offline function:\n', data
                offline_user_dict = create_offline_user_msg_dict (data)
                #print 'Offline user dictionary is:\n', offline_user_dict
                option = ''
                while not(option == 'no'):
                    option = raw_input ('Would you like to see all messages or from a specific subscription? [enter "all" or "specific"]: ')
                    if (option == 'back'):
                        current_state = states_list[0]
                        return
                    if not(option == 'all' or option == 'specific'):
                        option = raw_input ('Invalid option! Please enter "all" or "specific": ')
                        if (option == 'back'):
                            current_state = states_list[0]
                            return
                    if (option == 'all'):
                        print '\nMessages from all your subscriptions: '
                        print_dictionary (offline_user_dict, 0, '')
                    elif (option == 'specific'):
                        print '\nSubscriptions'
                        for key in offline_user_dict.keys():
                            print '    -', key
                        specific_user = raw_input ('Please select a subscription to view: ')
                        while not(specific_user in offline_user_dict):
                            specific_user = raw_input ('Invalid username. Please select an username from list: ')
                            if (specific_user == 'back'):
                                current_state = states_list[0]
                                return
                        print_dictionary (offline_user_dict, 1, specific_user)
                    option = raw_input ('Would you like to view your offline messages again? [yes/no]: ')
                    if (option == 'no'):
                        current_state = states_list[0]
                        process_status = 1
    return
 
###########################
# edit subscription action
###########################
def edit_subscription_action (port, host, socket):
    global current_state, states_list, real_time_msgs_buf
    action = raw_input ('Would you like to add a subscription or drop a subscription? [enter "add" or "drop"]: ')
    if (action == 'back'):
        current_state = states_list[0]
        return
    #ensure input is valid, that is input is either "add" or "drop"
    while not(action == 'add' or action == 'drop'):
        action = raw_input ('Invalid input! Please enter "add" or "drop": ')
        if (action == 'back'):
            current_state = states_list[0]
            return
    process_status = 0 # 0 - incomplete, 1 - subscription process is complete
    '''
    Subscription steps:
    0) send subscription initialization packet indicating add or drop
    1a) (Add) Get username to add (repeat until valid username is entered)
        - receive either NACK or ACK 
    1b) (Drop) Get username to drop from user (ensure it is valid in list passed back from server)
        - Since we ensure username is valid on client side, we'll receive only ACK from server
    '''
    # Current step:
    # 0 - initializing subscription edit
    # 1 - add (prompt for username to add)
    # 2 - add (wait for ACK)
    # 3 - drop (prompt for username from list)
    # 4 - drop (wait for ACK from server indicating removal was successful)
    current_process_step = 0
    #send subscription initialization packet
    sub_init_pkt =  make_packet(EDIT_SUBSCRIPTION, user_name, action, current_process_step)
    if (current_process_step == 0):
        socket.sendto(str(sub_init_pkt), (host, port))
        #update current step accordingly
        if (action == 'add'):
            current_process_step = 1
        elif (action == 'drop'):
            current_process_step = 3
     
    inputs = [socket]
    outputs = []
    timeout = 1
    while not(process_status):
        readable, writeable, expectional = select.select(inputs, outputs, inputs, timeout)
        for temp_socket in readable:
            received_data = temp_socket.recvfrom(1024)
            received_packet = received_data[0]
            address = received_data[1]
            #print 'Received packet: ', received_packet
            action, user, data = extract_data(received_packet, 1)
            if (int(action) == DISPLAY_REAL_TIME_MSGS):
                real_time_msgs_buf.append(data)
                continue
            #check if packet is meant for "me", if not just ignore
            if (int(action) == EDIT_SUBSCRIPTION and user_name == user):
                if (current_process_step == 1): # add (select user to add)
                    user_to_add = raw_input('Please input the user you would like to subscribe to: ')
                    if (user_to_add == 'back'):
                        current_state = states_list[0]
                        return
                    #send pkt
                    add_sub_pkt = make_packet(EDIT_SUBSCRIPTION, user_name, user_to_add, current_process_step)
                    socket.sendto(str(add_sub_pkt), (host, port))
                    current_process_step = 2 # wait for ACK or NACK
                elif (current_process_step == 2): #add (wait for ack)
                    if (data == 'ACK'):
                        print 'Successfully added to subscription!'
                        process_status = 1 # update status to complete
                        success_pkt = make_packet (EDIT_SUBSCRIPTION, user_name, 'successful add', 5)
                        socket.sendto(str(success_pkt), (host, port))
                    elif (data == 'NACK'):
                        user_to_add = raw_input('User does not exist. Please try again: ')
                        if (user_to_add == 'back'):
                            current_state = states_list[0]
                            return
                        #send pkt
                        add_sub_pkt = make_packet(EDIT_SUBSCRIPTION, user_name, user_to_add, current_process_step)
                        socket.sendto(str(add_sub_pkt), (host, port))
                elif (current_process_step == 3): #drop (selection)
                    #display the list of subscriptions received from server
                    print '\nYour currrent subscriptions:'
                    display_list (data)
                    if data[0] == '':
                        current_state = states_list[0]
                        return
                    #prompt user for username (ensure input matches with one entry in the list)
                    user_to_remove = raw_input ('Input username from the list to remove subscription to that user: ')
                    if (user_to_remove == 'back'):
                        current_state = states_list[0]
                        return
                    #while input username is not in the subscription list
                    while (not(data[0] == '') and data.count(user_to_remove) <= 0):
                        user_to_remove = raw_input ('Invalid username. Please try again: ')
                        if (user_to_remove == 'back'):
                            current_state = states_list[0]
                            return
                    #send pkt
                    drop_sub_pkt = make_packet(EDIT_SUBSCRIPTION, user_name, user_to_remove, current_process_step)
                    socket.sendto(str(drop_sub_pkt), (host, port))
                    #update current step
                    current_process_step = 4 #wait for ACK to complete deletion
                elif (current_process_step == 4): #drop (wait for completion)
                    if (data == 'ACK'):
                        process_status = 1 #update status to complete
                        success_pkt = make_packet (EDIT_SUBSCRIPTION, user_name, 'successful drop', 5)
                        socket.sendto(str(success_pkt), (host, port))
    return
 
#######################
# Post message process
#######################
def post_message_process (port, host, socket):
    global current_state, states_list, real_time_msgs_buf
    current_progress = 0
    '''
    current progress:
    1) sent message
    2) sent hashtag(s)
    3) await for ACK
    '''
    msg = raw_input ('Please enter message (up to 140 characters): ')
    while (len(msg) > MAX_LENGTH):
        msg = raw_input ('Message is too long. Please enter message again (up to 140 characters): ')
    current_progress = 1
    if (current_progress == 1):
        #send packet
        msg_pkt = make_packet(POST_MESSAGE, user_name, msg, current_progress)
        socket.sendto(str(msg_pkt), (host, port))
        current_progress = 2
         
    inputs = [socket]
    outputs = []
    timeout = 1
    process_status = 0
    while not(process_status):
        readable, writeable, expectional = select.select(inputs, outputs, inputs, timeout)
        #print 'in while loop....'
        for temp_socket in readable:
            received_data = temp_socket.recvfrom(1024)
            received_packet = received_data[0]
            address = received_data[1]
            #print 'Received packet: ', received_packet
            action, user, data = extract_data(received_packet, 0)
            if (int(action) == DISPLAY_REAL_TIME_MSGS):
                real_time_msgs_buf.append(data)
                continue
            if (current_progress == 2):
                hashtags = raw_input ('Enter hashtag(s) for message (leave blank for none): ')
                # we do not check for validity with hashtag(s)
                hashtag_pkt = make_packet(POST_MESSAGE, user_name, hashtags, current_progress)
                #send packet
                socket.sendto(str(hashtag_pkt), (host, port))
                current_progress = 3
            elif (current_progress == 3):
                if (data == 'hashtag ACK'):
                    process_status = 1
                    #send pkt indicating client knows process is complete
                    pkt = make_packet(POST_MESSAGE, user_name, 'ACK process complete', current_progress)
                    #send packet
                    socket.sendto(str(pkt), (host, port))
    return
 
############################
# hashtag search action
############################
def hashtag_search_action (port, host, socket):
    global current_state, states_list, real_time_msgs_buf
     
    #get from user hashtag search for
    hashtag_query = raw_input ('Input one hashtag to search for (please remember to put "#" first): ')
    while not(hashtag_query[0] == '#'):
        hashtag_query = raw_input ('Invalid hashtag query. Try again(please remember to put "#" first): ')
    #we do not perform validity check for hashtag query
    #if the query is not seen before then server sends back a NACK
     
    #send hashtag query packet
    hashtag_query_pkt = make_packet (HASH_TAG_SEARCH, user_name, hashtag_query, -1)
    socket.sendto (str(hashtag_query_pkt), (host, port))
     
    #wait for reply from server
    inputs = [socket]
    outputs = []
    timeout = 1
    process_status = 0
    while not(process_status):
        readable, writeable, expectional = select.select(inputs, outputs, inputs, timeout)
        for temp_socket in readable:
            received_data = temp_socket.recvfrom(1024)
            received_packet = received_data[0]
            address = received_data[1]
            #print 'Received packet: ', received_packet
            action, user, data = extract_data(received_packet, 0)
            if (int(action)== DISPLAY_REAL_TIME_MSGS):
                real_time_msgs_buf.append(data)
                continue
            if (data == 'NACK'):
                print '\nThere are no record of any messages corresponding to', hashtag_query
                process_status = 1
            else: # data is a list of messages corresponding to hashtag query
                print '\nThe 10 most recent messages corresponding to', hashtag_query
                i = 1
                for msg in data:
                    print '    ', i, ')', msg, '\n'
                    i = i + 1
                process_status = 1
    current_state = states_list[0]
    return
 
############################
# show followers action
############################
def show_follwers_action (port, host, socket):
    global current_state, states_list, real_time_msgs_buf
    #send show follower init pkt
    show_follower_init_pkt = make_packet (SHOW_FOLLOWERS, user_name, 'show followers', -1)
    socket.sendto (str(show_follower_init_pkt), (host, port))
     
    #wait for followers list from server
    inputs = [socket]
    outputs = []
    timeout = 1
    process_status = 0
    while not(process_status):
        readable, writeable, expectional = select.select(inputs, outputs, inputs, timeout)
        for temp_socket in readable:
            received_data = temp_socket.recvfrom(1024)
            received_packet = received_data[0]
            address = received_data[1]
            #print 'Received packet: ', received_packet
            action, user, data = extract_data(received_packet, 0)
            if (int(action)== DISPLAY_REAL_TIME_MSGS):
                real_time_msgs_buf.append(data)
                continue
            elif (data == 'none'):
                print '\nYou have 0 followers.'
                process_status = 1
            else: #data is a list of followers
                print '\nYou have', len(data), 'followers: '
                i = 1
                for follower in data:
                    print '    ', i, ')', follower
                    i = i + 1
                process_status = 1
    current_state = states_list[0]
    return
 
############################
# perform specified action
############################
def perform_action (action, port, host, socket):
    global current_state
    action_num = int(action)
    #print 'In perform_action, action #', action_num
    if action_num == LOGIN:
        #print 'LOGIN'
        login_action(port, host, socket)
    elif action_num == SEE_OFFLINE:
        #print 'SEE_OFFLINE'
        see_offline_msgs_action (port, host, socket)
    elif action_num == EDIT_SUBSCRIPTION:
        #print 'EDIT_SUBSCRIPTION'
        edit_subscription_action(port, host, socket)
    elif action_num == POST_MESSAGE:
        #print 'POST_MESSAGE'
        post_message_process(port, host, socket)
    elif action_num == LOG_OUT:
        #print 'LOG_OUT'
        logout_action(port, host, socket, '0')
    elif action_num == HASH_TAG_SEARCH:
        #print 'HASH_TAG_SEARCH'
        hashtag_search_action (port, host, socket)
    elif action_num == DISPLAY_REAL_TIME_MSGS:
        #print 'DISPLAY_REAL_TIME_MSGS'
        current_state = states_list[0]
    elif action_num == SHOW_FOLLOWERS:
        #print 'SHOW_FOLLOWERS'
        show_follwers_action (port, host, socket)
         
 
######################
# extract data
######################
# type of extraction
# 0) normal (data is just a string)
# normal format: (action #, username, data as a string)
# 1) list (data is a list of strings)
# list format: (action #, username, [a , b, ...])
# 2) tuple (data is a tuple)
# tuple format: (action #, username, [(origin, msg, hashtags),...])
def extract_data (received_packet, type_of_extraction):
    #convert received_packet, which is a string of a tuple back to actual tuple
    received_tuple = string.split(received_packet, ',')
    j = 0
    #notice the # of comma is different for when the data is just a string and a list
    # we can take advantage of this to use different extract methods
    # comma count = 2 is normal, > 2 is list
    comma_count = received_packet.count (',')
    left_bracket_count = received_packet.count('[')
    right_bracket_count = received_packet.count(']')
    left_paren_count = received_packet.count ('(')
    right_paren_count = received_packet.count (')')
    #print 'comma count = ', comma_count
    #normal packet
    if comma_count == 2 and (left_bracket_count + right_bracket_count <= 0):
        for i in received_tuple:
            i = string.strip(i, '(')
            i = string.strip(i, ')')
            i = string.strip (i) #by default it removes whitespace
            i = string.strip (i, '\'')
            received_tuple[j] = i
            j = j + 1
        action_num = received_tuple[0]
        user = received_tuple[1]
        data = received_tuple[2]
        return action_num, user, data
    #tuple packet
    elif comma_count >= 2 and left_bracket_count and right_bracket_count and left_paren_count >= 2 and right_paren_count >=2:
        for i in received_tuple:
            i = string.strip (i)
            #i = string.strip (i, '(')
            i = string.strip (i, ')')
            i = string.strip (i, '[')
            i = string.strip (i, ']')
            i = string.strip (i, '(')
            i = string.strip (i, ')')
            i = string.strip (i) #by default it removes whitespace
            i = string.strip (i, '\'')
            received_tuple[j] = i
            #print 'Received_tuple[j]: ', received_tuple[j]
            j = j + 1
        action_num = received_tuple[0]
        user = received_tuple[1]
        data = received_tuple[2:]
        #print 'Extraction of list is:\n', data
        return action_num, user, data
    #list packet
    elif comma_count >= 2 and left_bracket_count and right_bracket_count:
        for i in received_tuple:
            i = string.strip (i, '(')
            i = string.strip (i, ')')
            i = string.strip (i)
            i = string.strip (i, '[')
            i = string.strip (i, ']')
            i = string.strip (i) #by default it removes whitespace
            i = string.strip (i, '\'')
            received_tuple[j] = i
            #print 'Received_tuple[j]: ', received_tuple[j]
            j = j + 1
        action_num = received_tuple[0]
        user = received_tuple[1]
        data = received_tuple[2:]
        #print 'Extraction of list is:\n', data
        return action_num, user, data
    #real time msg & offline msg
    elif comma_count >=2:
        for i in received_tuple:
            i = string.strip (i)
            i = string.strip (i, '(')
            i = string.strip (i, ')')
            i = string.strip (i, ')')
            i = string.strip (i)
            i = string.strip (i, '\'')
            received_tuple[j] = i
            #print 'Received_tuple[j]: ', received_tuple[j]
            j = j + 1
        action_num = received_tuple[0]
        user = received_tuple[1]
        data = received_tuple[2:]
        #print 'Extraction of tuple is:\n', data
        return action_num, user, data
################################
# real time msgs listen
################################
def real_time_msgs_listen ():
    global s2, in_main_menu
    inputs = [s2] #socket
    outputs = []
    timeout = 0
    while (1):
        while (in_main_menu):
            readable, writeable, expectional = select.select(inputs, outputs, inputs, timeout)
            for temp_socket in readable:
              received_data = temp_socket.recvfrom(1024)
              received_packet = received_data[0]
              address = received_data[1]
              #print 'Received packet: ', received_packet
              action, user, data = extract_data(received_packet, 1)
              #print data
              
              if (int(action) == DISPLAY_REAL_TIME_MSGS):
                  i = 0
                  # i % 3 = 0 username 
                  # i % 3 = 1 msg
                  # i % 3 = 2 hashtag
                  print '\nUpdate(s) from your subscriptions:'
                  for msg in data:
                      if (i % 3 == 0):
                          print msg
                      elif (i % 3 == 1):
                          print '\t', msg
                      elif (i % 3 == 2):
                          print '\t', msg
                      i = i + 1
    return

# create dgram udp socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s2 = socket.socket (socket.AF_INET, socket.SOCK_DGRAM)
    
except socket.error:
    print 'Failed to create socket'
    sys.exit()
  
host = '10.0.0.4';
my_host_name = '';
port = 7109;
port_for_real_time_msg = 7110;

try:
    s2.bind((my_host_name, port_for_real_time_msg))
except socket.error , msg:
    print 'Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
    sys.exit()
#print 'socket2:', s2
#states for client
states = ['wait_for_user', 'wait_for_action_completion']
states_list = list(enumerate(states))
current_state = states_list[0]
#print current_state
unread_message_count = 0 #number of unread messages
#start thread that listens for real time messages
start_new_thread (real_time_msgs_listen, ())
while(1) :
  #wait for user, initial state
  if current_state == states_list[0]:
    display_real_time_msgs (real_time_msgs_buf)
    #clear real time msgs for next set
    real_time_msgs_buf = []
    display_prompt()
    in_main_menu = True
    action = raw_input('Enter action to perform (use 0 - 7): ')
    if action == 'exit':
        break;
    if (user_name == '' and action == '4'): #if not logged in yet and tries to logout ask for another valid input
        while (int(action) == LOG_OUT):
            print 'Cannot perform logout. Please login first.'
            action = raw_input ('Enter "0" to login: ')
    if user_name == '': #has not log in yet
        while not(int(action) == LOGIN):
            #print 'action is', action, 'login number is', LOGIN
            #print type(action), type(LOGIN)
            print 'Action is invalid, please log in first.'
            action = raw_input('Enter action to perform (use 0 - 5): ')
    if not(user_name == '') and action == '0': #if already logged in and trying to log in again
        while (int(action) == LOGIN):
            print 'You are already logged in. Please choose another operation'
            action = raw_input ('Use option 1-5: ')
     
    #transition to next state
    current_state = states_list[1]
    in_main_menu = False
    perform_action (action, port, host, s)
 
  #wait for action completion
  elif current_state == states_list[1]:
    #start timer here, select will block for a time out period if nothing is received
    #otherwise we know we have received something, so move onto checking it is what
    #we want. 
    inputs = [s] #socket
    outputs = []
    timeout = 5
    readable, writeable, expectional = select.select(inputs, outputs, inputs, timeout)
    for temp_socket in readable:
      received_data = temp_socket.recvfrom(1024)
      received_packet = received_data[0]
      address = received_data[1]
      #print 'Received packet: ', received_packet
      action, user, data = extract_data(received_packet, 1)
      action_num = int(action)
      if action_num == LOGIN:
        if (user_name == '' and data[0:3] == 'ACK'):
            user_name = user #update user name to that of user who logged in
            unread_message_count = int(data[3:])
            print '\nLogin successfully!\nWelcome', user_name, 'you have', unread_message_count , 'unread message(s).'
            current_state = states_list[0] #transition back to prompt new action
        elif (data == 'NACK'):
            print 'Username or password is incorrect. Please try again.'
            perform_action (action, port, host, s)
      elif action_num == SEE_OFFLINE:
        #print 'See Offline'
        current_state = states_list[0] #transition back to prompt new action
      elif action_num == EDIT_SUBSCRIPTION:
        #print 'Edit Subscriptions'
        #since we ensure for correctness in edit subscription function itself we can move back to other state
        if (data == 'ACK'):
            current_state = states_list[0] #transition back to prompt new action
      elif action_num == POST_MESSAGE:
        #print 'Post Message'
        #ensure ACK within prior function already, transition back to other state
        current_state = states_list[0] #transition back to prompt new action
      elif action_num == LOG_OUT:
        #print 'Log out'
        if (data == 'ACK'):
            print '\nSuccessfully log off!'
            user_name = '' #reset username to be nobody, now login process is valid again
            current_state = states_list[0] #transition back to prompt new action
      elif action_num == HASH_TAG_SEARCH:
        #print 'Hashtag search'
        current_state = states_list[0] #transition back to prompt new action
      elif action_num == DISPLAY_REAL_TIME_MSGS:
          #print 'Display real time msgs'
          #print data
          real_time_msgs_buf.append(data)
          
  else:
    print 'Something went wrong, current state is', current_state
    break;
