#server -> receiver
import socket   #for sockets
import sys  #for exit
import select
import string
from thread import *
 
PW_INDEX = 0
MSG_COUNT_INDEX = 1
MSG_SENT_INDEX = 2
MSG_OFFLINE_INDEX = 3
SUBSCRIPTION_LIST_INDEX = 4
STATUS_INDEX = 5
ADDRESS_INDEX = 6
SUBSCRIBERS_INDEX = 7
 
ERROR = -1
LOGIN = 0
SEE_OFFLINE = 1
EDIT_SUBSCRIPTION = 2
POST_MESSAGE = 3
LOG_OUT = 4
HASH_TAG_SEARCH = 5
DISPLAY_REAL_TIME_MSGS = 6
SHOW_FOLLOWERS = 7
 
message_count = 0
user_count = 0
stored_count = 0
thread_num = 1
hashtags_dict = {}
 
#######################
#initialize dictionary
#######################
def init_dictionary ():
    #hardcoded user and password for now
    user_name = 'user'
    password = 'pw'
    id_num = 1
    default_num_of_users = 3
    dict = {}
    while (id_num <= default_num_of_users):
        new_user = user_name + str(id_num)
        new_pass = password + str(id_num)
        '''
        Value is a list of various information pertaining to the specific user.
        Format: [password, # msgs sent, sent msgs, offline messages, status, address, subscribers list]
        '''
        dict[new_user] = [new_pass, 0, [], [], [], False, [], []]
        id_num = id_num + 1
    return dict
 
####################
# print list
####################
def print_list (list_to_print):
    for i in list_to_print:
        print i
    return
 
######################
# extract data
######################
def extract_data (received_packet):
  #convert received_packet, which is a string of a tuple back to actual tuple
  received_tuple = string.split(received_packet, ',')
  j = 0
   
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
  current_progress = -1
  if len(received_tuple) > 3:
      current_progress = received_tuple[3]
  return action_num, user, data, current_progress
   
#################################
# update hashtag dictionary
#################################
def update_hashtag_dict (data, index_of_most_recent_msg):
    global hashtags_dict
    hashtag_count = data.count('#')
    if (hashtag_count == 1): #only one hashtag
        if not(data in hashtags_dict):
            hashtags_dict[data] = []
            #add msg that correspond to this hashtag
            hashtags_dict[data].append(users_dict[user_name][MSG_SENT_INDEX][index_of_most_recent_msg])
        elif (data in hashtags_dict):
            #add msg that correspond to this hashtag
            hashtags_dict[data].append(users_dict[user_name][MSG_SENT_INDEX][index_of_most_recent_msg])
    elif (hashtag_count > 1): #at least 2 or more hashtags
        #process hashtag string by separating them into individual hashtags
        hashtag_list = string.split (data, '#')
        #print data
        #print hashtag_list
        j = 0
        #print 'hashtag processing...'
        for hashtag in hashtag_list:
            hashtag = string.strip (hashtag) #remove whitespaces
            if not(hashtag == ''):
                hashtag_list[j] = '#' + hashtag
                #print 'hashtag_list[j]: ', hashtag_list[j]
                #if hashtag is not yet in diction add it
                if not (hashtag_list[j] in hashtags_dict):
                    hashtags_dict[hashtag_list[j]] = []
                    #add msg that correspond to this hashtag
                    hashtags_dict[hashtag_list[j]].append(users_dict[user_name][MSG_SENT_INDEX][index_of_most_recent_msg])
                elif (hashtag_list[j] in hashtags_dict):
                    #add msg that correspond to this hashtag
                    hashtags_dict[hashtag_list[j]].append(users_dict[user_name][MSG_SENT_INDEX][index_of_most_recent_msg])
            j = j + 1
    return
 
######################
# create packet
######################
def make_packet (action_num, user, data):
  pkt = (action_num, user, data)
  return pkt
 
