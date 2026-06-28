import { createClient } from "@supabase/supabase-js";

const url  = process.env.SUPABASE_URL!;
const key  = process.env.SUPABASE_SERVICE_ROLE_KEY!;

// Server-only client — uses service role key, bypasses RLS.
// Never expose this to the browser.
export const supabase = createClient(url, key, {
  auth: { persistSession: false },
});
