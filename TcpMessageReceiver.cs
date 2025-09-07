using UnityEngine;
using System.Collections.Concurrent;

public class TcpMessageReceiver : MonoBehaviour
{
    public static TcpMessageReceiver instance;
    // Thread safe queue since the messages will not arrive on Unity's main thread
    private ConcurrentQueue<string> messageQueue = new ConcurrentQueue<string>();

    void Awake()
    {
        if (instance != null && instance != this) {
            Debug.LogError($"Error - multiple instances of {nameof(TcpMessageReceiver)} have been created");
            return;
        }
        instance = this;
    }

    public void Receive(string data){
        messageQueue.Enqueue(data);
    }

    void Update()
    {
        // Process messages on the main thread
        while (messageQueue.TryDequeue(out string message))
        {
            ProcessMessage(message);
        }
    }

    private void ProcessMessage(string message)
    {
        var parts = message.Split(";");
        if(parts[0] == "/my_topic"){
            // myManagerClass.HandleMessage(message);
        }
        else {
            Debug.Log("Received " + message);
        }

    }
}
