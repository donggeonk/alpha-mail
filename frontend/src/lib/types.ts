export interface EmailSummary {
  id: string;
  subject: string;
  sender: string;
  summary: string;
  receivedDate: string; // ISO date string
  actionRequired: boolean;
  fullContent: string;
  actionDescription?: string;
  status: "none" | "flag" | "keep" | "discard";
}