#client -> sender
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

#states for rdt 3.0 sender
states = ['wait_for_call_0', 'wait_for_ACK0)', 'wait_for_call_1', 'wait_for_ACK1']
states_list = list(enumerate(states))
current_state = states_list[0]
#print current_state
packet1_corrupt = 1

while(1) :
  #wait for call 0, initial state
  if current_state == states_list[0]:
    msg = raw_input('Enter message to send : ')
    if msg == 'exit':
        break;
    checksum = ip_checksum(msg)
    #print 'Checksum is', str(checksum)
    #print 'checksum is', checksum
    #create packet
    packet_to_send = make_packet('0', msg, checksum)
    
    #make a copy of packet for retransmission
    copy_of_sent_packet = packet_to_send
    print 'copy of packet is', copy_of_sent_packet
    #send the packet
    s.sendto(str(packet_to_send),(host, port))
    #change to next state
    current_state = states_list[1]
    #print current_state
  
  #wait for ACK0
  elif current_state == states_list[1]:
    #start timer here, select will block for a time out period if nothing is received
    #otherwise we know we have received something, so move onto checking it is what
    #we want. If so move to next state, otherwise let retransmission handle the problem
    inputs = [s] #socket
    outputs = []
    timeout = 5
    readable, writeable, expectional = select.select(inputs, outputs, inputs, timeout)
    for temp_socket in readable:
      received_data = temp_socket.recvfrom(1024)
      received_packet = received_data[0]
      address = received_data[1]
      print 'Received packet: ', received_packet
      packet_sequence_number, packet_data, packet_checksum = extract_data(received_packet)
      #print packet_sequence_number, packet_data, packet_checksum
      #check if packet is ACK0, if so move to next state
      #we would check for corrupt ACK as well, but for purpose of lab, we are omitting it
      if packet_data == 'ACK0' and packet_sequence_number == '0':
        current_state = states_list[2]
      #if checksum is valid move to next state
    #retransmission, if all returned list is empty from select
    if len(readable) <= 0:
      print 'Retransmitting packet'
      s.sendto(str(copy_of_sent_packet),(host, port))
      
  #wait for call 1
  elif current_state == states_list[2]:
    msg = raw_input('Enter message to send : ')
    if msg == 'exit':
        break;
    checksum = ip_checksum(msg)
    if packet1_corrupt:
        packet1_corrupt = 0
        #make a copy of packet for retransmission
        copy_of_sent_packet = make_packet('1', msg, checksum)
        checksum = checksum + '3' #modify the checksum in any manner to reflect corruption
        #create packet
        packet_to_send = make_packet('1', msg, checksum)
        print 'copy of packet is', packet_to_send
    elif not(packet1_corrupt):
        #create packet
        packet_to_send = make_packet('1', msg, checksum)
        #make a copy of packet for retransmission
        copy_of_sent_packet = packet_to_send
        print 'copy of packet is', copy_of_sent_packet
    #send the packet
    s.sendto(str(packet_to_send),(host, port))
    #change to next state
    current_state = states_list[3]
    #print current_state
    
  #wait for ACK1
  elif current_state == states_list[3]:
    #start timer here, select will block for a time out period if nothing is received
    #otherwise we know we have received something, so move onto checking it is what
    #we want. If so move to next state, otherwise let retransmission handle the problem
    inputs = [s] #socket
    outputs = []
    timeout = 5
    readable, writeable, expectional = select.select(inputs, outputs, inputs, timeout)
    #check for corruption with checksum
    for temp_socket in readable:
        received_data = temp_socket.recvfrom(1024)
        received_packet = received_data[0]
        address = received_data[1]
        print 'Received packet: ', received_packet
        packet_sequence_number, packet_data, packet_checksum = extract_data(received_packet)
        #print packet_sequence_number, packet_data, packet_checksum
        #check if packet is ACK1, if so move to next state
        if packet_data == 'ACK1' and packet_sequence_number == '1':
          current_state = states_list[0]
        #if checksum is valid move to next state
        
    #retransmission, if all returned list is empty from select
    if len(readable) <= 0:
      print 'Retransmitting packet'
      s.sendto(str(copy_of_sent_packet),(host, port))
      
  else:
    print 'Something went wrong, current state is', current_state
    break;
