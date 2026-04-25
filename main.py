import discord
from discord.ext import commands, tasks
import aiohttp
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime, UTC

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "3"))

DATA_FILE = "free_ugc_sent.json"

def load_sent_items():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_sent_items(sent_set):
    with open(DATA_FILE, "w") as f:
        json.dump(list(sent_set)[-1000:], f)

sent_items = load_sent_items()

async def scrape_free_ugc():
    url = "https://www.rolimons.com/free-roblox-limiteds"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                print(f"[{datetime.now(UTC)}] ❌ Gagal fetch: {resp.status}")
                return []
            html = await resp.text()
    
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    
    # Ambil semua teks dan split per baris
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    
    i = 0
    while i < len(lines) - 3:
        line = lines[i]
        
        # Deteksi nama item (baris panjang yang bukan "Stock", "Flex", "minutes ago", dll)
        if (len(line) > 15 and 
            not any(k in line for k in ["Stock", "Flex UGC", "minutes ago", "hours ago", "ago", "Newest Added", "Search"]) and
            not re.match(r'^\d+/\d+$', line)):
            
            name = line
            stock = "Limited"
            location = "Flex UGC Codes"
            
            # Ambil stock dan location di baris berikutnya
            for j in range(1, 6):
                if i + j >= len(lines):
                    break
                next_line = lines[i + j]
                if "/" in next_line and any(c.isdigit() for c in next_line):
                    stock = next_line.strip()
                elif "Flex UGC Codes" in next_line or "roblox.com/games" in next_line:
                    location = "Flex UGC Codes"
                elif "Lucky Box" in next_line:
                    location = "Lucky Box Free UGC"
            
            items.append({"name": name[:150], "stock": stock, "location": location})
            i += 3  # skip beberapa baris agar tidak duplikat
        else:
            i += 1
    
    print(f"[{datetime.now(UTC)}] Ditemukan {len(items)} item potensial.")
    return items[:15]  # ambil 15 teratas (newest)

@tasks.loop(minutes=CHECK_INTERVAL)
async def check_free_limiteds():
    global sent_items
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("❌ Channel tidak ditemukan!")
        return

    print(f"[{datetime.now(UTC)}] 🔍 Memeriksa Free UGC Limiteds...")
    new_items = await scrape_free_ugc()
    notified = 0

    for item in new_items:
        item_name = item["name"].strip()
        if not item_name or item_name in sent_items:
            continue

        embed = discord.Embed(
            title="🌙 New Free UGC Limited!",
            description=f"**{item_name}**",
            color=0x8B00FF,
            timestamp=datetime.now(UTC)
        )
        
        embed.add_field(name="Stock", value=item["stock"], inline=True)
        embed.add_field(name="Platform", value="🎮 In-Game Only", inline=True)
        embed.add_field(name="Sale Locations", value=f"• {item['location']}", inline=False)
        embed.add_field(name="Price", value="**FREE**", inline=True)
        embed.add_field(name="Creator", value="Various UGC Creators", inline=False)
        
        embed.set_footer(text="Rolimons • Ambil secepatnya sebelum stock habis!")

        try:
            await channel.send("@everyone **New Free Limited UGC Terdeteksi!** 🚨", embed=embed)
            sent_items.add(item_name)
            notified += 1
            print(f"✅ Terkirim: {item_name}")
        except Exception as e:
            print(f"❌ Gagal kirim: {e}")

    if notified > 0:
        save_sent_items(sent_items)
        print(f"Total notifikasi baru: {notified}")
    else:
        print("Tidak ada item baru yang terdeteksi.")

@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} online! Cek setiap {CHECK_INTERVAL} menit.")
    check_free_limiteds.start()

bot.run(TOKEN)
