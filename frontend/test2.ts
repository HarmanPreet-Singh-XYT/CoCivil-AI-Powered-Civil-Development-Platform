import { auth } from "./src/app/lib/auth";
console.log(auth.options.emailAndPassword ? Object.keys(auth.options.emailAndPassword) : "no email and password");
