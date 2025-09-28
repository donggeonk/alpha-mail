import { NextResponse } from "next/server";

export async function POST(request: Request) {
  try {
    const { emailId, action } = await request.json();
    console.log(
      `Received action '${action}' for email '${emailId}'. Action is currently disabled.`
    );

    // Return a success response without performing any action.
    return NextResponse.json({ success: true, message: "Action disabled." });
  } catch (error) {
    console.error("Error processing email action:", error);
    return NextResponse.json(
      { success: false, message: "Internal Server Error" },
      { status: 500 }
    );
  }
}

