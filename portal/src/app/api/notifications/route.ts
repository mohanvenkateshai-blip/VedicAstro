import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth/session";
import {
  listNotifications,
  unreadCount,
  markNotificationRead,
  markAllRead,
} from "@/lib/auth/index";

export const runtime = "nodejs";

/** GET → { items, unread } for the notification bell. */
export async function GET() {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const [items, unread] = await Promise.all([
    listNotifications(session.userId, 20),
    unreadCount(session.userId),
  ]);
  return NextResponse.json({ items, unread });
}

/** PATCH { id } → mark one read · PATCH { all: true } → mark all read. */
export async function PATCH(req: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const body = (await req.json().catch(() => ({}))) as { id?: string; all?: boolean };
  if (body.all) {
    await markAllRead(session.userId);
  } else if (body.id) {
    await markNotificationRead(session.userId, body.id);
  } else {
    return NextResponse.json({ error: "id or all required" }, { status: 400 });
  }
  const unread = await unreadCount(session.userId);
  return NextResponse.json({ ok: true, unread });
}
