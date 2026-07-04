"use client";

import { signOut } from "next-auth/react";
import { LogOut } from "lucide-react";

export function SignOutButton() {
  return (
    <button
      type="button"
      onClick={() => signOut({ redirectTo: "/" })}
      className="inline-flex items-center gap-2 rounded-xl border border-hairline px-5 py-2.5 text-sm font-medium text-danger transition-colors hover:bg-danger/10"
    >
      <LogOut size={15} /> Sign out
    </button>
  );
}
