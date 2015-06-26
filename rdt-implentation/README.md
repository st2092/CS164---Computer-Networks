__Reliable Data Transfer (RDT)__

-rdt3.0 sender

  * Account for errors and losses with checksum and timer for retransmission
  * Waits for a "reasonable" amount of time for ACK
      * if does not receive ACK within time duration, resend the packet

-rdt3.0 receiver

  * Same as rdt 2.2 receiver because changes to rdt2.2 sender is the addition of timer for packets. Since addition of a timer can only introduce duplicate packets, it is not necessary to change the receiver.
  
  
__Running the implementation__

* Open 2 seperate terminals
* On one of the terminal run the python script for rdt receiver and the other for rdt sender.
    * example: Type "python \<sender file name>.py" on one terminal and "python \<receiver file name>.py" on the other
* The sender python script will ask for messages to send to the receiver
* The packets receives on both the sender and receiver are output to terminal to show the flow of data transfer

*__IMPORTANT NOTE__: On fresh start of the receiver and sender there are two test scenarios that occurs. Afterwards, packet exchange between the sender and receiver will be normal. The two test scenarios are:
  1. The second packet sent will be corrupted. Upon timeout the sender will resend the packet and receive acknowledgement from receiver.
  2. After receiving the second packet, the receiver will send a delay acknowledgement. This delay period is slightly longer than the timer on the sender side. Once retransmission occurs, the receiver will end up sending a duplicate acknowledgement. Afterwards, transmission of packets functions normally.
