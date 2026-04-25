import discord
from discord.ext import commands, tasks
import aiohttp
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime, UTC

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "3"))  # cek setiap 3 menit

DATA_FILE = "free_ugc_sent.json"

def load_sent_items():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_sent_items(sent_list):
    with open(DATA_FILE, "w") as f:
        json.dump(sent_list[-800:], f)

sent_items = load_sent_items()

async def scrape_free_ugc():
    url = "https://www.rolimons.com/free-roblox-limiteds"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0 Safari/537.36"
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                print(f"[{datetime.now(UTC)}] Gagal mengambil halaman: {resp.status}")
                return []
            html = await resp.text()
    
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    
    # Cara scraping yang lebih baik (mencari card/item blocks)
    cards = soup.find_all("div", class_=lambda x: x and ("item" in x.lower() or "card" in x.lower() or "entry" in x.lower()))
    
    if not cards:
        # Fallback: ambil semua teks tebal atau baris yang mengandung nama item
        lines = [line.strip() for line in soup.get_text(separator="\n").splitlines() if line.strip()]
        current = {}
        for line in lines:
            if len(line) > 10 and any(k in line.lower() for k in ["scythe", "crown", "wings", "hat", "back", "jacket", "code", "stock"]):
                if current.get("name"):
                    items.append(current)
                current = {"name": line, "stock": "Limited", "location": "Flex Your UGC Limiteds Game"}
            elif current and ("Stock" in line or "/" in line and any(c.isdigit() for c in line)):
                current["stock"] = line
            elif current and ("roblox.com/games" in line or "Flex" in line or "Lucky" in line):
                current["location"] = line
        if current.get("name"):
            items.append(current)
    else:
        # Jika menemukan card, ambil teks di dalamnya (placeholder)
        for card in cards[:15]:
            text = card.get_text(strip=True, separator=" | ")
            if text and len(text) > 15:
                items.append({"name": text[:150], "stock": "Limited", "location": "Flex UGC Game"})
    
    return items[:12]

@tasks.loop(minutes=CHECK_INTERVAL)
async def check_free_limiteds():
    global sent_items
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print(f"[{datetime.now(UTC)}] ❌ Channel ID {CHANNEL_ID} tidak ditemukan atau bot belum join server!")
        return

    print(f"[{datetime.now(UTC)}] 🔍 Memeriksa Free UGC Limiteds...")
    new_items = await scrape_free_ugc()
    notified = 0

    for item in new_items:
        item_name = item.get("name", "").strip()[:100]
        if not item_name or item_name in sent_items:
            continue

        embed = discord.Embed(
            title="🌙 New Free UGC Limited!",
            description=f"**{item_name}**",
            color=0x8B00FF,
            timestamp=datetime.now(UTC)
        )
        
        embed.add_field(name="Stock", value=item.get("stock", "Limited"), inline=True)
        embed.add_field(name="Platform", value="🎮 In-Game Only", inline=True)
        embed.add_field(name="Sale Locations", 
                       value=f"• {item.get('location', 'Flex Your UGC Limiteds Game')}", 
                       inline=False)
        embed.add_field(name="Price", value="**FREE**", inline=True)
        embed.add_field(name="Creator", value="Community", inline=False)
        
        embed.set_footer(text="Rolimons • Snipe sekarang!")

        try:
            await channel.send("@everyone **New Free Limited UGC Terdeteksi!** 🚨", embed=embed)
            sent_items.append(item_name)
            notified += 1
            print(f"[{datetime.now(UTC)}] ✅ Notifikasi terkirim → {item_name}")
        except Exception as e:
            print(f"[{datetime.now(UTC)}] ❌ Gagal kirim: {e}")

    if notified > 0:
        save_sent_items(sent_items)
        print(f"[{datetime.now(UTC)}] Total notifikasi baru: {notified}")
    else:
        print(f"[{datetime.now(UTC)}] Tidak ada item baru yang terdeteksi.")

@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} online! Cek setiap {CHECK_INTERVAL} menit.")
    check_free_limiteds.start()

bot.run(TOKEN)