##################################
# check for valid user & password
##################################
def validate_login (user, pw):
    if (user in users_dict):
        if (users_dict[user][PW_INDEX] == pw):
            return True
        else:
            return False
    return False
 
###############################
# login process
###############################
def login_process (action_num, user_name, data, address, socket):
    global user_count
    # if username is valid, update the location for user
    if (user_name in users_dict and len(users_dict[user_name][ADDRESS_INDEX]) <= 0):
        users_dict[user_name][ADDRESS_INDEX].append(address [0])
        users_dict[user_name][ADDRESS_INDEX].append(address [1])
        #print 'Updated address for', user_name, '\nAddress is now', users_dict[user_name][ADDRESS_INDEX]
    # if username and password is correct
    if (validate_login (user_name, data)):
        #send valid login ACK back to client & update user status to on, update address
        pkt = make_packet(action_num, user_name, 'ACK'+str(len(users_dict[user_name][MSG_OFFLINE_INDEX])))
        # update address of client, although we updated it outside the address would be invalid if 
        # user input invalid password and uses a different connection to log in.
        # Specifically, when such event occurs the port # will change while the IP address may change.
        # In any case it is safer to update the address again.
        users_dict[user_name][ADDRESS_INDEX][0] = address [0]
        users_dict[user_name][ADDRESS_INDEX][1] = address [1]
        socket.sendto(str(pkt), tuple(users_dict[user_name][ADDRESS_INDEX]))
        #update user status
        users_dict[user_name][STATUS_INDEX] = True #set specific user to online status (all real time subscribed messages will be sent instead of stored on offline buffer)
        user_count = user_count + 1
    else:
        #send NACK back to client
        pkt = make_packet(action_num, user_name, 'NACK')
        socket.sendto(str(pkt), tuple(address))
    return
 
###############################
# logout process
###############################
def logout_process (action_num, user_name, data, address, socket):
    global user_count, stored_count
    #mark user as offline
    users_dict[user_name][STATUS_INDEX] = False
    user_count = user_count - 1
    #print user_name, 'status is now', users_dict[user_name][STATUS_INDEX]
    #before flushing offline msgs for user update stored_count
    stored_count = stored_count - len(users_dict[user_name][MSG_OFFLINE_INDEX])
     # flush offline msgs for specific user
    users_dict[user_name][MSG_OFFLINE_INDEX] = []
    #send ACK back to client
    pkt = make_packet(action_num, user_name, 'ACK')
    socket.sendto(str(pkt), tuple(users_dict[user_name][ADDRESS_INDEX]))
    return
#############################
# see offline msgs process
#############################
def get_key(item):
    return item[0]
def see_offline_msgs_process(action_num, user_name, data, address, socket):
    #send pkt with all of user's offline msgs
    offline_msgs_pkt = make_packet(action_num, user_name, sorted(users_dict[user_name][MSG_OFFLINE_INDEX], key=get_key))
    socket.sendto(str(offline_msgs_pkt), tuple(users_dict[user_name][ADDRESS_INDEX]))
    return
