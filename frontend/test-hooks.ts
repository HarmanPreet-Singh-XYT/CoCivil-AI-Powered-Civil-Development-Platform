import { auth } from "./src/app/lib/auth";
import "dotenv/config";

console.log("Hooks object keys:");
console.log(Object.keys(auth));
console.log("Internal methods/configs:");
console.log(auth.api ? Object.keys(auth.api) : "no api");
