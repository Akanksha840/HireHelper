"use client";

import { useEffect, useState } from "react";
import StatusBadge from "../../../components/StatusBadge";
import { Loader2, Clock, MapPin } from "lucide-react";

// Generate a consistent color from a name string
function getAvatarColor(name: string) {
  const colors = [
    "bg-blue-500",
    "bg-purple-500",
    "bg-green-500",
    "bg-rose-500",
    "bg-amber-500",
    "bg-teal-500",
    "bg-indigo-500",
    "bg-pink-500",
  ];
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
}

function getInitials(name: string) {
  return name
    .split(" ")
    .map((part) => part[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

export default function RequestsPage() {
  const [requests, setRequests] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => {
    fetchRequests();
  }, []);

  const fetchRequests = async () => {
    try {
      const token =
        sessionStorage.getItem("token") || localStorage.getItem("token");
      const res = await fetch("http://127.0.0.1:8000/api/requests/incoming", {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });

      if (!res.ok) throw new Error("Failed to fetch requests");

      const data = await res.json();
      setRequests(data);
    } catch (err: any) {
      setError(err.message || "Failed to load requests");
    } finally {
      setLoading(false);
    }
  };

  const handleAction = async (
    requestId: string,
    status: "accepted" | "rejected"
  ) => {
    setActionLoading(requestId);
    try {
      const token =
        sessionStorage.getItem("token") || localStorage.getItem("token");
      const res = await fetch(
        `http://127.0.0.1:8000/api/requests/${requestId}/status`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({ status }),
        }
      );

      if (!res.ok) throw new Error(`Failed to update request to ${status}`);

      setRequests((prev) =>
        prev.map((req) =>
          (req.id || req._id) === requestId ? { ...req, status } : req
        )
      );
    } catch (err) {
      console.error(err);
      alert("Something went wrong changing the status.");
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Requests</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          People who want to help with your tasks
        </p>
      </div>

      {/* Card */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {/* Section Header */}
        <div className="px-6 pt-5 pb-4 border-b border-gray-100">
          <h2 className="text-base font-semibold text-gray-900">
            Incoming Requests
          </h2>
          <p className="text-sm text-gray-500 mt-0.5">
            People who want to help with your tasks
          </p>
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex items-center justify-center h-48">
            <Loader2 className="h-7 w-7 animate-spin text-blue-500" />
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-48 text-red-500 font-medium text-sm">
            {error}
          </div>
        ) : requests.length === 0 ? (
          <div className="flex items-center justify-center h-48">
            <p className="text-gray-400">No incoming requests yet</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {requests.map((req) => {
              const reqId = req.id || req._id;
              const senderName = req.sender_name || "Unknown User";
              const avatarColor = getAvatarColor(senderName);
              const initials = getInitials(senderName);
              const rating = req.sender_rating ?? 4.8;
              const reviews = req.sender_reviews ?? 0;
              const isPending = req.status === "pending";

              // Format date
              let dateStr = "";
              try {
                const d = new Date(req.created_at || Date.now());
                dateStr = d.toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                });
                const timeStr = d.toLocaleTimeString("en-US", {
                  hour: "numeric",
                  minute: "2-digit",
                });
                dateStr = `${dateStr}, ${timeStr}`;
              } catch {
                dateStr = "";
              }

              return (
                <div key={reqId} className="px-6 py-5 flex flex-col gap-4">
                  {/* Top row: avatar + info + actions */}
                  <div className="flex items-start justify-between gap-4">
                    {/* Left: Avatar + Name/Message */}
                    <div className="flex items-start gap-3 flex-1 min-w-0">
                      {/* Avatar */}
                      <div
                        className={`flex-shrink-0 h-10 w-10 rounded-full ${avatarColor} flex items-center justify-center text-white text-sm font-bold overflow-hidden`}
                      >
                        {req.sender_image ? (
                          <img
                            src={req.sender_image}
                            alt={senderName}
                            className="h-full w-full object-cover"
                          />
                        ) : (
                          initials
                        )}
                      </div>

                      {/* Name + Rating + Message */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-semibold text-gray-900 text-sm">
                            {senderName}
                          </span>
                          <span className="flex items-center gap-1 text-xs text-amber-500 font-medium">
                            ★ {rating}
                            <span className="text-gray-400 font-normal">
                              ({reviews} reviews)
                            </span>
                          </span>
                        </div>
                        <p className="text-sm text-gray-600 mt-1 leading-relaxed">
                          {req.message ||
                            "I'd love to help with your task. I have the necessary skills and experience."}
                        </p>
                      </div>
                    </div>

                    {/* Right: Actions or Status Badge */}
                    <div className="flex-shrink-0 flex items-center gap-2">
                      {isPending ? (
                        <>
                          <button
                            onClick={() => handleAction(reqId, "accepted")}
                            disabled={actionLoading === reqId}
                            className="px-4 py-1.5 bg-green-500 hover:bg-green-600 text-white rounded-md text-sm font-medium transition-colors disabled:opacity-50 flex items-center gap-1"
                          >
                            {actionLoading === reqId && (
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            )}
                            Accept
                          </button>
                          <button
                            onClick={() => handleAction(reqId, "rejected")}
                            disabled={actionLoading === reqId}
                            className="px-4 py-1.5 text-gray-600 hover:text-gray-900 text-sm font-medium transition-colors disabled:opacity-50"
                          >
                            Decline
                          </button>
                        </>
                      ) : req.status === "accepted" ? (
                        <div className="flex items-center gap-2">
                          <StatusBadge status={req.status} />
                          <a
                            href={`/dashboard/chat/${reqId}`}
                            className="px-4 py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded-md text-sm font-medium transition-colors"
                          >
                            Chat & Call
                          </a>
                        </div>
                      ) : (
                        <StatusBadge status={req.status} />
                      )}
                    </div>
                  </div>

                  {/* Requesting For Box */}
                  <div className="ml-[52px] bg-gray-50 rounded-lg px-4 py-3 border border-gray-100">
                    <p className="text-xs text-gray-500 font-medium">
                      Requesting for:
                    </p>
                    <p className="text-sm text-gray-800 mt-0.5">
                      {req.task_title || "Unknown Task"}
                    </p>
                  </div>

                  {/* Footer Meta */}
                  <div className="ml-[52px] flex items-center gap-4 text-xs text-gray-400">
                    {dateStr && (
                      <div className="flex items-center gap-1">
                        <Clock className="h-3.5 w-3.5" />
                        {dateStr}
                      </div>
                    )}
                    {req.task_location && (
                      <div className="flex items-center gap-1">
                        <MapPin className="h-3.5 w-3.5" />
                        {req.task_location}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