###############################
# Edit subscriptions process
###############################
def edit_subscription_process (action_num, user_name, data, address, socket, current_progress):
    #data is either "add" or "drop"
    #current progress:
    # 0-add) Send something back to client to indicate server is ready 
    # 0-drop) send user's subscription list
    # 1 & 2) add (update user's subscription list with specified username then ACK or NACK is invalid)
    # 3 & 4) drop (update user's subscription list then ACK *client ensures correctness of username*)
    '''
    #current_progress = 0
    if (data == 'add'):
        #current_progress = 1
    elif (data == 'drop'):
        #current_progress = 3
    '''
    process_complete = False
    #if current_progress is 0, send corresponding packet back
    if (current_progress == 0):
        if (data == 'add'):
            #print 'In add state, current_progress:', current_progress
            #send packet indicating ready to receive
            add_sub_pkt = make_packet(action_num, user_name, 'Ready for updating subscription list')
            socket.sendto(str(add_sub_pkt), tuple (users_dict[user_name][ADDRESS_INDEX]))
        elif (data == 'drop'):
            #print 'In drop state, current_progress:', current_progress
            #send packet indicating ready to receive
            drop_sub_pkt = make_packet(action_num, user_name, users_dict[user_name][SUBSCRIPTION_LIST_INDEX])
            socket.sendto(str(drop_sub_pkt), tuple (users_dict[user_name][ADDRESS_INDEX]))
            #print 'Drop_sub_pkt looks like\n', str(drop_sub_pkt)
    elif (current_progress == 1 or current_progress == 2):
        #print 'In add state, current_progress:', current_progress
        if (not(user_name == data) and data in users_dict):
            #update user's subscription list
            #print 'Updating', user_name, '\'s subscription list by adding subscription to', data
            #we do not want repetition in subscription list
            if (users_dict[user_name][SUBSCRIPTION_LIST_INDEX].count(data) < 1):
                users_dict[user_name][SUBSCRIPTION_LIST_INDEX].append(data)
            #update subscriber list of user I just subscribed to to include me
            if (users_dict[data][SUBSCRIBERS_INDEX].count(user_name) < 1):
                users_dict[data][SUBSCRIBERS_INDEX].append(user_name)
            #print user_name, 'subscription list is now: \n', users_dict[user_name][SUBSCRIPTION_LIST_INDEX]
            #print 'Subscriber list of', data, 'is now:\n', users_dict[data][SUBSCRIBERS_INDEX]
            #send ACK
            ack_pkt = make_packet (action_num, user_name, 'ACK')
            socket.sendto(str(ack_pkt), tuple(users_dict[user_name][ADDRESS_INDEX]))
            process_complete = True # completion
        else: #user that client wishes to subscribe to does not exist
            #send NACK
            nack_pkt = make_packet (action_num, user_name, 'NACK')
            socket.sendto(str(nack_pkt), tuple(users_dict[user_name][ADDRESS_INDEX]))
    # if drop then we send a packet back with list of subscribers belonging to the specific user
    elif (current_progress == 3 or current_progress == 4):
        #print 'In drop state, current_progress:', current_progress
        if (not(user_name == data) and data in users_dict):
            #print 'Updating', user_name, '\'s subscription list by removing subscription to', data
            #make sure that specified subscription is really on list
            if (users_dict[user_name][SUBSCRIPTION_LIST_INDEX].count(data) >= 1):
                users_dict[user_name][SUBSCRIPTION_LIST_INDEX].remove(data)
                 
            #update subscriber list of user I just unsubscribed from
            if (users_dict[data][SUBSCRIBERS_INDEX].count(user_name) >= 1):
                users_dict[data][SUBSCRIBERS_INDEX].remove(user_name)
            #print user_name, 'subscription list is now: \n', users_dict[user_name][SUBSCRIPTION_LIST_INDEX]
            #print 'Subscriber list of', data, 'is now:\n', users_dict[data][SUBSCRIBERS_INDEX]
            #send ACK
            ack_pkt = make_packet (action_num, user_name, 'ACK')
            socket.sendto(str(ack_pkt), tuple(users_dict[user_name][ADDRESS_INDEX]))
            process_complete = True # completion
        else:
            #send NACK, but if no subscription then ACK
            #if user's subscription list has at least 1 entry
            if (len(users_dict[user_name][SUBSCRIPTION_LIST_INDEX]) > 0):
                nack_pkt = make_packet (action_num, user_name, 'NACK')
                socket.sendto(str(nack_pkt), tuple(users_dict[user_name][ADDRESS_INDEX]))
            else: #just ACK for now so client can move on (the payload can be anything)
                ack_pkt = make_packet (action_num, user_name, 'ACK')
                socket.sendto(str(ack_pkt), tuple(users_dict[user_name][ADDRESS_INDEX]))
                process_complete = True # completion
    elif (current_progress == 5):
        # current_progress can only be 5 if no issues had occur
        ack_pkt = make_packet (action_num, user_name, 'ACK')
        socket.sendto(str(ack_pkt), tuple(users_dict[user_name][ADDRESS_INDEX]))
    return
 
