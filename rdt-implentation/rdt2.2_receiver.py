# Server -> Receiver

import socket
import sys
import select
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

#states for rdt 2.2 receiver
states = ['wait_for_0', 'wait_for_call_1']
states_list = list(enumerate(states))
current_state = states_list[0]

delay_ack1 = 1
#packet1_corrput = 0

#now keep talking with the client
while 1:
  if current_state == states_list[0]:
    inputs = [s] #socket
    outputs = []
    timeout = 0 #when timeout is 0, it basically polls 
    readable, writeable, expectional = select.select(inputs, outputs, inputs, timeout)
    for temp_socket in readable:
      received_data = temp_socket.recvfrom(1024)
      received_packet = received_data[0]
      address = received_data[1]
      print 'Received packet: ', received_packet
      packet_sequence_number, packet_data, packet_checksum = extract_data(received_packet)
      #print packet_sequence_number, packet_data, packet_checksum
      #check if packet has sequence number 1 or 0
      #if 1 then we send an ACK1 back because there was a packet loss and 
      #the sender requires this ACK to make progress. Otherwise, the sender is 'stuck'
      if packet_sequence_number == '1':
        checksum = ip_checksum ('ACK1')
        packet_to_send = make_packet ('1', 'ACK1', checksum)
        #send packet
        s.sendto(str(packet_to_send), address)
      elif packet_sequence_number == '0' and checksum_cmp(packet_data, packet_checksum):
        # we have already extracted the data
        '''
        This is were we would forward the data up the internet protocl stack to 
        the application layer or any intermediate agent between the transport and
        application layer.
        '''
        #send ACK0 to sender
        checksum = ip_checksum ('ACK0')
        packet_to_send = make_packet('0', 'ACK0', checksum)
        #send packet
        s.sendto(str(packet_to_send), address)
        #change current state to wait for 1
        current_state = states_list[1]
      if not(checksum_cmp(packet_data, packet_checksum)):
          print 'Received corrupted packet, wait for retransmission from sender.'
  elif current_state == states_list[1]:
    inputs = [s] #socket
    outputs = []
    timeout = 0 #when timeout is 0, it basically polls 
    readable, writeable, expectional = select.select(inputs, outputs, inputs, timeout)
    for temp_socket in readable:
      received_data = temp_socket.recvfrom(1024)
      received_packet = received_data[0]
      address = received_data[1]
      print 'Received packet: ', received_packet
      packet_sequence_number, packet_data, packet_checksum = extract_data(received_packet)
      #print packet_sequence_number, packet_data, packet_checksum
      #check if packet has sequence number 1 or 0
      #if 0 then we send an ACK0 back because there was a packet loss and 
      #the sender requires this ACK to make progress. Otherwise, the sender is 'stuck'
      if packet_sequence_number == '0':
        checksum = ip_checksum ('ACK0')
        #make packet
        packet_to_send = make_packet ('0', 'ACK0', checksum)
        #send packet
        s.sendto(str(packet_to_send), address)
        
      elif packet_sequence_number == '1' and checksum_cmp(packet_data, packet_checksum):
        # we have already extracted the data
        '''
        This is were we would forward the data up the internet protocl stack to 
        the application layer or any intermediate agent between the transport and
        application layer.
        '''
        #send ACK1 to sender
        checksum = ip_checksum ('ACK1')
        packet_to_send = make_packet('1', 'ACK1', checksum)
        #send packet
        if delay_ack1:
          delay_ack1 = 0
          #packet1_corrput = 1
          inputs = [s] #socket
          outputs = []
          timeout = 6 #this timeout must be longer than on sender side
          readable, writeable, expectional = select.select(inputs, outputs, inputs, timeout)
        '''
        elif packet1_corrput:
          print 'packet is corrupt, wait for retransmission'
          packet1_corrput = 0
          continue
        '''
        s.sendto(str(packet_to_send), address)
        #change current state to wait for 0
        current_state = states_list[0]
      elif not(checksum_cmp(packet_data, packet_checksum)):
          print 'Received corrupted packet, wait for retransmission from sender.'
  else:
    print 'Something went wrong! Current state is', current_state
    break;
s.close()
