require("dotenv").config();

const { Client, GatewayIntentBits, EmbedBuilder } = require('discord.js');
const axios = require('axios');
const cheerio = require('cheerio');

const client = new Client({
  intents: [GatewayIntentBits.Guilds]
});

const posted = new Set();

async function getItemDetails(url) {
  try {
    const { data } = await axios.get(url);
    const $ = cheerio.load(data);

    const name = $("h1").first().text().trim();

    let details = {
      name,
      limit: "Unknown",
      quantity: "Unknown",
      creator: "Unknown",
      price: "FREE",
      availability: "Unknown",
      locations: [],
      image: $("img").first().attr("src")
    };

    $("div").each((i, el) => {
      const text = $(el).text();

      if (text.includes("Limit")) details.limit = text.replace("Limit", "").trim();
      if (text.includes("Quantity")) details.quantity = text.replace("Quantity", "").trim();
      if (text.includes("Creator")) details.creator = text.replace("Creator", "").trim();
      if (text.includes("In-Game")) details.availability = "In-Game Only";
    });

    $("li").each((i, el) => {
      const loc = $(el).text().trim();
      if (loc.length > 3) details.locations.push("• " + loc);
    });

    return details;

  } catch (err) {
    console.error("Detail error:", err.message);
    return null;
  }
}

async function checkUGC() {
  try {
    const { data } = await axios.get("https://www.rolimons.com/free-roblox-limiteds");
    const $ = cheerio.load(data);

    let links = [];

    $("a").each((i, el) => {
      const href = $(el).attr("href");
      if (href && href.includes("/item/")) {
        links.push("https://www.rolimons.com" + href);
      }
    });

    links = [...new Set(links)].slice(0, 5);

    for (let link of links) {
      if (posted.has(link)) continue;

      const item = await getItemDetails(link);
      if (!item) continue;

      posted.add(link);

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
          `🌐 [Roblox Page](${link}) | 👕 Try On`
        )

        .addFields(
          {
            name: "Sale Locations",
            value: item.locations.join("\n") || "Unknown",
            inline: false
          },
          {
            name: "Price",
            value: item.price,
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
        );

      const channel = await client.channels.fetch(process.env.CHANNEL_ID);
      await channel.send({ embeds: [embed] });
    }

  } catch (err) {
    console.error("Main error:", err.message);
  }
}

client.once("ready", () => {
  console.log(`Online sebagai ${client.user.tag}`);
  setInterval(checkUGC, 60000);
});

client.login(process.env.TOKEN);
