"use client";

import { useEffect, useState } from "react";
import StatusBadge from "../../../components/StatusBadge";
import { Loader2 } from "lucide-react";

export default function MyRequestsPage() {
  const [requests, setRequests] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchSentRequests();
  }, []);

  const fetchSentRequests = async () => {
    try {
      const token = sessionStorage.getItem("token") || localStorage.getItem("token");
      const res = await fetch("http://127.0.0.1:8000/api/requests/my", {
        headers: token ? { "Authorization": `Bearer ${token}` } : {}
      });

      if (!res.ok) throw new Error("Failed to fetch sent requests");

      const data = await res.json();
      setRequests(data);
    } catch (err: any) {
      setError(err.message || "Failed to load requests");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">My Requests</h1>
      <p className="text-gray-500 mb-8">Requests you've sent to help others with their tasks</p>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        </div>
      ) : error ? (
        <div className="flex items-center justify-center h-64 text-red-500 font-medium">
          {error}
        </div>
      ) : requests.length === 0 ? (
        <div className="flex items-center justify-center h-64 bg-white rounded-xl border border-dashed border-gray-300">
          <p className="text-gray-400 text-lg">You haven't sent any requests yet.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          {requests.map(req => {
            const reqId = req.id || req._id;
            return (
              <div key={reqId} className="bg-white rounded-xl shadow-sm border p-6 flex flex-col gap-4">

                {/* Header: User Info & Status */}
                <div className="flex justify-between items-start">
                  <div className="flex items-center gap-4">
                    {/* Avatar */}
                    <div className="h-10 w-10 rounded-full bg-gray-200 border border-gray-300 overflow-hidden flex-shrink-0 flex items-center justify-center text-gray-500 font-bold">
                      {req.owner_image ? (
                        <img src={req.owner_image} alt="User Profile" className="h-full w-full object-cover" />
                      ) : (
                        (req.owner_name || "U")[0].toUpperCase()
                      )}
                    </div>

                    {/* Title and Owner Name */}
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-gray-900 text-base">{req.task_title || "Unknown Task"}</h3>
                        <span className="text-xs px-2 py-0.5 bg-blue-50 text-blue-600 rounded-full font-medium">moving</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        Task owner: <span className="font-medium text-gray-700">{req.owner_name || "Unknown User"}</span>
                      </p>
                    </div>
                  </div>

                  {/* Status */}
                  <div className="flex flex-col items-end gap-2 ml-4">
                    <StatusBadge status={req.status} />
                    {req.status === "accepted" && (
                      <a
                        href={`/dashboard/chat/${reqId}`}
                        className="px-4 py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded-md text-sm font-medium transition-colors"
                      >
                        Chat & Call
                      </a>
                    )}
                  </div>
                </div>

                {/* Message Details Box */}
                <div className="ml-14 mr-4 bg-gray-50 rounded-lg p-4 border border-gray-100 flex flex-col gap-1">
                  <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Your message:</span>
                  <p className="text-sm text-gray-600">
                    {req.message || "I'd be happy to help with your task! I have the required skills and experience."}
                  </p>
                </div>

                {/* Footer Meta */}
                <div className="ml-14 flex flex-wrap items-center gap-4 text-xs text-gray-400">
                  <div className="flex items-center gap-1">
                    <span>🕒</span>
                    Sent {new Date(req.created_at || Date.now()).toLocaleDateString()}
                  </div>
                  {req.task_location && (
                    <div className="flex items-center gap-1">
                      <span>📍</span>
                      {req.task_location}
                    </div>
                  )}
                </div>

                {/* Optional Placeholder Image */}
                <div className="ml-14 mr-4 mt-2 h-40 max-w-sm rounded-lg overflow-hidden bg-gray-100 border border-gray-200">
                  <img src="https://images.unsplash.com/photo-1581578731548-c64695cc6952?q=80&w=1000&auto=format&fit=crop" alt="Task context" className="w-full h-full object-cover" />
                </div>

              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
