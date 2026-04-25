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
        json.dump(list(sent_set)[-2000:], f)

sent_items = load_sent_items()

async def scrape_free_ugc():
    url = "https://www.rolimons.com/free-roblox-limiteds"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                print(f"[{datetime.now(UTC)}] ❌ Gagal fetch halaman Rolimons: {resp.status}")
                return []
            html = await resp.text()
    
    soup = BeautifulSoup(html, 'html.parser')
    lines = [line.strip() for line in soup.get_text(separator="\n").splitlines() if line.strip()]
    
    items = []
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Filter ketat: nama item biasanya unik, panjang, dan tidak mengandung kata kunci sampah
        if (len(line) > 10 and 
            not re.search(r'^\d+ ?/ ?\d+$', line) and
            not any(k in line.lower() for k in [
                "stock", "flex ugc codes", "providing statistics", "roblox trading", 
                "most available", "newest added", "search", "limiteds table", 
                "withdraw", "consent", "terms", "privacy"
            ])):
            
            name = line.strip()
            stock = "Limited"
            location = "Flex UGC Codes"
            time_ago = ""
            
            # Ambil data di 10 baris berikutnya
            for j in range(1, 11):
                if i + j >= len(lines):
                    break
                nxt = lines[i + j].strip()
                if re.search(r'^\d+ ?/ ?\d+$', nxt):
                    stock = nxt
                elif "Flex UGC Codes" in nxt or "roblox.com/games" in nxt:
                    location = "Flex UGC Codes"
                elif any(x in nxt.lower() for x in ["minutes ago", "hours ago", "ago"]):
                    time_ago = nxt
            
            # Hanya ambil jika nama terlihat valid (bukan judul halaman)
            if not re.search(r'^\d+$', name) and len(name.split()) >= 1:
                items.append({
                    "name": name[:220],
                    "stock": stock,
                    "location": location,
                    "time": time_ago
                })
                i += 6  # loncat agar tidak duplikat
            else:
                i += 1
        else:
            i += 1
    
    print(f"[{datetime.now(UTC)}] ✅ Ditemukan {len(items)} item free UGC potensial.")
    return items[:15]

@tasks.loop(minutes=CHECK_INTERVAL)
async def check_free_limiteds():
    global sent_items
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("❌ Channel tidak ditemukan!")
        return

    print(f"[{datetime.now(UTC)}] 🔍 Memeriksa Free UGC Limiteds dari Rolimons...")
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
            print(f"✅ Terkirim → {item_name[:80]}...")
        except Exception as e:
            print(f"❌ Gagal kirim embed: {e}")

    if notified > 0:
        save_sent_items(sent_items)
        print(f"Total notifikasi baru: {notified}")
    else:
        print("Tidak ada item baru yang belum dikirim.")

@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} online! Cek setiap {CHECK_INTERVAL} menit.")
    check_free_limiteds.start()

bot.run(TOKEN)
