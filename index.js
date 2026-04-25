const axios = require("axios");
const cheerio = require("cheerio");
const fs = require("fs");

const WEBHOOK = process.env.WEBHOOK_URL;
const CHECK_DELAY = 10000; // 10 detik
const DB_FILE = "sent.json";

let sent = new Set();

// load DB
if (fs.existsSync(DB_FILE)) {
  try {
    sent = new Set(JSON.parse(fs.readFileSync(DB_FILE, "utf8")));
  } catch {}
}

function saveDB() {
  fs.writeFileSync(DB_FILE, JSON.stringify([...sent], null, 2));
}

async function getItems() {
  const url = "https://www.rolimons.com/free-roblox-limiteds";

  const { data } = await axios.get(url, {
    timeout: 15000,
    headers: {
      "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
      "Accept":
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
      "Accept-Language": "en-US,en;q=0.9",
      "Cache-Control": "no-cache",
      "Pragma": "no-cache"
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

    const image = $(el).find("img").attr("src") || "";

    const roblox =
      $(el).find("a:contains('Roblox Page')").attr("href") ||
      "https://www.roblox.com/catalog";

    const tryon =
      $(el).find("a:contains('Try On')").attr("href") || roblox;

    let sale = [];
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

async function send(item) {
  if (sent.has(item.id)) return;

  sent.add(item.id);
  saveDB();

  await axios.post(WEBHOOK, {
    embeds: [{
      color: 3447003,
      title: item.name,
      description:
`🌐 [Roblox Page](${item.roblox})
👕 [Try On](${item.tryon})`,
      thumbnail: { url: item.image },
      fields: [
        { name: "Sale Locations", value: item.sale },
        { name: "Quantity", value: item.qty, inline: true },
        { name: "Creator", value: item.creator, inline: true }
      ],
      timestamp: new Date()
    }]
  });

  console.log("Sent:", item.name);
}

async function monitor() {
  try {
    const items = await getItems();

    console.log("Items found:", items.length);

    for (const item of items) {
      await send(item);
    }

  } catch (err) {
    console.log("===== ERROR =====");
    console.log("Message:", err.message);

    if (err.response) {
      console.log("Status:", err.response.status);
      console.log("StatusText:", err.response.statusText);
    }

    if (err.code) {
      console.log("Code:", err.code);
    }

    console.log("=================");
  }
}

console.log("Bot Running...");
setInterval(monitor, CHECK_DELAY);
monitor();
