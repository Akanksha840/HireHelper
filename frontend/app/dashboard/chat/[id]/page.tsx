'use client';

import { useState, useEffect, useRef } from 'react';
import { useParams } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { getStoredToken } from '@/lib/auth';

interface Message {
  id: string;
  sender_id: string;
  content: string;
  timestamp: string;
  sender_name: string;
}

interface ChatData {
  id: string;
  task_request_id: string;
  messages: Message[];
}

export default function ChatPage() {
  const { id: taskRequestId } = useParams();

  const [chat, setChat] = useState<ChatData | null>(null);
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isInCall, setIsInCall] = useState(false);
  const [callId, setCallId] = useState<string | null>(null);

  // FIXED TOKEN HANDLING
  const [token, setToken] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const localVideoRef = useRef<HTMLVideoElement>(null);
  const remoteVideoRef = useRef<HTMLVideoElement>(null);
  const peerConnectionRef = useRef<RTCPeerConnection | null>(null);

  // LOAD TOKEN SAFELY FROM localStorage OR sessionStorage
  useEffect(() => {
    const storedToken = getStoredToken();

    setToken(storedToken);
    if (!storedToken) {
      setIsLoading(false);
    }
  }, []);

  // FETCH CHAT ONLY AFTER TOKEN EXISTS
  useEffect(() => {
    if (taskRequestId && token) {
      fetchChat();
    }
  }, [taskRequestId, token]);

  // CONNECT WEBSOCKET
  useEffect(() => {
    if (chat && token) {
      connectWebSocket();
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [chat, token]);

  // AUTO SCROLL
  useEffect(() => {
    scrollToBottom();
  }, [chat?.messages]);

  const fetchChat = async () => {
    if (!token) return;

    try {
      setIsLoading(true);

      const response = await fetch(
        `http://localhost:8000/api/chat/${taskRequestId}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setChat(data);
      } else {
        console.error('Failed to fetch chat');
      }
    } catch (error) {
      console.error('Error fetching chat:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const connectWebSocket = () => {
    if (!chat || !token) return;

    // CLOSE EXISTING SOCKET
    if (wsRef.current) {
      wsRef.current.close();
    }

    const ws = new WebSocket(
      `ws://localhost:8000/api/chat/ws/${taskRequestId}?token=${token}`
    );

    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      const messageData = JSON.parse(event.data);

      setChat((prev) =>
        prev
          ? {
              ...prev,
              messages: [...prev.messages, messageData],
            }
          : null
      );
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  };

  const sendMessage = async () => {
    if (!message.trim() || !chat || !token) return;

    try {
      const response = await fetch(
        `http://localhost:8000/api/chat/${taskRequestId}/messages`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            content: message,
          }),
        }
      );

      if (response.ok) {
        setMessage('');
      } else {
        console.error('Failed to send message');
      }
    } catch (error) {
      console.error('Error sending message:', error);
    }
  };

  const startCall = async () => {
    if (!token || !chat) return;

    try {
      const response = await fetch('http://localhost:8000/api/calls/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          chat_id: chat.id,
        }),
      });

      if (response.ok) {
        const callData = await response.json();

        setCallId(callData.id);
        setIsInCall(true);

        initializeWebRTC(callData.id);
      }
    } catch (error) {
      console.error('Error starting call:', error);
    }
  };

  const initializeWebRTC = async (callId: string) => {
    if (!token) return;

    try {
      const configuration = {
        iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
      };

      peerConnectionRef.current =
        new RTCPeerConnection(configuration);

      // GET USER MEDIA
      const stream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: true,
      });

      if (localVideoRef.current) {
        localVideoRef.current.srcObject = stream;
      }

      stream.getTracks().forEach((track) => {
        peerConnectionRef.current?.addTrack(track, stream);
      });

      // HANDLE REMOTE STREAM
      peerConnectionRef.current.ontrack = (event) => {
        if (remoteVideoRef.current) {
          remoteVideoRef.current.srcObject = event.streams[0];
        }
      };

      // SIGNALING WEBSOCKET
      const signalingWs = new WebSocket(
        `ws://localhost:8000/api/calls/ws/${callId}?token=${token}`
      );

      peerConnectionRef.current.onicecandidate = (event) => {
        if (event.candidate) {
          signalingWs.send(
            JSON.stringify({
              type: 'ice-candidate',
              data: event.candidate,
            })
          );
        }
      };

      signalingWs.onmessage = async (event) => {
        const signal = JSON.parse(event.data);

        if (signal.type === 'offer') {
          await peerConnectionRef.current?.setRemoteDescription(
            new RTCSessionDescription(signal.data)
          );

          const answer =
            await peerConnectionRef.current?.createAnswer();

          if (answer) {
            await peerConnectionRef.current?.setLocalDescription(
              answer
            );

            signalingWs.send(
              JSON.stringify({
                type: 'answer',
                data: answer,
              })
            );
          }
        } else if (signal.type === 'answer') {
          await peerConnectionRef.current?.setRemoteDescription(
            new RTCSessionDescription(signal.data)
          );
        } else if (signal.type === 'ice-candidate') {
          await peerConnectionRef.current?.addIceCandidate(
            new RTCIceCandidate(signal.data)
          );
        }
      };

      // CREATE OFFER
      const offer =
        await peerConnectionRef.current.createOffer();

      await peerConnectionRef.current.setLocalDescription(
        offer
      );

      signalingWs.send(
        JSON.stringify({
          type: 'offer',
          data: offer,
        })
      );
    } catch (error) {
      console.error('WebRTC initialization error:', error);
    }
  };

  const endCall = async () => {
    if (!token) return;

    try {
      if (callId) {
        await fetch(
          `http://localhost:8000/api/calls/${callId}/status`,
          {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              status: 'ended',
            }),
          }
        );
      }

      // CLOSE PEER CONNECTION
      if (peerConnectionRef.current) {
        peerConnectionRef.current.close();
        peerConnectionRef.current = null;
      }

      // STOP LOCAL STREAM
      if (localVideoRef.current?.srcObject) {
        (
          localVideoRef.current.srcObject as MediaStream
        )
          .getTracks()
          .forEach((track) => track.stop());
      }

      setIsInCall(false);
      setCallId(null);
    } catch (error) {
      console.error('Error ending call:', error);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({
      behavior: 'smooth',
    });
  };

  // LOADING STATE
  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        Loading chat...
      </div>
    );
  }

  // NO CHAT FOUND
  if (!chat) {
    return (
      <div className="flex justify-center items-center h-64">
        Chat not available
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      {/* HEADER */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Chat</h1>

        {!isInCall ? (
          <Button
            onClick={startCall}
            className="bg-green-600 hover:bg-green-700"
          >
            Start Call
          </Button>
        ) : (
          <Button
            onClick={endCall}
            className="bg-red-600 hover:bg-red-700"
          >
            End Call
          </Button>
        )}
      </div>

      {/* VIDEO CALL UI */}
      {isInCall && (
        <Card className="mb-6 p-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <h3 className="text-lg font-semibold mb-2">
                You
              </h3>

              <video
                ref={localVideoRef}
                autoPlay
                muted
                playsInline
                className="w-full h-48 bg-gray-200 rounded"
              />
            </div>

            <div>
              <h3 className="text-lg font-semibold mb-2">
                Other Person
              </h3>

              <video
                ref={remoteVideoRef}
                autoPlay
                playsInline
                className="w-full h-48 bg-gray-200 rounded"
              />
            </div>
          </div>
        </Card>
      )}

      {/* CHAT UI */}
      <Card className="h-96 flex flex-col">
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {chat.messages.map((msg) => (
            <div key={msg.id} className="flex flex-col">
              <div className="flex items-center space-x-2">
                <span className="font-semibold">
                  {msg.sender_name}
                </span>

                <span className="text-sm text-gray-500">
                  {new Date(
                    msg.timestamp
                  ).toLocaleString()}
                </span>
              </div>

              <p className="text-gray-800">
                {msg.content}
              </p>
            </div>
          ))}

          <div ref={messagesEndRef} />
        </div>

        {/* INPUT */}
        <div className="border-t p-4 flex space-x-2">
          <input
            type="text"
            value={message}
            onChange={(e) =>
              setMessage(e.target.value)
            }
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                sendMessage();
              }
            }}
            placeholder="Type a message..."
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />

          <Button
            onClick={sendMessage}
            disabled={!message.trim()}
          >
            Send
          </Button>
        </div>
      </Card>
    </div>
  );
}