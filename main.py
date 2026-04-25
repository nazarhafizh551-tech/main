import discord
from discord.ext import commands, tasks
import aiohttp
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Environment Variables (akan diisi di Railway)
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))  # ID channel Discord
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "5"))  # menit

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
        json.dump(sent_list[-500:], f)  # simpan maksimal 500 item terakhir

sent_items = load_sent_items()

async def scrape_free_ugc():
    url = "https://www.rolimons.com/free-roblox-limiteds"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                print(f"Error fetching page: {resp.status}")
                return []
            html = await resp.text()
    
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    
    # Parsing berdasarkan struktur teks Rolimons (item per baris)
    text_blocks = soup.get_text(separator="\n").splitlines()
    current_item = None
    
    for line in text_blocks:
        line = line.strip()
        if not line or line.startswith("http") or "Stock" in line or line.startswith("Free Roblox"):
            continue
        
        # Deteksi nama item baru (biasanya baris dengan nama panjang atau kode)
        if any(keyword in line.lower() for keyword in ["scythe", "crown", "hat", "backpack", "jacket", "bow"]) or "(" in line:
            if current_item and current_item.get("name"):
                items.append(current_item)
            
            current_item = {
                "name": line,
                "stock": "Limited",
                "location": "Flex UGC Codes / Game",
                "time": "Recently"
            }
            continue
        
        if "Stock" in line or "/" in line and any(c.isdigit() for c in line):
            if current_item:
                current_item["stock"] = line
        elif "roblox.com/games/" in line or "Flex UGC" in line or "Lucky Box" in line:
            if current_item:
                current_item["location"] = line
    
    if current_item and current_item.get("name"):
        items.append(current_item)
    
    return items[:20]  # Ambil maksimal 20 item terbaru

@tasks.loop(minutes=CHECK_INTERVAL)
async def check_free_limiteds():
    global sent_items
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("Channel not found!")
        return

    print(f"[{datetime.utcnow()}] Checking for new free UGC limiteds...")
    new_items = await scrape_free_ugc()
    notified = 0

    for item in new_items:
        item_name = item.get("name", "").strip()
        if not item_name or item_name in sent_items:
            continue

        embed = discord.Embed(
            title="🌙 New Free UGC Limited!",
            description=f"**{item_name}**",
            color=0x8B00FF,  # Ungu goth
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="UGC Type", value="⭐ UGC Back / Hat / Accessory Limited", inline=False)
        embed.add_field(name="Stock", value=item.get("stock", "Limited"), inline=True)
        embed.add_field(name="In-Game Only", value="🎮 In-Game Only", inline=True)
        
        embed.add_field(name="Sale Locations", 
                       value=f"• {item.get('location', 'Flex UGC Codes / Lucky Box Game')}", 
                       inline=False)
        
        embed.add_field(name="Price", value="**FREE**", inline=True)
        embed.add_field(name="Quantity", value=item.get("stock", "10"), inline=True)
        embed.add_field(name="Creator", value="Community / Various", inline=False)
        
        embed.set_footer(text="Sourced from Rolimons • Snipe fast before stock runs out!")

        try:
            await channel.send("@everyone **New Free Limited UGC Detected!** 🚨", embed=embed)
            sent_items.append(item_name)
            notified += 1
        except Exception as e:
            print(f"Failed to send message: {e}")

    if notified > 0:
        save_sent_items(sent_items)
        print(f"Sent {notified} new notification(s)")

@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} is online and ready!")
    if not check_free_limiteds.is_running():
        check_free_limiteds.start()

bot.run(TOKEN)
