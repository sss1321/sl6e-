import asyncio
import os
import json
import urllib.request
import discord
from discord import app_commands
from discord.ext import commands, tasks

SERVER_IP = "http://194.45.197.192:30120"
TOTAL_RESOURCES = 219

BOT_TOKEN = os.getenv("DISCORD_TOKEN") or "ضع_التوكن_هنا_إذا_لم_تستخدم_ENV"

intents = discord.Intents.default()
intents.message_content = True

class Client(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # تسجيل وتزامن أوامر السلاش (Slash Commands) مع ديسكورد
        await self.tree.sync()
        print("✅ تم تزامن أوامر السلاش (Slash Commands) بنجاح!")

bot = Client()

monitor_channel = None
status_message = None
last_state = None  # "OFFLINE", "ONLINE"
displayed_count = 0

def get_resources():
    try:
        req = urllib.request.Request(
            f"{SERVER_IP}/info.json", 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=1) as response:
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

# التحديث كل نصف ثانية لمواكبة تشغيل الملفات
@tasks.loop(seconds=0.5)
async def check_server_task():
    global status_message, last_state, displayed_count, monitor_channel

    if monitor_channel is None:
        return

    current_real = get_resources()

    # 1. حالة السيرفر طافي / برتيل / رسترت
    if current_real is None:
        if last_state != "OFFLINE":
            last_state = "OFFLINE"
            displayed_count = 0
            
            # رسالة تنبيه كبيرة وواضحة جداً
            alert_embed = discord.Embed(
                title="🚨🚨 تنبيه عاجل: برتيل / رسترت 🚨🚨",
                description=(
                    "====================================\n"
                    "⚠️ **السيرفر غير متاح حالياً!**\n\n"
                    "🔴 **الحالة:** طافي / جاري إعادة التشغيل (Restart)\n"
                    "===================================="
                ),
                color=discord.Color.red()
            )
            await monitor_channel.send(content="@everyone", embed=alert_embed)

            # إمبد المراقبة الثابت
            embed = discord.Embed(
                title="🔴 حالة السيرفر: مغلق (Offline)",
                description="❌ **السيرفر غير متاح حالياً (برتيل / جاري الرسترت)**",
                color=discord.Color.red()
            )
            if status_message is None:
                status_message = await monitor_channel.send(embed=embed)
            else:
                await status_message.edit(embed=embed)

    # 2. حالة السيرفر شغال (أونلاين)
    else:
        # عند اشتغال السيرفر فوراً
        if last_state == "OFFLINE" or last_state is None:
            online_embed = discord.Embed(
                title="✅✅ اشتغل السيرفر الآن ✅✅",
                description="🚀 **بدأ السيرفر بالعمل وجاري تحميل وتجميع الملفات...**",
                color=discord.Color.green()
            )
            await monitor_channel.send(content="@everyone", embed=online_embed)
            last_state = "ONLINE"

        # مواكبة الملفات الحقيقية
        if displayed_count < current_real:
            step = max(1, int((current_real - displayed_count) / 2))
            displayed_count += step

        progress_percent = int((displayed_count / TOTAL_RESOURCES) * 100)
        
        # شريط تقدم بلمس بصري ممتاز
        blocks = int(progress_percent / 10)
        progress_bar = "🟩" * blocks + "⬛" * (10 - blocks)

        status_text = "✅ **اكتمل تحميل جميع الملفات والسيرفر جاهز لدخول اللاعبين!**" if displayed_count >= TOTAL_RESOURCES else "⏳ **جاري تشغيل وتحميل ملفات السيرفر...**"

        embed = discord.Embed(
            title="🟢 FiveM Live Resource Tracker",
            color=discord.Color.green()
        )
        embed.add_field(
            name="📦 الملفات المحملة حالياً", 
            value=f"```\n{displayed_count} / {TOTAL_RESOURCES} ({progress_percent}%)\n```\n{progress_bar}", 
            inline=False
        )
        embed.add_field(name="⚙️ الحالة التشغيلية", value=status_text, inline=False)

        if status_message is None:
            status_message = await monitor_channel.send(embed=embed)
        else:
            try:
                await status_message.edit(embed=embed)
            except Exception:
                pass

# أمر السلاش لبدء المراقبة: /start_monitor
@bot.tree.command(name="start_monitor", description="تشغيل مراقبة السيرفر والملفات")
async def start_monitor(interaction: discord.Interaction):
    global monitor_channel, status_message, last_state, displayed_count
    
    if check_server_task.is_running():
        await interaction.response.send_message("⚠️ المراقبة شغالة بالفعل!", ephemeral=True)
        return

    monitor_channel = interaction.channel
    status_message = None
    last_state = None
    displayed_count = 0

    check_server_task.start()
    await interaction.response.send_message("🚀 **تم تشغيل المراقبة بنجاح!**")

# أمر السلاش لإيقاف المراقبة: /stop_monitor
@bot.tree.command(name="stop_monitor", description="إيقاف مراقبة السيرفر")
async def stop_monitor(interaction: discord.Interaction):
    global monitor_channel, status_message

    if check_server_task.is_running():
        check_server_task.stop()
        monitor_channel = None
        status_message = None
        await interaction.response.send_message("🛑 **تم إيقاف المراقبة.**")
    else:
        await interaction.response.send_message("⚠️ المراقبة متوقفة بالفعل!", ephemeral=True)

if __name__ == "__main__":
    bot.run(BOT_TOKEN)
