import { betterAuth } from "better-auth";
import "dotenv/config";
import { Pool } from "pg";
import nodemailer from "nodemailer";

const transporter = nodemailer.createTransport({});

export const auth = betterAuth({
    database: new Pool({
        connectionString: process.env.DATABASE_URL
    }),
    emailAndPassword: {
        enabled: true,
        // session invalidation
    },
    databaseHooks: {
        user: {
            create: {
                after: async (user) => {
                    console.log("Welcome!", user.email);
                }
            }
        },
        session: {
            create: {
                after: async (session) => {
                    console.log("New login from", session.ipAddress, session.userAgent);
                }
            }
        }
    }
});
