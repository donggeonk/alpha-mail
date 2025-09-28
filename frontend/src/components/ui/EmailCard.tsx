"use client";

import { useState } from "react";
import {
  motion,
  AnimatePresence,
  useMotionValue,
  useTransform,
} from "framer-motion";
import { Card, CardHeader, CardContent, CardFooter } from "@/components/ui/card";
import { EmailSummary } from "@/lib/types";

const DRAG_THRESHOLD = 100;

function formatDate(dateString: string) {
  const date = new Date(dateString);
  // Check if the date is valid before formatting
  if (isNaN(date.getTime())) {
    return "Invalid Date";
  }
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export default function EmailCard({
  email,
  onAction,
}: {
  email: EmailSummary;
  onAction?: (action: "flag" | "keep" | "discard") => void;
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const cardX = useMotionValue(0);

  // Animate the card's rotation and opacity based on the drag handle's position
  const rotate = useTransform(cardX, [-200, 200], [-25, 25]);
  const opacity = useTransform(cardX, [-150, 0, 150], [0.5, 1, 0.5]);

  const handleAction = (newStatus: "flag" | "keep" | "discard") => {
    onAction?.(newStatus);
  };

  return (
    <motion.div style={{ x: cardX, rotate, opacity }} className="w-full">
      <Card
        className="w-full max-w-lg shadow-md rounded-2xl bg-white overflow-hidden"
        onDoubleClick={() => handleAction("flag")}
      >
      <CardHeader>
        <h2 className="text-lg font-bold">{email.subject}</h2>
        <div className="text-xs text-gray-500 flex justify-between">
          <span>From: {email.sender}</span>
          <span>{formatDate(email.receivedDate)}</span>
        </div>
      </CardHeader>
      <CardContent>
        <div className="bg-gray-50 border border-gray-200 p-3 rounded-lg">
          <p className="font-bold text-gray-800">Summary</p>
          <div className="text-sm text-gray-700 mt-1">
            <p className="whitespace-pre-wrap">{email.summary}</p>
          </div>
        </div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-1 text-sm font-medium text-gray-600 hover:text-gray-900 mt-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
        >
          <span>{isExpanded ? "Close" : "View full email"}</span>
          <motion.span
            animate={{ rotate: isExpanded ? 180 : 0 }}
            transition={{ duration: 0.2 }}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="currentColor"
            >
              <path d="M4.94 5.727L8 8.787l3.06-3.06.94.94-4 4-4-4z" />
            </svg>
          </motion.span>
        </button>
        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden mt-3 text-sm text-gray-700"
            >
              <p className="whitespace-pre-wrap">{email.fullContent}</p>
            </motion.div>
          )}
        </AnimatePresence>
        {email.actionRequired && (
          <div className="bg-red-50 border border-red-200 text-red-800 p-3 mt-3 rounded-lg">
            <p className="font-bold">⚠️ Action Required!</p>
            <p className="text-sm mt-1">
              {email.actionDescription || "No specific action provided."}
            </p>
          </div>
        )}
      </CardContent>
      <CardFooter className="flex justify-between items-center pt-4 pb-5 bg-gray-50 border-t px-6">
        <span className="text-sm font-medium text-red-500">Discard</span>
        <div className="flex flex-col items-center gap-1">
          <motion.div
            drag="x"
            dragConstraints={{ left: 0, right: 0 }}
            dragElastic={0.2}
            style={{ x: cardX }}
            onDoubleClick={(e) => {
              e.stopPropagation(); // Prevent card's onDoubleClick from firing
              handleAction("flag");
            }}
            onDragEnd={(event, info) => {
              if (info.offset.x > DRAG_THRESHOLD) {
                handleAction("keep");
              } else if (info.offset.x < -DRAG_THRESHOLD) {
                handleAction("discard");
              }
            }}
            className="w-24 h-8 bg-gray-200 rounded-full flex items-center justify-center cursor-grab active:cursor-grabbing"
          >
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              className="text-gray-500"
            >
              <path d="M8 10L8 14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              <path d="M16 10L16 14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </motion.div>
          <span className="text-xs text-gray-400">Double Tap to Flag</span>
        </div>
        <span className="text-sm font-medium text-green-500">Keep</span>
      </CardFooter>
    </Card>
    </motion.div>
  );
}