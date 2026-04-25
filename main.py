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

# Environment Variables dari Railway
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "5"))  # dalam menit

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
        json.dump(sent_list[-500:], f)  # batasi 500 item

sent_items = load_sent_items()

async def scrape_free_ugc():
    url = "https://www.rolimons.com/free-roblox-limiteds"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                print(f"[{datetime.now(UTC)}] Error fetching Rolimons: {resp.status}")
                return []
            html = await resp.text()
    
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    current_item = None
    
    # Ambil semua teks dan proses baris per baris
    lines = soup.get_text(separator="\n").splitlines()
    
    for line in lines:
        line = line.strip()
        if not line or len(line) < 5:
            continue
        
        # Deteksi nama item baru (biasanya nama UGC yang unik)
        if any(x in line.lower() for x in ["scythe", "crown", "wings", "backpack", "hat", "jacket", "bow", "aura"]) or ("(" in line and ")" in line):
            if current_item and current_item.get("name"):
                items.append(current_item)
            
            current_item = {
                "name": line,
                "stock": "Limited",
                "location": "Flex Your UGC Limiteds Game / Lucky Box",
                "time": "Recently Added"
            }
            continue
        
        if current_item:
            if any(keyword in line for keyword in ["Stock", "Left", "/", "hours ago", "minutes ago"]):
                current_item["stock"] = line
            elif "roblox.com/games/" in line or "Flex" in line or "Lucky" in line:
                current_item["location"] = line
    
    if current_item and current_item.get("name"):
        items.append(current_item)
    
    # Ambil 15 item terbaru
    return items[:15]

@tasks.loop(minutes=CHECK_INTERVAL)
async def check_free_limiteds():
    global sent_items
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print(f"[{datetime.now(UTC)}] Channel ID {CHANNEL_ID} tidak ditemukan!")
        return

    print(f"[{datetime.now(UTC)}] Memeriksa new Free UGC Limiteds...")
    new_items = await scrape_free_ugc()
    notified = 0

    for item in new_items:
        item_name = item.get("name", "").strip()
        if not item_name or item_name in sent_items:
            continue

        embed = discord.Embed(
            title="🌙 New Free UGC Limited!",
            description=f"**{item_name}**",
            color=0x8B00FF,
            timestamp=datetime.now(UTC)
        )
        
        embed.add_field(name="UGC Type", value="⭐ UGC Limited Accessory / Item", inline=False)
        embed.add_field(name="Stock", value=item.get("stock", "Limited Stock"), inline=True)
        embed.add_field(name="Platform", value="🎮 In-Game Only", inline=True)
        
        embed.add_field(name="Sale Locations", 
                       value=f"• {item.get('location', 'Flex Your UGC Limiteds Game')}\n• Lucky Box / Purchase Game", 
                       inline=False)
        
        embed.add_field(name="Price", value="**FREE**", inline=True)
        embed.add_field(name="Quantity", value=item.get("stock", "Unknown"), inline=True)
        embed.add_field(name="Creator", value="Community Creators", inline=False)
        
        embed.set_footer(text="Data from Rolimons • Snipe cepat sebelum habis!")

        try:
            await channel.send("@everyone **New Free Limited UGC Terdeteksi!** 🚨", embed=embed)
            sent_items.append(item_name)
            notified += 1
            print(f"[{datetime.now(UTC)}] Notifikasi terkirim: {item_name}")
        except Exception as e:
            print(f"[{datetime.now(UTC)}] Gagal kirim embed: {e}")

    if notified > 0:
        save_sent_items(sent_items)
        print(f"[{datetime.now(UTC)}] Total notifikasi baru: {notified}")

@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} online! Monitoring Free UGC Limited setiap {CHECK_INTERVAL} menit.")
    if not check_free_limiteds.is_running():
        check_free_limiteds.start()

bot.run(TOKEN)
