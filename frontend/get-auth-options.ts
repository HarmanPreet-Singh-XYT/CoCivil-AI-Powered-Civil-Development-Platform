import { auth } from "./src/app/lib/auth";
console.log(auth.options.emailAndPassword);
const cb = auth.options.emailAndPassword;
console.log("Keys:", cb ? Object.keys(cb) : "None");
