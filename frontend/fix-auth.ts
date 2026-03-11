import { Pool } from "pg";
async function testLocation(ip: string) {
    if (ip === "::1" || ip === "127.0.0.1" || ip === "::" || ip === "0000:0000:0000:0000:0000:0000:0000:0001" || !ip || ip.includes("0000:0000")) {
        return "Local Network (Localhost)";
    }
    try {
        const res = await fetch(`http://ip-api.com/json/${ip}`);
        const data = await res.json();
        if (data.status === "success") {
            return `${data.city}, ${data.regionName}, ${data.country}`;
        }
    } catch(e) {}
    return "Unknown Location";
}
testLocation("8.8.8.8").then(console.log);
testLocation("::1").then(console.log);
testLocation("0000:0000:0000:0000:0000:0000:0000:0000").then(console.log);
