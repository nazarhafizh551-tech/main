const { Client, GatewayIntentBits, EmbedBuilder } = require('discord.js');
const axios = require('axios');
const cheerio = require('cheerio');
const fs = require("fs");

const client = new Client({
  intents: [GatewayIntentBits.Guilds]
});

// ===== CONFIG =====
const CHANNEL_ID = process.env.CHANNEL_ID;
const CHECK_INTERVAL = 30000; // 30 detik (cepat tapi aman)
const DATA_FILE = "data.json";

// ===== LOAD DATA =====
let posted = new Set();
if (fs.existsSync(DATA_FILE)) {
  const data = JSON.parse(fs.readFileSync(DATA_FILE));
  posted = new Set(data);
}

// ===== SAVE DATA =====
function saveData() {
  fs.writeFileSync(DATA_FILE, JSON.stringify([...posted]));
}

// ===== FETCH DETAIL =====
async function getItemDetails(url) {
  try {
    const { data } = await axios.get(url, { timeout: 10000 });
    const $ = cheerio.load(data);

    const name = $("h1").first().text().trim();

    let limit = "Unknown";
    let quantity = "Unknown";
    let creator = "Unknown";
    let availability = "Catalog";
    let locations = [];

    $("div").each((i, el) => {
      const text = $(el).text();

      if (text.includes("Limit")) limit = text.replace(/[^0-9]/g, "");
      if (text.includes("Quantity")) quantity = text.replace(/[^0-9]/g, "");
      if (text.includes("Creator")) creator = text.replace("Creator", "").trim();
      if (text.includes("In-Game")) availability = "In-Game Only";
    });

    $("li").each((i, el) => {
      const loc = $(el).text().trim();
      if (loc.length > 4 && loc.length < 60) {
        locations.push("• " + loc);
      }
    });

    const image = $("img").first().attr("src");

    return {
      name,
      limit,
      quantity,
      creator,
      availability,
      locations: locations.slice(0, 5),
      image
    };

  } catch (err) {
    console.log("Detail error:", err.message);
    return null;
  }
}

// ===== MAIN CHECK =====
async function checkUGC() {
  try {
    console.log("🔍 Checking UGC...");

    const { data } = await axios.get("https://www.rolimons.com/free-roblox-limiteds", {
      timeout: 10000
    });

    const $ = cheerio.load(data);

    let links = [];

    $("a").each((i, el) => {
      const href = $(el).attr("href");
      if (href && href.includes("/item/")) {
        links.push("https://www.rolimons.com" + href);
      }
    });

    links = [...new Set(links)].slice(0, 10);

    for (let link of links) {
      if (posted.has(link)) continue;

      const item = await getItemDetails(link);
      if (!item || !item.name) continue;

      posted.add(link);
      saveData();

      const embed = new EmbedBuilder()
        .setAuthor({
          name: "Rolimon's",
          iconURL: "https://www.rolimons.com/static/rolimons_logo.png"
        })
        .setTitle(item.name)
        .setURL(link)
        .setColor(0x4f8cff)
        .setThumbnail(item.image)

        .setDescription(
          `✨ **UGC Went Limited**\n` +
          `⛔ **Limit ${item.limit}**\n` +
          `🎮 **${item.availability}**\n` +
          `🌐 [Roblox Page](${link})`
        )

        .addFields(
          {
            name: "Sale Locations",
            value: item.locations.join("\n") || "Unknown",
            inline: false
          },
          {
            name: "Price",
            value: "FREE",
            inline: true
          },
          {
            name: "Quantity",
            value: item.quantity,
            inline: true
          },
          {
            name: "Creator",
            value: item.creator,
            inline: false
          }
        )
        .setTimestamp();

      try {
        const channel = await client.channels.fetch(CHANNEL_ID);
        await channel.send({ embeds: [embed] });
        console.log("✅ Sent:", item.name);
      } catch (err) {
        console.log("Send error:", err.message);
      }

      await new Promise(r => setTimeout(r, 2000)); // anti rate limit
    }

  } catch (err) {
    console.log("Main error:", err.message);
  }
}

// ===== READY =====
client.once("ready", () => {
  console.log(`🚀 Online sebagai ${client.user.tag}`);
  setInterval(checkUGC, CHECK_INTERVAL);
});

// ===== LOGIN =====
client.login(process.env.TOKEN);
