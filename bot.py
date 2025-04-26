import discord
from discord.ext import commands
import matplotlib.pyplot as plt
from io import BytesIO
from datetime import datetime
import json
import os
from dotenv import load_dotenv
from discord.ui import View, Button
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

class MenuView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Progress Saya", style=discord.ButtonStyle.primary, custom_id="progress_button")
    async def progress_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user.name
        total_markah = 0
        siap_assignments = []

        for tajuk, info in assignments.items():
            if user in info['siap']:
                total_markah += info['markah']
                siap_assignments.append(tajuk)

        if not siap_assignments:
            await interaction.response.send_message(f"❌ {user}, anda belum siapkan sebarang assignment.", ephemeral=True)
            return

        embed = discord.Embed(title=f"📈 Progress {user}", color=0x2ecc71)
        embed.add_field(name="Jumlah Markah", value=f"{total_markah} markah", inline=False)
        embed.add_field(name="Assignment Siap", value="\n".join(siap_assignments), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Leaderboard", style=discord.ButtonStyle.success, custom_id="leaderboard_button")
    async def leaderboard_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        leaderboard_data = {}

        for tajuk, info in assignments.items():
            for user in info['siap']:
                if user not in leaderboard_data:
                    leaderboard_data[user] = 0
                leaderboard_data[user] += info['markah']

        if not leaderboard_data:
            await interaction.response.send_message("❌ Tiada data leaderboard.", ephemeral=True)
            return

        sorted_leaderboard = sorted(leaderboard_data.items(), key=lambda x: x[1], reverse=True)

        embed = discord.Embed(title="🏆 Leaderboard Assignment", color=0xf1c40f)
        for idx, (user, markah) in enumerate(sorted_leaderboard, start=1):
            embed.add_field(name=f"{idx}. {user}", value=f"{markah} markah", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

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
    view = MenuView()

    embed = discord.Embed(title="📖 Menu - Panduan Command", color=0x3498db)
    embed.add_field(name="📚 !tambah", value="Tambah assignment baru. Format: !tambah \"Tajuk\" \"YYYY-MM-DD HH:MM\" \"Deskripsi\" (Admin sahaja)", inline=False)
    embed.add_field(name="📋 !tengok", value="Lihat senarai assignment.", inline=False)
    embed.add_field(name="📈 !tunjukprogress", value="Tunjuk carta progress markah.", inline=False)
    embed.add_field(name="✏️ !edit", value="Edit assignment. Format: !edit \"Tajuk Lama\" \"Tajuk Baru\" \"YYYY-MM-DD HH:MM\" \"Deskripsi Baru\" (Admin sahaja)", inline=False)
    embed.add_field(name="🗑️ !padam", value="Padam assignment. Format: !padam \"Tajuk\" (Admin sahaja)", inline=False)
    embed.add_field(name="✅ !siap", value="Tandakan assignment siap. Format: !siap \"Tajuk\"", inline=False)
    embed.add_field(name="📊 Butang Progress Saya", value="Tunjuk markah keseluruhan kamu dan assignment yang sudah siap.", inline=False)
    embed.add_field(name="🏆 Butang Leaderboard", value="Tunjuk leaderboard untuk melihat kedudukan siapa markah paling tinggi di kalangan BITA.", inline=False)
    embed.add_field(
        name="📊 Permarkahan",
        value=(
            "Sistem markah berdasarkan bila assignment siap:\n\n"
            "• Siap lebih 5 hari sebelum due date = 10 markah\n"
            "• Siap antara 2 hingga 4 hari sebelum due date = 5 markah\n"
            "• Siap 1 hari hingga 1 saat sebelum due date = 1 markah\n"
            "• Lebih lewat dari due date = -10 markah"
        ),
        inline=False
    )

    await ctx.send(embed=embed, view=view)


@bot.command(name="tambah")
async def tambahassignment(ctx, tajuk: str, due_date: str, deskripsi: str):
    if "Admin" not in [role.name for role in ctx.author.roles]:
        await ctx.send("❌ Hanya admin boleh tambah assignment.")
        return
    try:
        due_date_obj = datetime.strptime(due_date, '%Y-%m-%d %H:%M')
    except ValueError:
        await ctx.send("❌ Format tarikh salah! Guna: YYYY-MM-DD HH:MM")
        return
    markah = 0
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

@bot.command(name="edit")
async def editassignment(ctx, tajuk_lama: str, tajuk_baru: str, due_date: str, deskripsi: str):
    if "Admin" not in [role.name for role in ctx.author.roles]:
        await ctx.send("❌ Hanya admin boleh edit assignment.")
        return
    if tajuk_lama not in assignments:
        await ctx.send(f"❌ Assignment {tajuk_lama} tak jumpa.")
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
    await ctx.send(f"✅ Assignment {tajuk_lama} berjaya diedit ke {tajuk_baru}.")


@bot.command(name="padam")
async def padamassignment(ctx, tajuk: str):
    if "Admin" not in [role.name for role in ctx.author.roles]:
        await ctx.send("❌ Hanya admin boleh padam assignment.")
        return
    if tajuk not in assignments:
        await ctx.send(f"❌ Assignment {tajuk} tak jumpa.")
        return
    del assignments[tajuk]
    save_assignments()
    await ctx.send(f"✅ Assignment {tajuk} berjaya dipadam!")


from datetime import datetime

@bot.command(name="siap")
async def siapassignment(ctx, tajuk: str):
    if tajuk not in assignments:
        await ctx.send(f"❌ Assignment {tajuk} tak jumpa.")
        return
    
    # Mengambil due_date assignment
    due_date = assignments[tajuk]['due_date']
    
    if ctx.author.name in assignments[tajuk]['siap']:
        await ctx.send(f"✅ Anda dah siap assignment {tajuk}.")
        return
    
    # Menambah nama pengguna pada senarai siap
    assignments[tajuk]['siap'].append(ctx.author.name)
    
    # Kirakan berapa hari awal atau lewat dari due date
    now = datetime.now()
    days_before_due = (due_date - now).days
    
    # Jika submit awal, akan dapat markah penuh, jika lewat markah akan dikurangkan
    if days_before_due >= 0:
        status = f"Siap {days_before_due} hari awal"
        assignments[tajuk]['jumlah_markah'] += assignments[tajuk]['markah']
    else:
        status = f"Siap {abs(days_before_due)} hari lewat"
        assignments[tajuk]['jumlah_markah'] += assignments[tajuk]['markah'] - (abs(days_before_due) * 2)  # Contoh penalti 2 markah setiap hari lewat
    
    # Simpan kemaskini assignments
    save_assignments()
    
    await ctx.send(f"✅ {ctx.author.name} telah siap assignment {tajuk}! {status}.")


@bot.command(name="tengok")
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



bot.run("TOKEN")
