// index.js
require("dotenv").config();
const axios = require("axios");
const cheerio = require("cheerio");
const fs = require("fs");

const WEBHOOK = process.env.WEBHOOK_URL;
const CHECK_DELAY = 1000; // 1 detik
const DB_FILE = "sent.json";

let sent = new Set();

// Load database item terkirim
if (fs.existsSync(DB_FILE)) {
    const data = JSON.parse(fs.readFileSync(DB_FILE));
    sent = new Set(data);
}

// Save database
function saveDB() {
    fs.writeFileSync(DB_FILE, JSON.stringify([...sent], null, 2));
}

// Ambil item Rolimons
async function getItems() {
    const { data } = await axios.get("https://www.rolimons.com/free-roblox-limiteds", {
        headers: {
            "User-Agent": "Mozilla/5.0"
        }
    });

    const $ = cheerio.load(data);
    const items = [];

    $(".card, .limited-card, .item-card").each((i, el) => {
        const name = $(el).find("h3,h4,.item-name").first().text().trim();
        if (!name) return;

        const creator =
            $(el).find(".creator,.creator-name").text().trim() || "Unknown";

        const qty =
            $(el).find(".stock,.quantity").text().trim() || "Unknown";

        const image =
            $(el).find("img").attr("src") || "";

        const roblox =
            $(el).find("a:contains('Roblox Page')").attr("href") ||
            "https://roblox.com/catalog";

        const tryon =
            $(el).find("a:contains('Try On')").attr("href") ||
            roblox;

        const sale = [];

        $(el).find("a").each((_, a) => {
            const text = $(a).text().trim();
            const href = $(a).attr("href");

            if (
                text &&
                href &&
                !text.includes("Roblox") &&
                !text.includes("Try")
            ) {
                sale.push(`[${text}](https://www.rolimons.com${href})`);
            }
        });

        items.push({
            id: name,
            name,
            creator,
            qty,
            image,
            roblox,
            tryon,
            sale: sale.join("\n") || "None"
        });
    });

    return items;
}

// Kirim Discord
async function send(item) {
    if (sent.has(item.id)) return;

    sent.add(item.id);
    saveDB();

    await axios.post(WEBHOOK, {
        content: "@everyone 🚨 NEW FREE LIMITED FOUND!",
        embeds: [{
            color: 3447003,
            author: {
                name: "Rolimon's",
                icon_url: "https://www.rolimons.com/favicon.ico"
            },
            title: item.name,
            description:
`✨ UGC Back Accessory Went Limited
🎮 In-Game Only

🌐 [Roblox Page](${item.roblox})
👕 [Try On](${item.tryon})`,
            thumbnail: {
                url: item.image
            },
            fields: [
                {
                    name: "Sale Locations",
                    value: item.sale
                },
                {
                    name: "Quantity",
                    value: item.qty,
                    inline: true
                },
                {
                    name: "Creator",
                    value: item.creator,
                    inline: true
                }
            ],
            footer: {
                text: "Rolimons Instant Monitor"
            },
            timestamp: new Date()
        }]
    });

    console.log("Sent:", item.name);
}

// Monitoring ultra cepat
async function monitor() {
    try {
        const items = await getItems();

        for (const item of items) {
            await send(item);
        }

    } catch (err) {
        console.log("Error, retrying...");
    }
}

console.log("🚀 Railway PRO Running...");
setInterval(monitor, CHECK_DELAY);
monitor();
