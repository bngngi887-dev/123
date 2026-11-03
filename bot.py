import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
import config
import database as db

# Настройка интентов
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        YOUR_GUILD_ID = 1514247399340507369 
        guild = discord.Object(id=YOUR_GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        try:
            synced = await self.tree.sync(guild=guild)
            print(f"Бот запущен. Команд синхронизировано: {len(synced)}")
        except Exception as e:
            print(f"ОШИБКА СИНХРОНИЗАЦИИ: {e}")

bot = MyBot()

# --- НАСТРОЙКА РОЛЕЙ ПО РЕАКЦИЯМ ---
MESSAGE_ID = 1567152303473959034 
REACTION_ROLES = {
    "1566449049790316605": 1567150477647417524, # Рейс
    "1566450492610187355": 1567150207815131237, # Новости
    "1566450272564158504": 1567150170393550858, # Разработка
}

# --- СОБЫТИЯ РЕАКЦИЙ ---
@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id: return
    if payload.message_id != MESSAGE_ID: return
    emoji_id = str(payload.emoji.id) if payload.emoji.id else payload.emoji.name
    if emoji_id in REACTION_ROLES:
        role_id = REACTION_ROLES[emoji_id]
        guild = bot.get_guild(payload.guild_id)
        role = guild.get_role(role_id)
        member = payload.member
        if role and member:
            try: await member.add_roles(role)
            except discord.Forbidden: pass

@bot.event
async def on_raw_reaction_remove(payload):
    if payload.user_id == bot.user.id: return
    if payload.message_id != MESSAGE_ID: return
    emoji_id = str(payload.emoji.id) if payload.emoji.id else payload.emoji.name
    if emoji_id in REACTION_ROLES:
        role_id = REACTION_ROLES[emoji_id]
        guild = bot.get_guild(payload.guild_id)
        role = guild.get_role(role_id)
        member = guild.get_member(payload.user_id)
        if role and member:
            try: await member.remove_roles(role)
            except discord.Forbidden: pass

# --- ФОРМА ЗАЯВКИ (MODAL) ---
class ApplicationModal(discord.ui.Modal, title='Заявка на рейс'):
    roblox_nick = discord.ui.TextInput(label='Ваш ник Roblox', placeholder='Например: Roblox2009', required=True)
    route = discord.ui.TextInput(label='Какой Маршрут', placeholder='Например: Бийск - Барнаул', required=True)
    date = discord.ui.TextInput(label='Дата', placeholder='Например: 30.10.2026', required=True)

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(title="📝 Новая заявка на рейс", color=0xFFFF00)
        embed.add_field(name="Игрок", value=interaction.user.mention, inline=True)
        embed.add_field(name="Ник Roblox", value=self.roblox_nick.value, inline=True)
        embed.add_field(name="Маршрут", value=self.route.value, inline=True)
        embed.add_field(name="Дата", value=self.date.value, inline=True)

        # Отправляем заявку в канал РЕГИСТРАЦИИ
        channel = bot.get_channel(config.CHANNEL_REGISTRATION_ID)
        if channel:
            req_id = await db.add_trip_request(0, str(interaction.user.id), "general")
            await channel.send(embed=embed, view=RequestView(req_id))
            await interaction.response.send_message("✅ Ваша заявка отправлена Хосту!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Ошибка: канал регистрации не настроен.", ephemeral=True)

# --- КНОПКИ ПРИНЯТИЯ/ОТКЛОНЕНИЯ ---
class RequestView(discord.ui.View):
    def __init__(self, req_id: int):
        super().__init__(timeout=None)
        self.req_id = req_id

    @discord.ui.button(label="Принять", style=discord.ButtonStyle.success, emoji="✅")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Только Хост может одобрять заявки.", ephemeral=True)
        
        await db.update_request_status(self.req_id, "approved")
        embed = interaction.message.embeds[0]
        embed.color = 0x00FF00
        embed.add_field(name="Статус", value=f"✅ Одобрено\n**Хост:** {interaction.user.mention}", inline=False)
        await interaction.message.edit(embed=embed, view=None)
        
        # Логи принятия идут в общий канал ЛОГОВ
        log_channel = bot.get_channel(config.CHANNEL_LOGS_ID)
        if log_channel:
            applicant_mention = embed.fields[0].value 
            log_embed = discord.Embed(description=f"✅ {applicant_mention}, ваша заявка одобрена хостом {interaction.user.mention}.", color=0x00FF00)
            await log_channel.send(embed=log_embed)
            
        await interaction.response.send_message("Заявка одобрена!", ephemeral=True)

    @discord.ui.button(label="Отклонить", style=discord.ButtonStyle.danger, emoji="❌")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Только Хост может отклонять заявки.", ephemeral=True)
        
        await db.update_request_status(self.req_id, "rejected")
        embed = interaction.message.embeds[0]
        embed.color = 0xFF0000
        embed.add_field(name="Статус", value=f"❌ Отклонено\n**Хост:** {interaction.user.mention}", inline=False)
        await interaction.message.edit(embed=embed, view=None)
        
        # Логи отклонения идут в общий канал ЛОГОВ
        log_channel = bot.get_channel(config.CHANNEL_LOGS_ID)
        if log_channel:
            applicant_mention = embed.fields[0].value
            log_embed = discord.Embed(description=f"❌ {applicant_mention}, ваша заявка отклонена хостом {interaction.user.mention}.", color=0xFF0000)
            await log_channel.send(embed=log_embed)
            
        await interaction.response.send_message("Заявка отклонена!", ephemeral=True)

# --- ОСТАЛЬНОЙ КОД БОТА ---
@bot.event
async def on_ready():
    await db.init_db()
    await db.init_staff_db()

def build_trip_embed(trip: dict, host_mention: str | None = None) -> discord.Embed:
    t = trip["times"]
    stops_lines = "\n".join(str(s).strip() for s in trip["stops"] if str(s).strip())
    wagons_lines = "\n".join(f"Вагон {i+1} - {w}" for i, w in enumerate(trip["wagons"]) if str(w).strip())
    extra = trip.get("extra_info", {})
    extra_lines = "\n".join([f"Ходьба по вагону - {extra.get('walk', 'только персоналу(и вип)')}", f"Обслуживание - {extra.get('service', 'да')}", f"Вагон ресторан - {extra.get('restaurant', 'нет')}", f"Вагоны для инвалидов или льготников - {extra.get('disabled', 'нет')}"])
    time_block_lines = []
    time_labels = [("open_map", "Открытие карты"), ("open_cash", "Открытие касс"), ("boarding", "Посадка"), ("boarding_end", "Конец посадки"), ("departure", "Отправление"), ("trip_end", "Приблизительное время конца рейса"), ("prep", "Подготовка к рейсу")]
    for key, label in time_labels:
        if t.get(key): time_block_lines.append(f"{label}: {t[key]}")
    time_block = "\n".join(time_block_lines)
    line = "——————————————————————————————————"
    description = f"""**Дата/Date:** {trip['date']}
**Станция отправления:** {trip['station_from']}
**Станция назначения:** {trip['station_to']}
**Перевозчик:** {trip['carrier']}
**Номер поезда:** {trip['train_number']}
**Хост:** {host_mention or trip['host_name']}
{line}
**ВРЕМЯ**
{time_block}
{line}
**ОСТАНОВКИ**
Название станции
{stops_lines}
{line}
**ВАГОНЫ**
{wagons_lines}
{line}
**ДРУГАЯ ИНФОРМАЦИЯ:**
{extra_lines}
{line}
`УВАЖАЕМЫЕ ПАССАЖИРЫ, СОБЛЮДАЙТЕ ПРАВИЛА ПЕРЕВОЗОК И ОСНОВНЫЕ ПРАВИЛА "ОАО" РПК. НА СТАНЦИЯХ С ОСТАНОВКОЙ В ОДНУ МИНУТ КАТЕГОРИЧЕСКИ ЗАПРЕЩАЕТСЯ ВЫСАЖИВАТЬСЯ. РАЗРЕШАЕТСЯ ТОЛЬКО ПОСАДКА. ТАКЖЕ, ОТПРАВЛЕНИЕ ПОЕЗДА НАЧИНАЕТСЯ ЗА 2 МИНУТЫ ДО ЕГО ОТПРАВЛЕНИЯ ПО ГРАФИКУ!!!`
"""
    embed = discord.Embed(title="РЕЙС", description=description, color=0xFF0000)
    if config.THUMBNAIL_URL: embed.set_image(url=config.THUMBNAIL_URL)
    return embed

# --- КОМАНДЫ ---

@bot.tree.command(name="рейс", description="Создать объявление о рейсе")
async def reys(
    interaction: discord.Interaction, 
    дата: str, откуда: str, куда: str, перевозчик: str, номер_поезда: str, хост: discord.Member, 
    открытие_карты: str, открытие_касс: str, посадка: str, конец_посадки: str, отправление: str, конец_рейса: str, подготовка: str, 
    остановки: str, вагоны: str, 
    канал: discord.TextChannel | None = None,
    ходьба: str = "только персоналу(и вип)", обслуживание: str = "да", ресторан: str = "нет", инвалиды: str = "нет"
):
    has_admin_role = any(r.id == 1567108963827458118 for r in interaction.user.roles)
    if not has_admin_role and not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ У вас нет прав для создания рейса.", ephemeral=True)

    times = {"open_map": открытие_карты.strip(), "open_cash": открытие_касс.strip(), "boarding": посадка.strip(), "boarding_end": конец_посадки.strip(), "departure": отправление.strip(), "trip_end": конец_рейса.strip(), "prep": подготовка.strip()}
    stops = [s.strip() for s in остановки.split(",") if s.strip()]
    wagons = [w.strip() for w in вагоны.split(",") if w.strip()]
    extra_info = {"walk": ходьба.strip(), "service": обслуживание.strip(), "restaurant": ресторан.strip(), "disabled": инвалиды.strip()}
    
    target_channel = канал or interaction.channel
    trip_data = {
        "date": дата, "station_from": откуда, "station_to": куда, "carrier": перевозчик, "train_number": номер_поезда, 
        "host_id": str(хост.id), "host_name": f"{хост.display_name}", 
        "times": times, "stops": stops, "wagons": wagons, "extra_info": extra_info, 
        "channel_id": target_channel.id if target_channel else None
    }
    
    trip_id = await db.add_trip(trip_data)
    trip = await db.get_trip(trip_id)
    
    # Отправляем основной рейс
    sent = await target_channel.send(embed=build_trip_embed(trip, хост.mention))
    await db.set_trip_message(trip_id, target_channel.id, sent.id)

    # 1. Канал РЕГИСТРАЦИИ
    reg_channel = bot.get_channel(config.CHANNEL_REGISTRATION_ID)
    if reg_channel:
        reg_embed = discord.Embed(title="📢 НАЧАЛАСЬ РЕГИСТРАЦИЯ НА РЕЙС!", color=0x00FF00)
        reg_embed.description = f"**Рейс:** {откуда} → {куда}\n**Дата:** {дата}\n**Поезд:** {номер_поезда}\n\nПодать заявку можно командой `/заявка`!"
        await reg_channel.send(embed=reg_embed)

    # 2. Канал НЕЯВОК (тот самый, который ты скинул: 1566454025417924678)
    no_show_channel = bot.get_channel(config.CHANNEL_NO_SHOW_ID)
    if no_show_channel:
        noshow_embed = discord.Embed(title="⚠️ Информация о рейсе", color=0xFFA500)
        noshow_embed.description = f"Создан рейс **{номер_поезда}** ({дата}). Если вы не сможете явиться, сообщите об этом заранее."
        await no_show_channel.send(embed=noshow_embed)

    await interaction.response.send_message(f"✅ Рейс #{trip_id} создан и анонсирован!", ephemeral=True)


@bot.tree.command(name="заявка", description="Подать заявку на рейс")
async def apply_trip(interaction: discord.Interaction):
    has_special_role = any(r.id == 1514254833563996220 for r in interaction.user.roles)
    if not has_special_role and not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ У вас нет нужной роли для подачи заявки.", ephemeral=True)
    
    await interaction.response.send_modal(ApplicationModal())


@bot.tree.command(name="отпуск", description="Подать заявку на отпуск")
async def apply_vacation(interaction: discord.Interaction, дата_начала: str, дата_конца: str, причина: str = "Не указана"):
    has_special_role = any(r.id == 1514254833563996220 for r in interaction.user.roles)
    if not has_special_role and not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ У вас нет нужной роли.", ephemeral=True)
    
    await db.add_vacation(str(interaction.user.id), дата_начала, дата_конца, причина)
    embed = discord.Embed(title="🏖️ Заявка на отпуск", color=0x00BFFF)
    embed.add_field(name="Сотрудник", value=interaction.user.mention, inline=False)
    embed.add_field(name="Период", value=f"С {дата_начала} по {дата_конца}", inline=False)
    embed.add_field(name="Причина", value=причина, inline=False)

    # Отправляем в канал ОТПУСКОВ
    channel = bot.get_channel(config.CHANNEL_VACATIONS_ID)
    if channel:
        await channel.send(embed=embed)
        await interaction.response.send_message("✅ Заявка отправлена!", ephemeral=True)
    else: await interaction.response.send_message("❌ Канал не настроен.", ephemeral=True)


@bot.tree.command(name="неявка", description="Отметить неявку")
async def no_show(interaction: discord.Interaction, сотрудник: discord.Member, причина: str):
    has_special_role = any(r.id == 1514254833563996220 for r in interaction.user.roles)
    if not has_special_role and not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("❌ Только Хост может отмечать неявку.", ephemeral=True)

    await db.add_no_show(0, str(сотрудник.id), причина)
    embed = discord.Embed(title="⚠️ Неявка", color=0xFF0000)
    embed.add_field(name="Сотрудник", value=сотрудник.mention, inline=True)
    embed.add_field(name="Причина", value=причина, inline=False)
    
    # Команда /неявка тоже кидает отчет в канал НЕЯВОК
    channel = bot.get_channel(config.CHANNEL_NO_SHOW_ID)
    if channel: await channel.send(embed=embed)
    await interaction.response.send_message("✅ Неявка зафиксирована.", ephemeral=True)

if __name__ == "__main__":
    if not config.TOKEN: raise SystemExit("Укажите DISCORD_TOKEN в файле .env")
    bot.run(config.TOKEN)