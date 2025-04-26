import discord
from discord.ext import commands
import matplotlib.pyplot as plt
from io import BytesIO
from datetime import datetime
import json
import os
from dotenv import load_dotenv
from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def hello():
    return "Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=5000)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()  # Start Flask server in a separate thread
    import bot  # This will run your actual Discord bot code

# Load environment variables from .env file
load_dotenv()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)

assignments = {}

DATA_FILE = 'assignments.json'
LEADERBOARD_FILE = 'leaderboard.json'

# Function untuk load data dari file
def load_assignments():
    global assignments
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            for tajuk, info in data.items():
                info['due_date'] = datetime.strptime(info['due_date'], '%Y-%m-%d %H:%M')
            assignments = data

# Function untuk save data ke file
def save_assignments():
    data = {}
    for tajuk, info in assignments.items():
        data[tajuk] = info.copy()
        data[tajuk]['due_date'] = info['due_date'].strftime('%Y-%m-%d %H:%M')
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)
    save_leaderboard()

# Function untuk save leaderboard ke file
def save_leaderboard():
    leaderboard_data = []
    for tajuk, info in assignments.items():
        for user in info["siap"]:
            due_date = info['due_date']
            current_time = datetime.now()
            days_before_due = (due_date - current_time).days
            if days_before_due < 0:
                markah = -10
            elif days_before_due >= 5:
                markah = 10
            elif 2 <= days_before_due < 5:
                markah = 5
            elif 1 <= days_before_due < 2:
                markah = 1
            else:
                markah = 1

            leaderboard_data.append({
                "user": user,
                "tajuk": tajuk,
                "markah": markah,
                "days_before_due": days_before_due,
                "total_markah": assignments[tajuk]["jumlah_markah"] + markah
            })
    with open(LEADERBOARD_FILE, 'w') as f:
        json.dump(leaderboard_data, f, indent=4)

# Function untuk load leaderboard
def load_leaderboard():
    if os.path.exists(LEADERBOARD_FILE):
        with open(LEADERBOARD_FILE, 'r') as f:
            return json.load(f)
    return []

# Function untuk cipta carta progress
def cipta_carta_markah():
    labels = [tajuk for tajuk in assignments.keys()]
    marks = [assignment["jumlah_markah"] for assignment in assignments.values()]

    fig, ax = plt.subplots()
    ax.barh(labels, marks, color='skyblue')
    ax.set_xlabel('Jumlah Markah')
    ax.set_ylabel('Assignments')
    ax.set_title('Progress Markah Assignment')

    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    return buf

@bot.event
async def on_ready():
    load_assignments()
    load_leaderboard()
    print(f'✅ Bot {bot.user} sudah online!')

@bot.event
async def on_reaction_add(reaction, user):
    if user == bot.user:
        return
    
    if reaction.emoji == "✅":
        for tajuk, info in assignments.items():
            if reaction.message.embeds and reaction.message.embeds[0].title == f"📚 Assignment: {tajuk}":
                if user.name not in info["siap"]:
                    info["siap"].append(user.name)
                    info["jumlah_markah"] += info["markah"]
                    await reaction.message.channel.send(f"✅ Assignment `{tajuk}` telah ditandakan sebagai siap oleh {user.name}.")
                    save_assignments()
                else:
                    await reaction.message.channel.send(f"⚠️ Assignment `{tajuk}` sudah ditanda siap oleh {user.name}.")
                break

@bot.command(name="menu")
async def menu(ctx):
    embed = discord.Embed(title="📖 Menu - Panduan Command", color=0x3498db)
    embed.add_field(name="📚 !tambahassignment", value="Tambah assignment baru. Format: !tambahassignment \"Tajuk\" \"YYYY-MM-DD HH:MM\" \"Deskripsi\" (Admin sahaja)", inline=False)
    embed.add_field(name="📋 !tengokassignment", value="Lihat senarai assignment.", inline=False)
    embed.add_field(name="📈 !tunjukprogress", value="Tunjuk carta progress markah.", inline=False)
    embed.add_field(name="📊 !progress", value="Tunjuk leaderboard untuk siapa yang siap assignment paling awal dan markah mereka.", inline=False)
    embed.add_field(name="✏️ !editassignment", value="Edit assignment. Format: !editassignment \"Tajuk Lama\" \"Tajuk Baru\" \"YYYY-MM-DD HH:MM\" \"Deskripsi Baru\" (Admin sahaja)", inline=False)
    embed.add_field(name="🗑️ !padamassignment", value="Padam assignment. Format: !padamassignment \"Tajuk\" (Admin sahaja)", inline=False)
    embed.add_field(name="✅ !siapassignment", value="Tandakan assignment siap. Format: !siapassignment \"Tajuk\"", inline=False)
    embed.add_field(name="📊 Permarkahan", value="Sistem markah berdasarkan bila assignment siap:\n\n"
                                                     "• Siap lebih 5 hari sebelum due date = 10 markah\n"
                                                     "• Siap antara 2 hingga 4 hari sebelum due date = 5 markah\n"
                                                     "• Siap 1 hari hingga 1 saat sebelum due date = 1 markah\n"
                                                     "• Lebih lewat dari due date = -10 markah", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="tambahassignment")