###############################
# post message process
###############################
def post_message_process (action_num, user_name, data, address, socket, progress):
    global message_count, hashtags_dict, stored_count
    '''
    progress:
    1) received message
    2) received hashtag
    3) Indicate to client post message was successful
    '''
    if (progress == 1):
        if (user_name in users_dict):
            users_dict[user_name][MSG_SENT_INDEX].append(data)
            users_dict[user_name][MSG_COUNT_INDEX] = users_dict[user_name][MSG_COUNT_INDEX] + 1
            message_count = message_count + 1
            #send ACK for received msg okay
            received_ok_pkt = make_packet (action_num, user_name, 'Received message OKAY')
            socket.sendto(str(received_ok_pkt), tuple(users_dict[user_name][ADDRESS_INDEX]))
    elif (progress == 2):
        if (user_name in users_dict):
            users_dict[user_name][MSG_SENT_INDEX].append(data)
            #print user_name, 'sent massage is now:'
            #print_list (users_dict[user_name][MSG_SENT_INDEX])
            #send ACK for received hashtag(s) okay
            received_ok_pkt = make_packet (action_num, user_name,'hashtag ACK')
            socket.sendto(str(received_ok_pkt), tuple(users_dict[user_name][ADDRESS_INDEX]))
            index_of_most_recent_msg = len(users_dict[user_name][MSG_SENT_INDEX]) - 2 # 2 because entry is always in pair (msg then hashtag)
            #update hashtag dictionary 
            update_hashtag_dict(data, index_of_most_recent_msg)
            #print hashtag dict to verify...
            #for key in hashtags_dict.keys():
             #   print key, ':', hashtags_dict[key]
            #for every subscriber of this user, we send them a copy of msg w/hashtag(s)
            for user in users_dict[user_name][SUBSCRIBERS_INDEX]:
                #msg_with_hash = user_name + ':' + users_dict[user_name][MSG_SENT_INDEX][index_of_most_recent_msg] + ',' + users_dict[user_name][MSG_SENT_INDEX][index_of_most_recent_msg+1]
                #print 'message with hash combine:', msg_with_hash
                #if this subscriber is online
                #format: (username of msg origin, msg, hashtag(s))
                msg_with_hash = (user_name, users_dict[user_name][MSG_SENT_INDEX][index_of_most_recent_msg], users_dict[user_name][MSG_SENT_INDEX][index_of_most_recent_msg+1])
                #print str(msg_with_hash)
                if (users_dict[user][STATUS_INDEX]):
                    #send packet
                    #print 'Sending message from', user_name, 'to subscriber', user
                    pkt = make_packet (DISPLAY_REAL_TIME_MSGS, user_name, msg_with_hash)
                    tuple_addr = (users_dict[user][ADDRESS_INDEX][0], port_for_real_time_msg)
                    #print 'Sending real time message to', user, 'at address:' , tuple_addr
                    socket.sendto(str(pkt), tuple_addr)
                else: #subscriber is offline
                    #print user, 'is offline, adding into their offline message buffer.'
                    users_dict[user][MSG_OFFLINE_INDEX].append(msg_with_hash)
                    stored_count = stored_count + 1
    elif (progress == 3):
        #send ACK for received hashtag(s) okay
        ack_pkt = make_packet (action_num, user_name,'ACK')
        socket.sendto(str(ack_pkt), tuple(users_dict[user_name][ADDRESS_INDEX]))
    return
