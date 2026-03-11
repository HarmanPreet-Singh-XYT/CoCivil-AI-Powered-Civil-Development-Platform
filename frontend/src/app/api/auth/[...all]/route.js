import { betterAuth } from "better-auth";
import { Pool } from "pg";

const pool = new Pool({
  connectionString: process.env.DATABASE_URL || "postgresql://postgres:postgres@db.tcrtgxjqfokmhlwxhwxy.supabase.co:5432/postgres" // Note: Please add your actual Railway DATABASE_URL to .env
});

export const auth = betterAuth({
    database: {
        pool: pool,
        type: "postgres"
    },
    emailAndPassword: {
        enabled: true
    }
});

import { toNodeHandler } from "better-auth/node";

export const GET = toNodeHandler(auth.handler);
export const POST = toNodeHandler(auth.handler);