async def tambahassignment(ctx, tajuk: str, due_date: str, deskripsi: str):
    if "Admin" not in [role.name for role in ctx.author.roles]:
        await ctx.send("❌ Hanya admin boleh tambah assignment.")
        return
    try:
        due_date_obj = datetime.strptime(due_date, '%Y-%m-%d %H:%M')
    except ValueError:
        await ctx.send("❌ Format tarikh salah! Guna: YYYY-MM-DD HH:MM")
        return
    markah = 5
    assignments[tajuk] = {
        "deskripsi": deskripsi,
        "siap": [],
        "belum_siap": [],
        "markah": markah,
        "jumlah_markah": 0,
        "due_date": due_date_obj
    }
    save_assignments()
    embed = discord.Embed(title=f"📚 Assignment: {tajuk}", description=deskripsi, color=0x00ff00)
    embed.add_field(name="Due Date", value=due_date_obj.strftime('%Y-%m-%d %H:%M'), inline=False)
    embed.set_footer(text="Tekan ✅ kalau dah siap!")
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("✅")

@bot.command(name="editassignment")
async def editassignment(ctx, tajuk_lama: str, tajuk_baru: str, due_date: str, deskripsi: str):
    if "Admin" not in [role.name for role in ctx.author.roles]:
        await ctx.send("❌ Hanya admin boleh edit assignment.")
        return
    if tajuk_lama not in assignments:
        await ctx.send(f"❌ Assignment `{tajuk_lama}` tak jumpa.")
        return
    try:
        due_date_obj = datetime.strptime(due_date, '%Y-%m-%d %H:%M')
    except ValueError:
        await ctx.send("❌ Format tarikh salah! Guna: YYYY-MM-DD HH:MM")
        return
    assignments[tajuk_baru] = assignments.pop(tajuk_lama)
    assignments[tajuk_baru]['deskripsi'] = deskripsi
    assignments[tajuk_baru]['due_date'] = due_date_obj
    save_assignments()
    await ctx.send(f"✅ Assignment `{tajuk_lama}` berjaya diedit ke `{tajuk_baru}`.")

@bot.command(name="padamassignment")
async def padamassignment(ctx, tajuk: str):
    if "Admin" not in [role.name for role in ctx.author.roles]:
        await ctx.send("❌ Hanya admin boleh padam assignment.")
        return
    if tajuk not in assignments:
        await ctx.send(f"❌ Assignment `{tajuk}` tak jumpa.")
        return
    del assignments[tajuk]
    save_assignments()
    await ctx.send(f"✅ Assignment `{tajuk}` berjaya dipadam!")

@bot.command(name="siapassignment")
async def siapassignment(ctx, tajuk: str):
    if tajuk not in assignments:
        await ctx.send(f"❌ Assignment `{tajuk}` tak jumpa.")
        return
    if ctx.author.name in assignments[tajuk]['siap']:
        await ctx.send(f"✅ Anda dah siap assignment `{tajuk}`.")
        return
    assignments[tajuk]['siap'].append(ctx.author.name)
    assignments[tajuk]['jumlah_markah'] += assignments[tajuk]['markah']
    save_assignments()
    await ctx.send(f"✅ {ctx.author.name} telah siap assignment `{tajuk}`!")

@bot.command(name="tengokassignment")
async def tengokassignment(ctx):
    if not assignments:
        await ctx.send("📭 Tiada assignment lagi.")
        return
    embed = discord.Embed(title="📋 Senarai Assignment", color=0x3498db)
    for tajuk, info in assignments.items():
        siap_list = ", ".join(info["siap"]) if info["siap"] else "Tiada lagi"
        embed.add_field(name=tajuk, value=f"{info['deskripsi']}\n✅ Siap: {siap_list}\nDue Date: {info['due_date'].strftime('%Y-%m-%d %H:%M')}", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="tunjukprogress")
async def tunjukprogress(ctx):
    buf = cipta_carta_markah()
    await ctx.send(file=discord.File(buf, "progress.png"))

@bot.command(name="progress")
async def progress(ctx):
    leaderboard = load_leaderboard()
    if not leaderboard:
        await ctx.send("❌ Tiada user lagi dalam leaderboard.")
        return
    leaderboard.sort(key=lambda x: x["total_markah"], reverse=True)
    embed = discord.Embed(title="🏆 Leaderboard Assignment", color=0x3498db)
    for entry in leaderboard:
        days_text = f"{entry['days_before_due']} hari awal" if entry['days_before_due'] >= 0 else f"{abs(entry['days_before_due'])} hari lewat"
        embed.add_field(
            name=f"{entry['user']} - {entry['tajuk']}",
            value=f"Markah: {entry['markah']} (Siap {days_text})\nJumlah Markah: {entry['total_markah']}",
            inline=False
        )
    await ctx.send(embed=embed)

bot.run(TOKEN)
