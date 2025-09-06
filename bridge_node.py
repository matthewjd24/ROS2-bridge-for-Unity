import socket
import rclpy
from rclpy.node import Node
from threading import Thread
from std_msgs.msg import String
from std_msgs.msg import Float32
from functools import partial
from rclpy.qos import QoSProfile, QoSReliabilityPolicy

PACKET_SIZE = 4096
HEADER_SIZE = 16
PAYLOAD_SIZE = PACKET_SIZE - HEADER_SIZE
NO_MSG_THRESH = 60

class TCPServer(Node):

    def __init__(self):
        super().__init__('tcp_relay')
        self.topic_publishers = {}  # Dictionary to store topic_name -> publisher

        # When we receive a message from Unity, sometimes it has to be converted to a ROS2 msg
        # This maps topics to message type to enable that conversion
        self.message_type_map = {
            # Example: 'set_joint_angles': Float32MultiArray,
        } 

        self.subscribers = []
        self.tcp_client = None
        self.get_logger().info('TCP server initialized.')
        self.no_msg_count = 0
        
        # Topics we subscribe to will automatically be relayed to unity
        self.add_subscription('my_ros2_topic', String)

    def add_subscription(self, topic_name, message_type):
        # Create and store a subscription for each topic
        subscription = self.create_subscription(
            message_type,
            topic_name,
            partial(self.ros_to_tcp_callback, topic_name),
            10
        )
        self.subscribers.append(subscription)
        self.get_logger().info(f"Subscribed to topic: {topic_name}")

    def ros_to_tcp_callback(self, topic_name, msg): # Callback for messages received on ROS 2 topics
        if not(self.tcp_client):
            if self.no_msg_count >= NO_MSG_THRESH:
                self.no_msg_count = 0
                self.get_logger().warn("No active TCP client. Message not sent.")
            self.no_msg_count += 1
            return
            
        try:
            message = topic_name + ";"
            if topic_name == "tower/status/gps":
                # Parse the message into a string to be passed through the socket
                message += f"{msg.rover_latitude};{msg.rover_longitude}"
            else:
                message += msg.data # handle string messages (not custom message type)
            
            self.tcp_client.sendall(message.encode('utf-8')) # Send the constructed string over TCP
            # self.get_logger().info(f"Sent message over TCP: {message}")
        except Exception as e:
            self.get_logger().error(f"Failed to send message over TCP: {e}")

    def get_or_create_publisher(self, topic_name):
        if topic_name not in self.topic_publishers: # If the publisher doesn't exist yet, create it
            message_type = String # Default to string publisher
            if topic_name in self.message_type_map:
                message_type = self.message_type_map[topic_name] # Use the topic -> message type map to find the type

            self.topic_publishers[topic_name] = self.create_publisher(message_type, topic_name, 10)
            self.get_logger().info(f"Created new publisher for topic: {topic_name}, type: {message_type}")

        return self.topic_publishers[topic_name]

    def handle_client(self, conn, addr):
        # Handles receiving messages from Unity and sending it to a ROS2 topic
        self.get_logger().info(f"Connected by {addr}")
        self.tcp_client = conn

        # Set a short timeout so we can periodically check if rclpy is still running.
        conn.settimeout(1.0)
        try:
            while rclpy.ok():
                try:
                    data = conn.recv(1024)
                except socket.timeout:
                    # No data arrived within 1 second, check if we're still running.
                    continue
                if not data:
                    # Client disconnected.
                    break

                # Process the received message.
                message = data.decode().strip()
                # self.get_logger().info(f"Received from TCP: {message}")

                # Expect the string to be semicolon delimited
                parts = message.split(';')
                if len(parts) < 2:
                    self.get_logger().error("Invalid message format. Expected 'topic_name;message_content'.")
                    continue

                topic_name = parts[0]
                content = ';'.join(parts[1:])

                publisher = self.get_or_create_publisher(topic_name)
                if not publisher:
                    self.get_logger().error("Failed to get or create a publisher")
                    continue

                # Create and publish the message based on its type.
                message_type = self.message_type_map.get(topic_name, String)
                if message_type == String:
                    ros_msg = String()
                    ros_msg.data = content
                # elif message_type == MyCustomMessageType:
                #     ros_msg = MyCustomMessageType()
                #     Create the custom message here
                #     property1 = float(parts[1])
                #     property2 = float(parts[2])
                #     etc. 
                else:
                   self.get_logger().error(f"Unsupported message type for topic: {topic_name}")
                   continue

                publisher.publish(ros_msg)
                #self.get_logger().info(f"Published to {topic_name}: {ros_msg.data}")

        except Exception as e:
            self.get_logger().error(f"Error handling client: {e}")
        finally:
            self.get_logger().info(f"Closing connection with {addr}")
            conn.close()
            self.tcp_client = None

    def start_tcp_server(self, host, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Enable port reuse
            server_socket.bind((host, port))
            server_socket.listen()
            self.get_logger().info(f"Server listening on {host}:{port}...")

            try:
                while rclpy.ok():
                    # Use a timeout to allow periodic checking of rclpy.ok()
                    server_socket.settimeout(1.0)
                    try:
                        conn, addr = server_socket.accept()  # Accept a connection
                        if not rclpy.ok():
                            break
                        self.handle_client(conn, addr)  # Handle the client in the same thread
                    except socket.timeout:
                        continue  # Timeout reached; check rclpy.ok() again
            except Exception as e:
                if rclpy.ok():  # Avoid logging if shutdown has been called
                    self.get_logger().error(f"Error in TCP server: {e}")
            finally:
                if rclpy.ok():
                    self.get_logger().info("Shutting down TCP server.")

shutdown_called = False

def main(args=None):
    global shutdown_called
    rclpy.init(args=args)
    node = TCPServer()

    # Run the TCP server in a separate thread
    tcp_thread_status = Thread(target=node.start_tcp_server, args=('127.0.0.1', 65432))

    tcp_thread_status.start()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if not shutdown_called:
            shutdown_called = True
            node.get_logger().info("Shutting down server...")
            node.destroy_node()

if __name__ == '__main__':
    main()
