# Server -> Receiver
# SR implementation
import socket
import sys
import select
import string
import binascii
import cPickle
import Queue
import heapq
from check import ip_checksum
 
######################
# create packet
######################
def make_packet (sq_num, data, checksum):
  pkt = (sq_num, data, checksum)
  return pkt
  
######################
# extract data
######################
#normal extract - 0
#out of order extra - 1
def extract_data (received_packet, type_of_extract):
  #convert received_packet, which is a string of a tuple back to actual tuple
  if (type_of_extract == 0):
      received_tuple = string.split(received_packet, ',')
      j = 0
      for i in received_tuple:
        i = string.strip(i, '(')
        i = string.strip(i, ')')
        i = string.strip (i) #by default it removes whitespace
        i = string.strip (i, '\'')
        received_tuple[j] = i
        j = j + 1
      #print type(check)
      #print 'checksum is', check, str(received_tuple[2])
      #uni = '\x97\x96'
      #decode = unicodestring.decode("windows-1252")
      #encoded = decode.encode('ascii', 'ignore')
      #print encoded
      #print 'Received tuple is', received_tuple[0], received_tuple[1], received_tuple[2]
      seq_num = received_tuple[0]
      data = received_tuple[1]
      check_sum = received_tuple[2]
  elif (type_of_extract == 1):
      received_packet_str = str(received_packet)
      received_tuple = string.split(received_packet_str, ',')
      j = 0
      for i in received_tuple:
        i = string.strip (i, '"')
        i = string.strip(i, '(')
        i = string.strip(i, ')')
        i = string.strip (i) #by default it removes whitespace
        i = string.strip (i, '"')
        i = string.strip(i, ')')
        i = string.strip (i, '\'')
        received_tuple[j] = i
        #print 'Processed str: ', received_tuple[j]
        j = j + 1
      #print type(check)
      #print 'checksum is', check, str(received_tuple[2])
      #uni = '\x97\x96'
      #decode = unicodestring.decode("windows-1252")
      #encoded = decode.encode('ascii', 'ignore')
      #print encoded
      #print 'Received tuple is', received_tuple[0], received_tuple[1], received_tuple[2]
      seq_num = received_tuple[0]
      data = received_tuple[2]
      check_sum = received_tuple[3]
  return seq_num, data, check_sum
 
#################################
#checksum cmp
#################################
def checksum_cmp (received_content, received_checksum):
  #casting checksum to str by itself is not the same when casting it to str via tuple...
  #when checksum is in tuple and is cast into a string, they are the same
  check = ip_checksum(received_content)
  tuple_pkt = (0,0, check)
  tuple_pkt_str = str(tuple_pkt)
  splice_tuple_pkt = string.split(tuple_pkt_str, ',')
  j = 0
  for i in splice_tuple_pkt:
    i = string.strip(i, '(')
    i = string.strip(i, ')')
    i = string.strip (i) #by default it removes whitespace
    i = string.strip (i, '\'')
    splice_tuple_pkt[j] = i
    j = j + 1
  #print 'computed checksum:', splice_tuple_pkt[2], '\nReceived_checksum:', received_checksum
  if splice_tuple_pkt[2] == received_checksum:
    return 1
  else:
    return 0
 
HOST = ''   # Symbolic name meaning all available interfaces
PORT = 7109 # Arbitrary non-privileged port
packet_sequence_number = 0
# Datagram (udp) socket
try :
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print 'Socket created'
except socket.error, msg :
    print 'Failed to create socket. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
    sys.exit()
 
 
# Bind socket to local host and port
try:
    s.bind((HOST, PORT))
except socket.error , msg:
    print 'Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
    sys.exit()
     
print 'Socket bind complete'
 
#states for SR receiver
states = ['wait']
states_list = list(enumerate(states))
current_state = states_list[0]
 
received_base = 0
packet_received_queue = [] #for out of order packets
window_size = 4
clear_entries = 0
#related variables for select
inputs = [s] #socket
outputs = []
timeout = 0 #when timeout is 0, it basically polls
readable = []
writeable = []
expectional =[]
#now keep talking with the client
while 1:
  if current_state == states_list[0]:
    
    readable, writeable, expectional = select.select(inputs, outputs, inputs, timeout)
    for temp_socket in readable:
      received_data = temp_socket.recvfrom(1024)
      received_packet = received_data[0]
      address = received_data[1]
      print 'Received packet: ', received_packet
      packet_sequence_number, packet_data, packet_checksum = extract_data(received_packet, 0)
      #if the packet sequence number is what we expect then send ACK for it
      #otherwise we send the ACK still, because the sender needs it to move forward
      
      if checksum_cmp (packet_data, packet_checksum):
        if (int(packet_sequence_number) >= received_base) or (int(packet_sequence_number) <= (received_base + window_size -1)):
            #print 'Valid Checksum, sending ACK', received_base
            msg = 'ACK' + packet_sequence_number
            checksum = ip_checksum (msg)
            '''
            This is were we would forward the data up the internet protocl stack to
            the application layer or any intermediate agent between the transport and
            application layer.
            '''
            packet_to_send = make_packet (packet_sequence_number, msg, checksum)
            #send packet
            s.sendto(str(packet_to_send), address)
           
            if (int(packet_sequence_number) == received_base):
                received_base = received_base + 1
                #if there is out of order packets, we want to send them up to application as well if the seq number is sequential to received packet
                if (len(packet_received_queue) > 0):
                    for pkt in packet_received_queue:
                        packet_sequence_number, packet_data, packet_checksum = extract_data(pkt, 1)
                        #we only want to send up consecutive numbers to received base
                        i = 0
                        #print 'Sequence number of buffered packet:', packet_sequence_number
                        #print 'Received Base = ', received_base
                        if int(packet_sequence_number) == received_base:
                            #increment received base accordingly
                            received_base = received_base + 1
                            #pop front of queue
                            #packet_received_queue.get()
                            #send packet upward to application here
                            i = i + 1
                            clear_entries = 1
                    if clear_entries:
                        packet_received_queue= [] #clear out entries
                        clear_entries = 0
            else: #buffer packet
                print 'out of order packet, buffering'
                #insert into priority queue, where the lower sequence number means higher priority
                heapq.heappush(packet_received_queue, (int(packet_sequence_number), received_packet))
                #print 'packet queue is now:', packet_received_queue
        #send ACK for already seen packet, possible it was lost and sender needs it to move on
        elif (int(packet_sequence_number) >= received_base - window_size) or (int(packet_sequence_number) <= (received_base -1)): 
            msg = 'ACK' + packet_sequence_number
            checksum = ip_checksum (msg)
            packet_to_send = make_packet (received_base, msg, checksum)
            #send packet
            s.sendto(str(packet_to_send), address)
      elif not(checksum_cmp(packet_data, packet_checksum)):
          print 'Received corrupted packet, wait for retransmission from sender.'
  else:
    print 'Something went wrong! Current state is', current_state
    break;
s.close()
