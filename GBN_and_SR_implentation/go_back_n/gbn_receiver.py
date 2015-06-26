# Server -> Receiver
# GBN implementation
import socket
import sys
import select
import string
import binascii
import cPickle

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

#states for GBN receiver
states = ['wait']
states_list = list(enumerate(states))
current_state = states_list[0]

delay_ack1 = 0
#packet1_corrput = 0

expected_seq_num = 0
msg = 'ACK' + str (expected_seq_num)
checksum = ip_checksum(msg)
#create packet
packet_to_send = make_packet(str(expected_seq_num), msg, checksum)

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
      packet_sequence_number, packet_data, packet_checksum = extract_data(received_packet)
      #print packet_sequence_number, packet_data, packet_checksum
      #if the packet sequence number is what we expect then send ACK for it
      #otherwise we send the old ACK and let sender retransmit all packets
      #print 'packet sequence number =', packet_sequence_number, '\nExpected sequence number =', expected_seq_num
      if (packet_sequence_number == str(expected_seq_num)) and checksum_cmp (packet_data, packet_checksum):
        #print 'Valid Checksum, sending ACK', expected_seq_num
        msg = 'ACK' + str (expected_seq_num)
        checksum = ip_checksum (msg)
        '''
        This is were we would forward the data up the internet protocl stack to 
        the application layer or any intermediate agent between the transport and
        application layer.
        '''
        packet_to_send = make_packet (expected_seq_num, msg, checksum)
        #send packet
        s.sendto(str(packet_to_send), address)
        expected_seq_num = expected_seq_num + 1
      else: #send the old ACK packet, possible it was lost and sender needs it to move on
        # we have already extracted the data
        #send old ack to sender
        s.sendto(str(packet_to_send), address)
      if not(checksum_cmp(packet_data, packet_checksum)):
          print 'Received corrupted packet, wait for retransmission from sender.'
  else:
    print 'Something went wrong! Current state is', current_state
    break;
s.close()
