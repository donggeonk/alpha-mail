"use client";

import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import EmailCard from "@/components/ui/EmailCard";
import { EmailSummary } from "@/lib/types";

export default function EmailCardStack({
  initialEmails,
}: {
  initialEmails: EmailSummary[];
}) {
  const [emails, setEmails] = useState(initialEmails);
  const [exitDirection, setExitDirection] = useState<"keep" | "discard" | "flag" | null>(null);

  const handleAction = async (
    emailId: string,
    action: "keep" | "discard" | "flag"
  ) => {
    setExitDirection(action);

    // Optimistically remove the email from the UI
    setEmails((prev) => prev.filter((email) => email.id !== emailId));

    try {
      const response = await fetch("/api/email-action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ emailId, action }),
      });

      if (!response.ok) {
        console.error("Failed to save action to backend:", await response.text());
        // TODO: Handle error, e.g., show a toast and potentially revert the state
      }
    } catch (error) {
      console.error("Error communicating with backend:", error);
      // TODO: Handle network error
    }
  };

  const exitVariants = useMemo(() => ({
    keep: { x: 300, opacity: 0, transition: { duration: 0.3 } },
    discard: { x: -300, opacity: 0, transition: { duration: 0.3 } },
    flag: { y: -100, opacity: 0, transition: { duration: 0.3 } },
    default: {
      y: -20,
      opacity: 0,
      scale: 0.95,
      transition: { duration: 0.2 },
    },
  }), []);

  return (
    <div className="relative w-full max-w-lg h-[700px] flex items-center justify-center">
      <AnimatePresence>
        {emails.length > 0 && (
          <motion.div
            key={emails[emails.length - 1].id}
            className="absolute w-full"
            initial={{ scale: 0.95, y: 20, opacity: 0 }}
            animate={{ scale: 1, y: 0, opacity: 1 }}            
            exit={exitDirection ? exitVariants[exitDirection] : exitVariants.default}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
          >
            <EmailCard
              email={emails[emails.length - 1]}
              onAction={(action) =>
                handleAction(emails[emails.length - 1].id, action)
              }
            />
          </motion.div>
        )}
      </AnimatePresence>
      {emails.length === 0 && (
        <p className="text-gray-500">All emails have been reviewed!</p>
      )}
    </div>
  );
}