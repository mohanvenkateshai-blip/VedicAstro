/**
 * NextAuth v5 configuration — Google OAuth only.
 *
 * Environment variables required:
 *   AUTH_SECRET          — cookie signing key (run: npx auth secret)
 *   AUTH_GOOGLE_ID       — Google OAuth client ID
 *   AUTH_GOOGLE_SECRET   — Google OAuth client secret
 *   DATABASE_URL         — Neon Postgres connection string
 *
 * When auth is not configured, exports no-op stubs so Learn and other public
 * routes work without MissingSecret console errors.
 */

import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
import type { Role } from "@/lib/auth/types";
import { isAdminEmail, isAuthConfigured } from "@/lib/auth-config";

declare module "next-auth" {
  interface User {
    role?: Role;
  }
}

declare module "@auth/core/adapters" {
  interface AdapterUser {
    role?: Role;
  }
}

function googleUserId(
  user: { id?: string },
  account?: { providerAccountId?: string | null } | null,
) {
  return account?.providerAccountId ?? user.id ?? "";
}

function createNextAuth() {
  return NextAuth({
    secret: process.env.AUTH_SECRET,
    providers: [
      Google({
        clientId: process.env.AUTH_GOOGLE_ID!,
        clientSecret: process.env.AUTH_GOOGLE_SECRET!,
      }),
    ],
    callbacks: {
      async signIn({ user, account }) {
        if (account?.provider === "google" && user.email) {
          const id = googleUserId(user, account);
          if (!id) return false;
          try {
            const { upsertUser } = await import("@/lib/auth/index");
            await upsertUser({
              id,
              email: user.email,
              name: user.name ?? undefined,
            });
          } catch {
            // Non-fatal — user can still sign in without DB
          }
        }
        return true;
      },
      async jwt({ token, user, account }) {
        if (account?.providerAccountId) {
          token.id = account.providerAccountId;
          token.sub = account.providerAccountId;
        } else if (user) {
          const id = googleUserId(user, account);
          token.id = id;
          token.sub = id;
        }
        if (user || account?.providerAccountId) {
          const id = (token.id ?? token.sub) as string;
          try {
            const { getUser } = await import("@/lib/auth/index");
            const dbUser = id ? await getUser(id) : null;
            const email = (user?.email ?? token.email) as string | undefined;
            if (email && isAdminEmail(email)) {
              token.role = "admin";
            } else {
              token.role = dbUser?.role ?? "free";
            }
          } catch {
            token.role = "free";
          }
        }
        return token;
      },
      async session({ session, token }) {
        if (session.user) {
          const id = (token.id ?? token.sub) as string;
          (session.user as { id?: string }).id = id;
          (session.user as { role?: Role }).role = (token.role as Role) ?? "free";
        }
        return session;
      },
    },
    pages: {
      signIn: "/auth/signin",
      error: "/auth/error",
    },
    trustHost: true,
  });
}

/** No-op auth exports when OAuth is not configured (anonymous / Learn mode). */
function createAuthDisabled() {
  const notConfigured = () =>
    Response.json({ error: "Auth not configured" }, { status: 503 });

  return {
    handlers: { GET: notConfigured, POST: notConfigured },
    auth: async () => null,
    signIn: async () => {
      throw new Error("Auth not configured — set AUTH_SECRET and Google OAuth env vars");
    },
    signOut: async () => {},
  };
}

export const { handlers, auth, signIn, signOut } = isAuthConfigured()
  ? createNextAuth()
  : createAuthDisabled();
