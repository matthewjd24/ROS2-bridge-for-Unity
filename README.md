# Unity - ROS2 Communication
This repository provides tools for enabling Unity to ROS2 communication, in the hopes of reducing headache for other robotics enthusiasts. I wasn't satisfied with the other solutions I tried for this problem.

## Overview
This solution involves running a ROS2 node on your machine that communicates with a Unity client over a TCP socket. Communication is bidirectional: the node can pass messages from topics to Unity and from Unity to topics. It's split into two parts: 
- A ROS2 node
- The code you will need to use Unity side to communicate with your node

## Limitations
The node currently does not automatically handle custom message types. For a message that's being passed to Unity, the node must check its type and, if it's not a string, encode it as text using a method you must explicitly define. Similarly, if you want your Unity application to send a custom message to a topic, you must send it over the socket as text (JSON, delimiter, etc.) and handle the creation of the message at the node.

## Technologies
- ROS2
- Python
- Unity, C#  