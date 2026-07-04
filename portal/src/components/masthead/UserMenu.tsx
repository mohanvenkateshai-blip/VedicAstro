"use client";

import { signOut } from "next-auth/react";
import { User, Settings, LogOut } from "lucide-react";
import { Avatar } from "@/components/ui/Avatar";
import { Menu, MenuItem } from "@/components/ui/Menu";
import { ThemePicker } from "./ThemePicker";
import type { Session } from "@/lib/auth/types";

/** Top-right account menu: profile, settings, theme, admin (if admin), sign out. */
export function UserMenu({ session }: { session: Session }) {
  const isAdmin = session.role === "admin";

  return (
    <Menu
      label="Account menu"
      trigger={
        <span className="flex items-center gap-2 rounded-full p-0.5 hover:bg-accent/5 transition-colors">
          <Avatar name={session.name} email={session.email} image={session.image} size="md" />
        </span>
      }
      panelClassName="min-w-[240px]"
    >
      <div className="border-b border-hairline px-4 py-3">
        <p className="truncate text-sm font-medium text-text-main">
          {session.name || "Signed in"}
        </p>
        <p className="truncate text-xs text-text-muted">{session.email}</p>
        {isAdmin && (
          <span className="mt-1.5 inline-block rounded border border-accent/40 px-1.5 py-px text-[10px] font-mono uppercase tracking-wide text-accent">
            admin
          </span>
        )}
      </div>

      <div className="py-1">
        <MenuItem href="/profile" icon={<User size={15} />}>
          Profile
        </MenuItem>
        <MenuItem href="/settings" icon={<Settings size={15} />}>
          Settings
        </MenuItem>
      </div>

      <div className="border-t border-hairline px-4 py-3">
        <p className="mb-2 text-[10px] font-mono uppercase tracking-wide text-text-muted">Theme</p>
        <ThemePicker signedIn size="sm" />
      </div>

      <div className="border-t border-hairline py-1">
        <MenuItem icon={<LogOut size={15} />} danger onClick={() => signOut({ redirectTo: "/" })}>
          Sign out
        </MenuItem>
      </div>
    </Menu>
  );
}
