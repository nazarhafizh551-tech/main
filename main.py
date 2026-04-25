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
                print(f"[{datetime.now(UTC)}] ❌ Gagal fetch: {resp.status}")
                return []
            html = await resp.text()
    
    soup = BeautifulSoup(html, 'html.parser')
    lines = [line.strip() for line in soup.get_text(separator="\n").splitlines() if line.strip()]
    
    items = []
    i = 0
    while i < len(lines) - 3:
        line = lines[i]
        
        # Deteksi nama item (pola ketat: bukan stock, bukan flex, bukan deskripsi situs)
        if (len(line) > 8 and 
            not re.search(r'^\d+ ?/ ?\d+$', line) and
            "Flex UGC Codes" not in line and
            not any(k in line.lower() for k in ["stock", "providing statistics", "roblox trading", "most available", "newest added", "search"])):
            
            name = line.strip()
            stock = "Limited"
            location = "Flex UGC Codes"
            time_ago = ""
            
            # Ambil stock, location, dan time di baris berikutnya
            for j in range(1, 10):
                if i + j >= len(lines):
                    break
                nxt = lines[i + j]
                if re.search(r'^\d+ ?/ ?\d+$', nxt) or "Stock" in nxt:
                    stock = nxt
                elif "Flex UGC Codes" in nxt:
                    location = "Flex UGC Codes"
                elif any(x in nxt.lower() for x in ["minutes ago", "hours ago", "ago"]):
                    time_ago = nxt
            
            items.append({
                "name": name[:200],
                "stock": stock,
                "location": location,
                "time": time_ago
            })
            i += 6   # loncat cukup jauh supaya tidak ambil sampah
        else:
            i += 1
    
    print(f"[{datetime.now(UTC)}] ✅ Ditemukan {len(items)} item free UGC dari Rolimons.")
    return items[:15]

@tasks.loop(minutes=CHECK_INTERVAL)
async def check_free_limiteds():
    global sent_items
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("❌ Channel ID tidak ditemukan!")
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
        
        footer = f"Rolimons • Ambil secepatnya sebelum stock habis!"
        if item.get("time"):
            footer = f"Rolimons • {item['time']} • Ambil secepatnya!"
        
        embed.set_footer(text=footer)

        try:
            await channel.send("@everyone **New Free Limited UGC Terdeteksi!** 🚨", embed=embed)
            sent_items.add(item_name)
            notified += 1
            print(f"✅ Terkirim → {item_name[:80]}...")
        except Exception as e:
            print(f"❌ Gagal kirim: {e}")

    if notified > 0:
        save_sent_items(sent_items)
        print(f"Total notifikasi baru: {notified}")
    else:
        print("Tidak ada item baru yang belum pernah dikirim.")

@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} online! Cek setiap {CHECK_INTERVAL} menit.")
    check_free_limiteds.start()

bot.run(TOKEN)
