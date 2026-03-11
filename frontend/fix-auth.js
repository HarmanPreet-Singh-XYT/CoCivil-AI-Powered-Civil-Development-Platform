async function getLocation(ip) {
    if (!ip || ip === "::1" || ip === "127.0.0.1" || ip === "::" || ip.includes("0000:0000")) {
        return { loc: "Local Network (Localhost)", lat: null, lon: null, ipString: "Localhost" };
    }
    try {
        const res = await fetch(`http://ip-api.com/json/${ip}`);
        const data = await res.json();
        if (data.status === "success" && data.city) {
            return { loc: `${data.city}, ${data.regionName}, ${data.countryCode}`, lat: data.lat, lon: data.lon, ipString: ip };
        }
    } catch(e) { }
    return { loc: "Unknown Geographical Location", lat: null, lon: null, ipString: ip };
}

getLocation("8.8.8.8").then(console.log);
getLocation("::1").then(console.log);
