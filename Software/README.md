# BioMechDesignTeam_EMG
Code base for EMG Fabric sub-team on UWaterloo BioMechatronics Design Team

# Brief Introduction
We are currently using ESP-NOW framework for communication. There is a sender and receiver.

Sender:
- Has the MAC address of the receiver.
- Defines the data structure of the message to be sent.

Receiver:
- Must have the same data structure as the sender.

Note:
- When using ESP-NOW, only the following GPIO pins are available to use:
- 32, 33, 34, 35, 36, 37, 38, 39

# ML
There is an colab extension in vscode so we no longer need the web colab