###############################
# hashtag search process
###############################
def hashtag_search_process (action_num, user_name, hashtag_query, address, socket):
    # The server keeps a running hashtag dictionary so if the data (hash query)
    # is in the dictionary we just check if there are more than 10 msgs corresponding to that
    # hash query. If not just send back to client entire list of msgs, otherwise adjust
    # accordingly to end just the last 10 msgs
    if (hashtag_query in hashtags_dict):
        #if there are 10 or less msgs corresponding to the query hashtag, just send them back to client
        if (len(hashtags_dict[hashtag_query]) <= 10):
            msgs_pkt = make_packet(action_num, user_name, hashtags_dict[hashtag_query])
            socket.sendto(str(msgs_pkt), tuple(users_dict[user_name][ADDRESS_INDEX]))
        else: # there must be more than 10 msgs corresponding to query hashtag
            index_of_tenth_previous_msgs = len(hashtags_dict[hashtag_query]) - 10 #index of the 10th previous msg with query hashtag
            #send the 10 latest msgs corresponding to query hashtag
            msgs_pkt = make_packet (action_num, user_name, hashtags_dict[hashtag_query][index_of_tenth_previous_msgs:])
            socket.sendto(str(msgs_pkt), tuple(users_dict[user_name][ADDRESS_INDEX]))
    else:
        #send pkt back to client indicating that query hashtag has no corresponding messages
        pkt = make_packet (action_num, user_name, 'NACK')
        socket.sendto(str(pkt), tuple(users_dict[user_name][ADDRESS_INDEX]))
    return
 
###############################
# show followers process
###############################
def show_followers_process (action_num, user_name, data, address, socket):
    #make sure user_name is valid and follower list has at least 1 follower
    if (user_name in users_dict and len(users_dict[user_name][SUBSCRIBERS_INDEX])):
        #send pkt to client with user_name's subscribers/followers  as payload
        followers_pkt = make_packet(action_num, user_name, users_dict[user_name][SUBSCRIBERS_INDEX])
        socket.sendto(str(followers_pkt), tuple(users_dict[user_name][ADDRESS_INDEX]))
    elif (len(users_dict[user_name][SUBSCRIBERS_INDEX]) <= 0): 
        #send pkt to client with user_name's follower list being 'none'
        followers_pkt = make_packet (action_num, user_name, 'none')
        socket.sendto(str(followers_pkt), tuple (users_dict[user_name][ADDRESS_INDEX]))
         
###############################
# receiver thread action
###############################
def receiver_thread_action(socket):
    try:
        inputs = [socket]
        outputs = []
        timeout = 0 # when timeout is 0, it just polls
        i = 0
        while (1):
            i = i + 1
            readable, writeable, expectional = select.select(inputs, outputs, inputs, timeout)
            for temp_socket in readable:
                #print 'receiver_thread_action iteration', i 
                received_data = temp_socket.recvfrom(1024)
                received_packet = received_data[0]
                address = received_data[1]
                #print 'Received packet: ', received_packet, 'from address', address
                action, user_name, data, progress = extract_data(received_packet)
                action_num = int(action)
                progress_num = int(progress)
                #create a thread to take care of the client's need
                start_new_thread(sender_thread_action, (action_num, user_name, data, address, socket, progress_num))
    except Exception:
        import traceback
        print traceback.format_exc()
     
######################
# sender thread action
######################
def sender_thread_action (action_num, user_name, data, address, socket, progress, thread_num):
    #print 'I am sender thread #', thread_num
    #thread_num = thread_num + 1
    if action_num == LOGIN:
        login_process(action_num, user_name, data, address, socket)
    elif action_num == SEE_OFFLINE:
        #print 'See offline'
        see_offline_msgs_process(action_num, user_name, data, address, socket)
    elif action_num == EDIT_SUBSCRIPTION:
        #print 'Edit subscription'
        edit_subscription_process(action_num, user_name, data, address, socket, progress)
    elif action_num == POST_MESSAGE:
        #print 'Post message'
        post_message_process(action_num, user_name, data, address, socket, progress)
    elif action_num == LOG_OUT:
        #print 'Log out'
        logout_process(action_num, user_name, data, address, socket)
    elif action_num == HASH_TAG_SEARCH:
        #print 'Hashtag search'
        hashtag_search_process (action_num, user_name, data, address, socket)
    elif action_num == SHOW_FOLLOWERS:
        #print 'Show followers'
        show_followers_process (action_num, user_name, data, address, socket)
    #print 'Sender thread ending'
    #print 'thread #', thread_num, 'ending.'
    return
 
