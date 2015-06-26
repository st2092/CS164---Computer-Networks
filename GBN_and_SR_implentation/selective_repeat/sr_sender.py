#client -> sender
#SR implementation
import socket   #for sockets
import sys  #for exit
import select
import cPickle
import string
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
  if splice_tuple_pkt[2] == received_checksum:
    return 1
  else:
    return 0
 
# create dgram udp socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
except socket.error:
    print 'Failed to create socket'
    sys.exit()
 
host = 'localhost';
port = 7109;
flag = 1
copy_of_sent_packet = (0, 0, 0)
 
#states for SR sender
states = ['wait']
states_list = list(enumerate(states))
current_state = states_list[0]
#print current_state
copy_of_packet = (0,0,0)
packet_corrupt = 0
window_size = 4
base = 0
next_seq_num = 0
index = 0 #for indexing the sent packet buffer
max_size = 10000
#create a buffer for sent packets
sent_packets = [(0, 0, 0)]*window_size
#create a table for marking received packets (selective repeat)
mark_off_table = [False]*max_size

ack_count = 0
#buffers for select
inputs = [s] #socket
outputs = []
timeout = 5
readable = []
writeable = []
expectional =[]
timeout_flag = 0
initial_start = 1
while(1) :
  #wait
  if current_state == states_list[0]:
    #received an ACK from receiver
    if (len(readable) > 0):
      #print 'received an ack'
      for temp_socket in readable:
          received_data = temp_socket.recvfrom(1024)
          received_packet = received_data[0]
          address = received_data[1]
          print 'Received packet: ', received_packet
          packet_sequence_number, packet_data, packet_checksum = extract_data(received_packet)
          if checksum_cmp (packet_data, packet_checksum):
              ack_count = ack_count + 1
              if (ack_count == window_size):
                  #stop timer
                  print 'Setting timer off!\n'
                  timeout_flag = 0
                  ack_count = 0
                  base = base + window_size
                  #manually clear out buffers that select write on
                  readable = []
                  writeable = []
                  expectional =[]
                  #flush the buffer for sent packets
                  i = 0
                  for dummy_tuple in sent_packets:
                      sent_packets[i] = (0, 0, 0)
                      i = i + 1
              else:
                #refresh timer
                timeout_flag = 1
              #mark off received packet
              mark_off_table[int(packet_sequence_number)] = True
    #timeout
    elif (len(readable) <= 0 and not(initial_start) and timeout_flag):
        print 'Timeout! Resending all sent UNACKED packets starting from base to base + N'
        # send all the packets that is unACKed
        i = base
        j = 0
        while (i < base + window_size):
            #if corresponding seq is not marked, resend it
            if not(mark_off_table[i]):
                print 'Packet being resent:', sent_packets[j]
                s.sendto(str(sent_packets[j]), (host, port))
                #if ever resend a packet, start timer
                timer_flag = 1
            i = i + 1
            j = j + 1
    elif (next_seq_num < (base + window_size)):
        initial_start = 0
        msg = raw_input('Enter message to send : ')
        if msg == 'exit':
            break;
        checksum = ip_checksum(msg)
        
        if msg == 'lost':
            sequence_number = next_seq_num - 1
        else:
            sequence_number = next_seq_num
        #create packet
        packet_to_send = make_packet(str(sequence_number), msg, checksum)
        
        if msg == 'lost':
            copy_of_packet = make_packet(str(sequence_number+1), msg, checksum)
        else:
            copy_of_packet = packet_to_send
        
        #make a copy of packet for retransmission by adding it to a buffer
        index = next_seq_num % window_size
        sent_packets[index]= copy_of_packet
        print 'copy of packet is', sent_packets[index]
        #send the packet
        #due to nature of SR we cannot just modify the sequence number like GBN to 'fake' a lost packet
        #thus, we must not send this packet but yet make a copy of it for resending at timeout
        if not(msg == 'lost'):
            s.sendto(str(packet_to_send),(host, port))
        #start timer here ideally, but since the select function waits until timeout
        #the program actually stops for the specified time. So we should use select at the end
        #then check if any of the 3 buffers has anything
        if (base == (next_seq_num - window_size + 1)):
            print 'Setting timer on!'
            timeout_flag = 1
        next_seq_num = next_seq_num + 1
    if timeout_flag:
        readable, writeable, expectional = select.select(inputs, outputs, inputs, timeout)
    if (len(readable) > 0):
        timeout_flag = 0
  else:
    print 'Something went wrong, current state is', current_state
    break;
