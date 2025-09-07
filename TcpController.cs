using UnityEngine;
using System.Net.Sockets;
using System.Text;
using System.Threading;

public class TcpController : MonoBehaviour
{
    // Handles low level communication over a port (65432) with the tcp_relay node
    // Communication is bidirectional so we can send data to the ROS2 ecosystem over this
    //      as well as receive data from it

    public static TcpController instance;
    private TcpClient client;
    private NetworkStream stream;
    private Thread listenThread;
    private bool isRunning;
    public bool disconnected;

    public void Reconnect()
    {
        Start();
    }

    void Start()
    {
        if(instance != null && instance != this) {
            Debug.LogError($"Error - multiple instances of {nameof(TcpController)} have been created");
            return;
        }
        instance = this;
        string server = "127.0.0.1"; // Server IP
        int port = 65432;
        try
        {
            client = new TcpClient(server, port);
            stream = client.GetStream();
            isRunning = true;

            Debug.Log($"Connected to tcp_relay at {server}:{port}");
            disconnected = false;

            // Start a thread to listen for incoming data
            listenThread = new Thread(ListenForData);
            listenThread.IsBackground = true;
            listenThread.Start();
        }
        catch (SocketException e)
        {
            Debug.LogWarning($"Could not connect to server: {e.Message}");
            disconnected = true;
        }
    }

    public void Publish(string message)
    {
        Debug.Log($"Sending: {message}");
        if (client == null || stream == null || !client.Connected)
        {
            Debug.LogWarning("TCP connection is not established. Attempting reconnect.");
            Start();
            if (client == null || stream == null || !client.Connected)
            {
                Debug.LogWarning("Attempted reconnect but still failed. Canceling publish");
                return;
            }
        }

        disconnected = false;
        try
        {
            // Format the message
            byte[] dataToSend = Encoding.ASCII.GetBytes(message);

            // Send the message
            stream.Write(dataToSend, 0, dataToSend.Length);
        }
        catch (System.Exception e)
        {
            Debug.LogWarning($"Error while sending data: {e.Message}");
            disconnected = true;
        }
    }

    private void ListenForData()
    {
        try
        {
            byte[] buffer = new byte[4096];
            while (isRunning && client != null && stream != null)
            {
                // Check if data is available
                if (stream.DataAvailable)
                {
                    int bytesRead = stream.Read(buffer, 0, buffer.Length);
                    if (bytesRead > 0)
                    {
                        string receivedMessage = Encoding.ASCII.GetString(buffer, 0, bytesRead);
                        // Handle the data received from the tcp_relay node
                        TcpMessageReceiver.inst.Receive(receivedMessage);
                    }
                }
            }
        }
        catch (System.Exception e)
        {
            Debug.LogError($"Error while listening for data: {e.Message}");
        }
    }


    void OnDestroy()
    {
        // Cleanup
        isRunning = false;

        if (listenThread != null && listenThread.IsAlive)
        {
            listenThread.Join();
        }

        if (stream != null)
            stream.Close();
        if (client != null)
            client.Close();
    }
}
