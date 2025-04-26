import discord
from discord.ext import commands
import matplotlib.pyplot as plt
from io import BytesIO
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Ambil token dari .env file
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True  # Enable reaction tracking

bot = commands.Bot(command_prefix="!", intents=intents)

assignments = {}

# Function to generate graph
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

# When the bot is ready
@bot.event
async def on_ready():
    print(f'✅ Bot {bot.user} sudah online LAA BODOO!')

# Reaction event to mark assignment as completed
@bot.event
async def on_reaction_add(reaction, user):
    if user == bot.user:  # Ignore the bot's own reactions
        return
    
    # Check if the reaction is the ✅ emoji
    if reaction.emoji == "✅":
        # Look for the assignment based on the message
        for tajuk, info in assignments.items():
            if reaction.message.embeds and reaction.message.embeds[0].title == f"📚 Assignment: {tajuk}":
                # Add user to the "siap" list
                if user.name not in info["siap"]:
                    info["siap"].append(user.name)
                    info["jumlah_markah"] += info["markah"]  # Add marks when completed
                    await reaction.message.channel.send(f"✅ Assignment `{tajuk}` telah ditandakan sebagai siap oleh {user.name}.")
                else:
                    await reaction.message.channel.send(f"Assignment `{tajuk}` telah siap lebih awal oleh {user.name}.")
                break

# !menu command
@bot.command(name="menu")
async def menu(ctx):
    embed = discord.Embed(title="📖 Menu - Panduan Command", color=0x3498db)
    embed.add_field(name="📚 !tambahassignment", value="Gunakan command ini untuk menambah assignment baru. Format dan Contoh: `!tambahassignment \"Computer Network\" \"2025-04-22 23:59\" \"Kena buat Tutorial 3 -Dalam Ulearn\"" , inline=False)
    embed.add_field(name="📋 !tengokassignment", value="Gunakan command ini untuk melihat senarai assignment yang ada.", inline=False)
    embed.add_field(name="📈 !tunjukprogress", value="Gunakan command ini untuk melihat carta markah progress assignment.", inline=False)
    await ctx.send(embed=embed)

# !tambahassignment command
@bot.command(name="tambahassignment")
async def tambahassignment(ctx, tajuk: str, due_date: str, deskripsi: str):
    if "Admin" not in [role.name for role in ctx.author.roles]:
        await ctx.send("❌ Anda tidak mempunyai akses untuk menambah assignment. Hanya admin sahaja boleh.")
        return

    try:
        due_date_obj = datetime.strptime(due_date, '%Y-%m-%d %H:%M')  # Convert tarikh & masa ke objek datetime
    except ValueError:
        await ctx.send("Format tarikh salah! Guna: 'YYYY-MM-DD HH:MM'")
        return

    # Tetapkan markah tetap 5
    markah = 5

    assignments[tajuk] = {
        "deskripsi": deskripsi,
        "siap": [],
        "belum_siap": [],
        "markah": markah,
        "jumlah_markah": 0,
        "due_date": due_date_obj
    }

    embed = discord.Embed(title=f"📚 Assignment: {tajuk}", description=deskripsi, color=0x00ff00)
    embed.add_field(name="Due Date", value=due_date_obj.strftime('%Y-%m-%d %H:%M'), inline=False)
    embed.set_footer(text="Tekan ✅ kalau dah siap!")
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("✅")

    await ctx.send(f"Assignment `{tajuk}` berjaya ditambah dengan markah tetap 5!")

# !removeassignment command (for admin)
@bot.command(name="removeassignment")
async def removeassignment(ctx, tajuk: str):
    if "Admin" not in [role.name for role in ctx.author.roles]:
        await ctx.send("❌ Anda tidak mempunyai akses untuk membuang assignment. Hanya admin sahaja boleh.")
        return

    if tajuk not in assignments:
        await ctx.send(f"Assignment `{tajuk}` tidak wujud.")
        return

    del assignments[tajuk]
    await ctx.send(f"Assignment `{tajuk}` berjaya dibuang!")

# !tengokassignment command
@bot.command(name="tengokassignment")
async def tengokassignment(ctx):
    if not assignments:
        await ctx.send("Tiada assignment aktif.")
        return

    embed = discord.Embed(title="📋 Senarai Assignment", color=0x3498db)
    for tajuk, info in assignments.items():
        siap_list = ", ".join(info["siap"]) if info["siap"] else "Tiada lagi"
        embed.add_field(name=tajuk, value=f"{info['deskripsi']}\n✅ Siap: {siap_list}\nDue Date: {info['due_date'].strftime('%Y-%m-%d %H:%M')}", inline=False)

    await ctx.send(embed=embed)

# !tunjukprogress command
@bot.command(name="tunjukprogress")
async def tunjukprogress(ctx):
    buf = cipta_carta_markah()
    await ctx.send(file=discord.File(buf, "progress.png"))

# Run the bot
bot.run(TOKEN)
