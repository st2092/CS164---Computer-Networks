__Go Back N__

-Sender

  * Can have up to N unacked packets in pipeline
  * Has timer for oldest in-flight unacked packet
      * when timer expires, retransmit all unacked packets

-Receiver
  
  * Only sends accumulative ack
      * Does not ack packet if there is a gap
      
      
__Selective Repeat__

-Sender

  * when data arrives from an application, if the next sequence number is within window, sends packet, start timer for this specific packet, and increment to next sequence number
  * if the timer for a packet expires, resend the packet and restart timer
  * if some packet is ACKed, mark it as ACKed and advance send_base to next unACKed sent packet

-Receiver

  * Initially, set the receive_base sequence number
  * Afterwards, if a packet is received and is not corrupt:
      * if sequence number is between receive_base and receive_base + window_size - 1:
              send ACK and if sequence number equals receive_base, deliver data to app, and deliver consecutive buffered data then
              advance receive_base accordingly
      * otherwise:
               buffer received data
      * if sequence number is between receive_base - window_size and receive_base - 1:
              send ACK
      * if none is true, ignore the packet
