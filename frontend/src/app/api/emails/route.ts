import { NextResponse } from "next/server";
import { EmailSummary } from "@/lib/types";
import { firestoreAdmin } from "@/lib/firebase-admin";

export async function GET() {
  try {
    // TODO: Replace 'default' with the actual user_id you want to query for.
    const userId = "default";
    const collectionName = "emails"; // As defined in your Python script

    const emailsSnapshot = await firestoreAdmin
      .collection(collectionName)
      .where("user_id", "==", userId)
      .where("is_read", "==", false)
      .where("discard", "==", false)
      .orderBy("received_date", "desc")
      .limit(20) // Limit to a reasonable number of emails
      .get();

    if (emailsSnapshot.empty) {
      return NextResponse.json({ emails: [] });
    }

    // Map the backend data to the frontend EmailSummary type
    const emails: EmailSummary[] = emailsSnapshot.docs.map((doc) => {
      const data = doc.data();
      // Safely handle received_date: check if it's a Firestore Timestamp.
      // Fallback to the current date if it's missing or invalid.
      const receivedDate = data.received_date?.toDate
        ? data.received_date.toDate().toISOString()
        : new Date().toISOString();
      return {
        id: data.gmail_id, // Use the unique gmail_id for the card's key
        subject: data.subject,
        sender: data.sender,
        summary: data.summary || data.snippet, // Use LLM summary if available, otherwise fallback to snippet
        fullContent: data.body,
        receivedDate: receivedDate,
        actionRequired: data.is_important || false,
        actionDescription: data.is_important ? "This email is marked as important." : undefined,
        status: "none",
      };
    });

    return NextResponse.json({ emails });
  } catch (error) {
    console.error("Error fetching emails from Firestore:", error);
    return NextResponse.json(
      { message: "Failed to fetch emails from Firestore.", error: (error as Error).message },
      { status: 500 }
    );
  }
}