##################################
# prompt administrative options
##################################
def prompt_admin_options():
    print '+--------------------------------------------------------------------------+'
    print '|     Type the following to activate administrative commands:              |'
    print '|          "messagecount": display the number of messages received since   |'
    print '|                          server was activated                            |'
    print '|                                                                          |'
    print '|          "usercount": display the current number of users logged in      |'
    print '|                                                                          |'
    print '|          "storedcount": display the number of messages that have been    |'
    print '|                         received but not yet delivered                   |'
    print '|                                                                          |'
    print '|          "newuser": permanently add a new username and password to       |'
    print '|                     current list of user accounts                        |'
    print '+--------------------------------------------------------------------------+'
    return
##################################
# add to dictionary
##################################
def add_to_dict (username):
    global users_dict
    if not(username in users_dict):
        pw = raw_input ('Please input password: ')
        #add user and password into users dictionary
        users_dict[username] = [pw, 0, [], [], [], False, [], []]
        print username, 'successfully added!'
    elif (username in users_dict):
        user = username
        while (user in users_dict):
            user = raw_input ('Username already exist! Try another username: ')
        pw = raw_input ('Please input password: ')
        #add user and password into users dictionary
        users_dict[user] = [pw, 0, [], [], [], False, [], []]
        print user, 'successfully added!'
    return
 
##################################
# admin command action
##################################
def admin_command_action(admin_command):
    if (admin_command == 'messagecount'):
        print '\nThe server has received', message_count, 'messages since activation.'
    elif (admin_command == 'usercount'):
        print '\nThere are', user_count, 'users logged in at the moment.'
    elif (admin_command == 'storedcount'):
        print '\nThere are', stored_count, 'messages stored at the moment.'
    elif (admin_command == 'newuser'):
        user = raw_input('Enter new user''s username: ')
        add_to_dict (user)
    return
 
##################################
# thread action for admin command
##################################
def admin_command_thread ():
    while (1):
        prompt_admin_options()
        admin_command = raw_input('')
        while not(admin_command == 'messagecount' or admin_command == 'usercount' or admin_command == 'storedcount' or admin_command == 'newuser'):
            admin_command = raw_input('Invalid command. Try again: ')
        admin_command_action (admin_command)
    return
 
# create dgram udp socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #s2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
except socket.error:
    print 'Failed to create socket'
    sys.exit()
  
host = '';
port = 7109;
port_for_real_time_msg = 7110;

# Bind socket to local host and port
try:
    s.bind((host, port))
    #s2.bind((host, port_for_real_time_msg))
except socket.error , msg:
    print 'Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
    sys.exit()
print 'Socket bind complete'
 
#initialize dictionary
users_dict = init_dictionary()
#print 'Initialization of dictionary complete! Here is the content\n', users_dict
 
#initialize thread for admin command
start_new_thread (admin_command_thread, ())
#main thread handles the receiving
try:
    inputs = [s] #socket
    outputs = []
    timeout = 0 # when timeout is 0, it just polls
    while (1):
        readable, writeable, expectional = select.select(inputs, outputs, inputs, timeout)
        for temp_socket in readable:
            #print 'receiver_thread_action iteration', i 
            received_data = temp_socket.recvfrom(1024)
            received_packet = received_data[0]
            address = received_data[1]
            #print 'Received packet: ', received_packet, 'from address', address
            action, user_name, data, progress = extract_data(received_packet)
            action_num = int(action)
            progress_num = int(progress)
            #create a thread to take care of the client's need
            start_new_thread(sender_thread_action, (action_num, user_name, data, address, s, progress_num, thread_num))
            thread_num = thread_num + 1
except Exception:
    import traceback
    print traceback.format_exc()
