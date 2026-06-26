/**
 * NextAuth v5 configuration — Google OAuth only.
 *
 * Environment variables required:
 *   AUTH_SECRET          — cookie signing key (run: npx auth secret)
 *   AUTH_GOOGLE_ID       — Google OAuth client ID
 *   AUTH_GOOGLE_SECRET   — Google OAuth client secret
 *   DATABASE_URL         — Neon Postgres connection string
 */

import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
import type { Role } from "@/lib/auth/types";

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

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Google({
      clientId: process.env.AUTH_GOOGLE_ID!,
      clientSecret: process.env.AUTH_GOOGLE_SECRET!,
    }),
  ],
  callbacks: {
    async signIn({ user, account }) {
      if (account?.provider === "google" && user.id && user.email) {
        try {
          const { upsertUser } = await import("@/lib/auth/index");
          await upsertUser({
            id: user.id as string,
            email: user.email as string,
            name: user.name ?? undefined,
          });
        } catch {
          // Non-fatal — user can still sign in without DB
        }
      }
      return true;
    },
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id;
        try {
          const { getUser } = await import("@/lib/auth/index");
          const dbUser = await getUser(user.id as string);
          token.role = dbUser?.role ?? "free";
        } catch {
          token.role = "free";
        }
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        (session.user as any).id = token.id as string;
        (session.user as any).role = token.role ?? "free";
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
