import asyncio
import os
import json
import urllib.request
import discord
from discord.ext import commands, tasks

SERVER_IP = "http://194.45.197.192:30120"
TOTAL_RESOURCES = 219

# يقبل التوكن من متغيرات البيئة أو يمكنك كتابته مباشرة هنا بين القوسين
BOT_TOKEN = os.getenv("DISCORD_TOKEN") or "ضع_التوكن_هنا_إذا_لم_تستخدم_ENV"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

monitor_channel = None
status_message = None
last_state = None  # None / "OFFLINE" / "ONLINE"
displayed_count = 0

def get_resources():
    try:
        req = urllib.request.Request(
            f"{SERVER_IP}/info.json", 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                resources = data.get("resources", [])
                return len(resources)
        return None
    except Exception:
        return None

@bot.event
async def on_ready():
    print(f"✅ تم تسجيل الدخول بنجاح باسم البوت: {bot.user}")

@tasks.loop(seconds=2)
async def check_server_task():
    global status_message, last_state, displayed_count, monitor_channel

    if monitor_channel is None:
        return

    current_real = get_resources()

    # الحالة الأولى: السيرفر أوفلاين
    if current_real is None:
        if last_state != "OFFLINE":
            last_state = "OFFLINE"
            displayed_count = 0
            embed = discord.Embed(
                title="🔴 حالة السيرفر",
                description="❌ **السيرفر مغلق أو غير متاح حالياً.**",
                color=discord.Color.red()
            )
            if status_message is None:
                status_message = await monitor_channel.send(embed=embed)
            else:
                await status_message.edit(embed=embed)

    # الحالة الثانية: السيرفر أونلاين
    else:
        # إرسال إشعار لحظة تشغيل السيرفر
        if last_state == "OFFLINE" or last_state is None:
            await monitor_channel.send("🔔 @everyone **تنبيه:** السيرفر أشتغل الآن! جاري تحميل الملفات...")
            last_state = "ONLINE"

        # زيادة العدّ تدريجياً حتى يصل للعدد الحقيقي للملفات
        if displayed_count < current_real:
            displayed_count = min(displayed_count + 10, current_real)

        progress_percent = int((displayed_count / TOTAL_RESOURCES) * 100)
        status_text = "✅ اكتمل التحميل" if displayed_count >= TOTAL_RESOURCES else "⏳ جاري تشغيل الملفات..."

        embed = discord.Embed(
            title="🟢 FiveM Live Resource Tracker",
            color=discord.Color.green()
        )
        embed.add_field(name="📦 الملفات المحملة", value=f"`{displayed_count} / {TOTAL_RESOURCES}` ({progress_percent}%)", inline=False)
        embed.add_field(name="⚙️ الحالة", value=status_text, inline=False)

        if status_message is None:
            status_message = await monitor_channel.send(embed=embed)
        else:
            try:
                await status_message.edit(embed=embed)
            except Exception:
                pass

# امر بدء المراقبة
@bot.command(name="start_monitor")
async def start_monitor(ctx):
    global monitor_channel, status_message, last_state, displayed_count
    
    if check_server_task.is_running():
        await ctx.send("⚠️ المراقبة شغالة بالفعل في السيرفر!")
        return

    monitor_channel = ctx.channel
    status_message = None
    last_state = None
    displayed_count = 0

    check_server_task.start()
    await ctx.send("🚀 **تم تشغيل أمر مراقبة السيرفر بنجاح!**")

# امر إيقاف المراقبة
@bot.command(name="stop_monitor")
async def stop_monitor(ctx):
    global monitor_channel, status_message

    if check_server_task.is_running():
        check_server_task.stop()
        monitor_channel = None
        status_message = None
        await ctx.send("🛑 **تم إيقاف المراقبة.**")
    else:
        await ctx.send("⚠️ المراقبة متوقفة بالفعل!")

if __name__ == "__main__":
    bot.run(BOT_TOKEN)
