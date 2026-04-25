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
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "3"))

DATA_FILE = "free_ugc_sent.json"

def load_sent_items():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return set(json.load(f))   # pakai set biar lebih cepat
        except:
            return set()
    return set()

def save_sent_items(sent_set):
    with open(DATA_FILE, "w") as f:
        json.dump(list(sent_set)[-1000:], f)

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
    items = []
    
    # Scraping yang lebih akurat berdasarkan struktur card saat ini
    cards = soup.find_all(["div", "a"], class_=lambda x: x and any(keyword in x.lower() for keyword in ["card", "item", "entry", "flex", "stock"]))
    
    for card in cards[:20]:   # ambil 20 item teratas (Newest Added)
        text = card.get_text(strip=True, separator=" | ")
        if len(text) < 10:
            continue
            
        name = None
        stock = "Limited"
        location = "Flex UGC Codes"
        
        # Ambil nama item (biasanya baris pertama yang panjang)
        lines = [line.strip() for line in card.get_text(separator="\n").splitlines() if line.strip()]
        for line in lines:
            if len(line) > 15 and not any(k in line for k in ["Stock", "minutes ago", "hours ago", "Flex UGC"]):
                name = line
                break
        
        if not name:
            continue
            
        # Cari stock
        stock_text = card.find(string=lambda t: t and ("Stock" in t or "/" in t and any(c.isdigit() for c in t)))
        if stock_text:
            stock = stock_text.strip()
        
        # Cari lokasi
        if "Flex UGC Codes" in text:
            location = "Flex UGC Codes"
        elif "Lucky Box" in text:
            location = "Lucky Box Free UGC"
        
        items.append({
            "name": name[:120],   # batasi panjang
            "stock": stock,
            "location": location
        })
    
    print(f"[{datetime.now(UTC)}] Ditemukan {len(items)} item free UGC di halaman.")
    return items

@tasks.loop(minutes=CHECK_INTERVAL)
async def check_free_limiteds():
    global sent_items
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print(f"[{datetime.now(UTC)}] ❌ Channel ID salah atau bot belum diinvite!")
        return

    print(f"[{datetime.now(UTC)}] 🔍 Memeriksa Newest Free UGC Limiteds...")
    new_items = await scrape_free_ugc()
    notified = 0

    for item in new_items:
        item_name = item["name"].strip()
        if item_name in sent_items:
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
            print(f"[{datetime.now(UTC)}] ✅ Terkirim: {item_name}")
        except Exception as e:
            print(f"[{datetime.now(UTC)}] ❌ Gagal kirim embed: {e}")

    if notified > 0:
        save_sent_items(sent_items)
        print(f"[{datetime.now(UTC)}] Total notifikasi baru: {notified}")
    else:
        print(f"[{datetime.now(UTC)}] Tidak ada item **baru** (semua sudah pernah dikirim).")

@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} online! Monitoring Free UGC Limited setiap {CHECK_INTERVAL} menit.")
    check_free_limiteds.start()

bot.run(TOKEN)
