"use client";

import { useEffect, useState } from "react";
import { EmailSummary } from "@/lib/types";
import EmailCardStack from "@/components/ui/EmailCardStack";

export default function HomePage() {
  const [emails, setEmails] = useState<EmailSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchEmails() {
      try {
        // TODO: Replace with actual backend endpoint
        const response = await fetch("/api/emails");
        if (!response.ok) {
          throw new Error("Failed to fetch emails");
        }
        const data = await response.json();
        setEmails(data.emails);
      } catch (error) {
        console.error("Error fetching emails:", error);
        // TODO: Handle error state in the UI
      } finally {
        setIsLoading(false);
      }
    }
    fetchEmails();
  }, []);

  return (
    <div className="flex flex-col items-center p-6">
      <h1 className="text-2xl font-bold mb-6">⍺lphaMail</h1>
      {isLoading ? (
        <p className="text-gray-500">Loading emails...</p>
      ) : (
        <EmailCardStack initialEmails={emails} />
      )}
    </div>
  );
}
