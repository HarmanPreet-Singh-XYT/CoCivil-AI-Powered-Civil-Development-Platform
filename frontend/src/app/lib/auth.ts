import { betterAuth } from "better-auth";
import "dotenv/config";
import { Pool } from "pg";
import nodemailer from "nodemailer";

const pool = new Pool({
    connectionString: process.env.DATABASE_URL
});

// Configure standard Nodemailer settings using Env variables
const transporter = nodemailer.createTransport({
    host: process.env.SMTP_HOST || "smtp.gmail.com",
    port: parseInt(process.env.SMTP_PORT || "587"),
    secure: process.env.SMTP_PORT === "465", 
    auth: {
        user: process.env.SMTP_USER,
        pass: process.env.SMTP_PASSWORD,
    },
});

export const auth = betterAuth({
    database: new Pool({
        connectionString: process.env.DATABASE_URL
    }),
    rateLimit: {
        window: 60, // 60 seconds
        max: 100, // 100 requests max per 60 seconds
    },
    emailAndPassword: {
        enabled: true,
        // Invalidate all other sessions when user changes/resets password for security
        revokeSessionsOnPasswordReset: true,
        async sendResetPassword(data: any, request: any) {
            console.log("Preparing to send reset password email to:", data.user.email);
            
            try {
                if (process.env.SMTP_USER && process.env.SMTP_PASSWORD) {
                    await transporter.sendMail({
                        from: process.env.SMTP_FROM || '"CoCivil Team" <hello@cocivil.app>',
                        to: data.user.email,
                        subject: "Reset your CoCivil password",
                        html: `
                            <div style="font-family: Arial, sans-serif; background-color: #0A0A0C; color: #ffffff; padding: 40px; border-radius: 8px; max-width: 600px; margin: 0 auto;">
                                <h1 style="color: #c8a55c; text-align: center;">CoCivil Password Reset</h1>
                                <p style="font-size: 16px; color: #d6d3d1;">Hello ${data.user.name},</p>
                                <p style="font-size: 16px; color: #a8a29e;">We received a request to reset your password. If you didn't make this request, you can safely ignore this email.</p>
                                <div style="text-align: center; margin: 30px 0;">
                                    <a href="${data.url}" style="background-color: #c8a55c; color: #111; padding: 14px 24px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px; display: inline-block;">Reset Password</a>
                                </div>
                                <p style="font-size: 14px; color: #a8a29e; text-align: center;">Or copy and paste this link into your browser:</p>
                                <p style="font-size: 12px; color: #888; text-align: center; word-break: break-all;">${data.url}</p>
                                <hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.1); margin: 30px 0;">
                                <p style="font-size: 12px; color: #888; text-align: center;">This link will expire in 1 hour.</p>
                            </div>
                        `,
                    });
                    console.log("Reset email dispatched successfully.");
                } else {
                    console.warn("⚠️ SMTP credentials missing! The Reset URL is:");
                    console.info(data.url);
                }
            } catch (err) {
                console.error("Failed to send reset email via Nodemailer:", err);
            }
        },
        async onPasswordReset({ user }: any, request: any) {
            try {
                if (process.env.SMTP_USER && process.env.SMTP_PASSWORD) {
                    await transporter.sendMail({
                        from: process.env.SMTP_FROM || '"CoCivil Team" <hello@cocivil.app>',
                        to: user.email,
                        subject: "Your CoCivil password has been changed",
                        html: `
                            <div style="font-family: Arial, sans-serif; background-color: #0A0A0C; color: #ffffff; padding: 40px; border-radius: 8px; max-width: 600px; margin: 0 auto;">
                                <h1 style="color: #10b981; text-align: center;">Password Updated</h1>
                                <p style="font-size: 16px; color: #d6d3d1;">Hello ${user.name},</p>
                                <p style="font-size: 16px; color: #a8a29e;">This is a confirmation that the password for your CoCivil account has been successfully changed.</p>
                                <p style="font-size: 16px; color: #a8a29e;">If you did not make this change, please contact support immediately.</p>
                            </div>
                        `,
                    });
                }
            } catch (e) {
                console.error("Failed to send password reset successful email:", e);
            }
        }
    },
    databaseHooks: {
        user: {
            create: {
                after: async (user: any) => {
                    try {
                        if (process.env.SMTP_USER && process.env.SMTP_PASSWORD) {
                            await transporter.sendMail({
                                from: process.env.SMTP_FROM || '"CoCivil Team" <hello@cocivil.app>',
                                to: user.email,
                                subject: "Welcome to CoCivil!",
                                html: `
                                    <div style="font-family: Arial, sans-serif; background-color: #0A0A0C; color: #ffffff; padding: 40px; border-radius: 8px; max-width: 600px; margin: 0 auto;">
                                        <h1 style="color: #c8a55c; text-align: center;">Welcome to CoCivil!</h1>
                                        <p style="font-size: 16px; color: #d6d3d1;">Hello ${user.name},</p>
                                        <p style="font-size: 16px; color: #a8a29e;">We're excited to have you on board! You can now start using CoCivil to explore subsurface infrastructure.</p>
                                    </div>
                                `,
                            });
                        }
                    } catch (e) { console.error("Welcome email error:", e); }
                }
            }
        },
        session: {
            create: {
                after: async (session: any) => {
                    // Send sign-in email
                    try {
                        // The user was created, but usually session format might not have fully populated user, so we pull email logic carefully
                        // In Better Auth `session.create.after`, `session` object contains `userId`, `ipAddress`, `userAgent`.
                        if (process.env.SMTP_USER && process.env.SMTP_PASSWORD) {
                            
                            // we need user email to send it to. we can fetch it via pg pool directly
                            const res = await pool.query('SELECT name, email FROM "user" WHERE id = $1', [session.userId]);
                            if (res.rows.length === 0) return;
                            const dbUser = res.rows[0];

                            // Check if this is their first login by seeing if they just created their account
                            // Normally we'd check created_at. Let's send it regardless for now or just trust our condition
                            // Let's assume the prompt says 'but not for first time sign in', we could theoretically check their previous sessions, or just check created_at.
                            const userRes = await pool.query('SELECT "createdAt" FROM "user" WHERE id = $1', [session.userId]);
                            const isNewAccount = userRes.rows.length > 0 && (new Date().getTime() - new Date(userRes.rows[0].createdAt).getTime()) < 60000;
                            
                            let displayIp = session.ipAddress || 'Unknown';
                            let locationText = "Unknown Geographical Location";
                            let mapImg = "";

                            // Handle Local/IPv6 Local IPs
                            if (!displayIp || displayIp === "::1" || displayIp === "127.0.0.1" || displayIp === "::" || displayIp.includes("0000:0000")) {
                                displayIp = "Local Network (Localhost)";
                                locationText = "Local Machine";
                            } else {
                                try {
                                    const geoRes = await fetch(`http://ip-api.com/json/${displayIp}`);
                                    const geoData = await geoRes.json();
                                    if (geoData.status === "success" && geoData.city) {
                                        locationText = `${geoData.city}, ${geoData.regionName}, ${geoData.country}`;
                                        // Include a small OpenStreetMap static map if coords are available
                                        mapImg = `<div style="margin: 20px 0; border-radius: 8px; overflow: hidden; border: 1px solid rgba(255,255,255,0.1);"><img src="https://staticmap.openstreetmap.de/staticmap.php?center=${geoData.lat},${geoData.lon}&zoom=10&size=600x200&markers=${geoData.lat},${geoData.lon}" width="100%" alt="Map" style="display: block;" /></div>`;
                                    }
                                } catch (e) {
                                    console.error("IP geolocation failed", e);
                                }
                            }

                            if (!isNewAccount) {
                                await transporter.sendMail({
                                    from: process.env.SMTP_FROM || '"CoCivil Team" <hello@cocivil.app>',
                                    to: dbUser.email,
                                    subject: "New Login into CoCivil",
                                    html: `
                                        <div style="font-family: Arial, sans-serif; background-color: #0A0A0C; color: #ffffff; padding: 40px; border-radius: 8px; max-width: 600px; margin: 0 auto;">
                                            <h1 style="color: #c8a55c; text-align: center;">New Sign-In Found</h1>
                                            <p style="font-size: 16px; color: #d6d3d1;">Hello ${dbUser.name},</p>
                                            <p style="font-size: 16px; color: #a8a29e;">We noticed a new login to your CoCivil account.</p>
                                            <hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.1); margin: 30px 0;">
                                            <p style="font-size: 14px; color: #d6d3d1; margin: 8px 0;"><strong>Browser:</strong> ${session.userAgent || 'Unknown'}</p>
                                            <p style="font-size: 14px; color: #d6d3d1; margin: 8px 0;"><strong>IP Address:</strong> ${displayIp}</p>
                                            <p style="font-size: 14px; color: #d6d3d1; margin: 8px 0;"><strong>Location:</strong> ${locationText}</p>
                                            ${mapImg}
                                            <hr style="border: 0; border-top: 1px solid rgba(255,255,255,0.1); margin: 30px 0;">
                                            <p style="font-size: 14px; color: #a8a29e;">If this wasn't you, someone else might have accessed your account. We highly recommend you change your password immediately.</p>
                                            <div style="text-align: center; margin: 30px 0;">
                                                <a href="${process.env.BETTER_AUTH_URL || 'http://localhost:3000'}/forget-password" style="background-color: #ef4444; color: #fff; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 14px; display: inline-block;">Reset Password</a>
                                            </div>
                                        </div>
                                    `,
                                });
                            }
                        }
                    } catch (e) {
                        console.error("Sign-in security email error:", e);
                    }
                }
            }
        }
    }
});