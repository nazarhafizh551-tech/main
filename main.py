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
        json.dump(list(sent_set)[-1500:], f)

sent_items = load_sent_items()

async def scrape_free_ugc():
    url = "https://www.rolimons.com/free-roblox-limiteds"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                print(f"[{datetime.now(UTC)}] ❌ Gagal fetch halaman: {resp.status}")
                return []
            html = await resp.text()
    
    soup = BeautifulSoup(html, 'html.parser')
    lines = [line.strip() for line in soup.get_text(separator="\n").splitlines() if line.strip()]
    
    items = []
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Deteksi nama item (pola yang lebih ketat)
        if (len(line) > 8 and 
            not re.search(r'^\d+/\d+$', line) and
            not any(k in line.lower() for k in ["stock", "flex ugc codes", "minutes ago", "hours ago", "ago", "providing statistics", "roblox trading"])):
            
            name = line.strip()
            stock = "Limited"
            location = "Flex UGC Codes"
            time_ago = ""
            
            # Ambil data berikutnya
            for j in range(1, 10):
                if i + j >= len(lines):
                    break
                nxt = lines[i + j]
                if re.search(r'^\d+ ?/ ?\d+$', nxt):
                    stock = nxt
                elif "Flex UGC Codes" in nxt or "roblox.com/games" in nxt:
                    location = "Flex UGC Codes"
                elif "Lucky Box" in nxt:
                    location = "Lucky Box Free UGC"
                elif any(x in nxt for x in ["minutes ago", "hours ago", "ago"]):
                    time_ago = nxt
            
            items.append({
                "name": name[:200],
                "stock": stock,
                "location": location,
                "time": time_ago
            })
            i += 5   # loncat lebih jauh supaya tidak duplikat
        else:
            i += 1
    
    print(f"[{datetime.now(UTC)}] ✅ Ditemukan {len(items)} item free UGC.")
    return items[:12]  # ambil 12 item terbaru

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
        
        footer = "Rolimons • Ambil secepatnya sebelum stock habis!"
        if item.get("time"):
            footer = f"Rolimons • {item['time']} • Ambil secepatnya!"
        
        embed.set_footer(text=footer)

        try:
            await channel.send("@everyone **New Free Limited UGC Terdeteksi!** 🚨", embed=embed)
            sent_items.add(item_name)
            notified += 1
            print(f"✅ Terkirim: {item_name[:70]}...")
        except Exception as e:
            print(f"❌ Gagal kirim: {e}")

    if notified > 0:
        save_sent_items(sent_items)
        print(f"Total notifikasi baru: {notified}")
    else:
        print("Tidak ada item baru.")

@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} online! Cek setiap {CHECK_INTERVAL} menit.")
    check_free_limiteds.start()

bot.run(TOKEN)
