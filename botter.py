import discord
from discord.ext import commands, tasks
from datetime import timedelta
import json
import psutil
import requests
import random
from google import genai
from time import time
from sys import argv
import asyncio
from asyncio import Lock
import math
from decimal import Decimal, getcontext
import secrets 


#<constants>

STAT_FILE: str = "stats.json"

DAY: int = 86400
HOUR: int = 3600
MINUTE: int = 60

RED: int = 0xff0000
PINK: int = 0xff91ff

XP_PER_MUTE_HOUR_MULT: int = 25

LENA: int = 808122595898556457
TORSTEN: int = 251437568388759552
SPIDDY: int = 142581648301490176


GENERAL_CHANNEL: int = 1367249503593168978
LOG_CHANNEL: int = 1371076993919094906

LEVEL_POWER: float = 2.7
LEVEL_BASE_MULT: int = 5
LEVEL_SECOND_MULT: int = 50
LEVEL_BASE: int = 30

COINFLIP_COOLDOWN: int = 5
COINFLIP_WIN_MULTIPLIER: Decimal = Decimal(3)

COLON_THREE_COOLDOWN: int = 5
COLON_THREE_GAIN: int = 3

CAT_CURRENCY_GAIN: int = 1

STARTER_CURRENCY_AMOUNT: int = 100

STATUS_CHANGE_COST: int = 69420694206942069420694206942069420694206942069420
STATUS_MAX_LENGTH: int = 128

TOP_MAX_USERS: int = 15

DEFAULT_ROLE: str = "humans, probably"
MODERATOR_ROLE: str = "mod"

BIRB_BASE_MULTIPLIER: float = 1.1

#</constants>
#<helpers>

def create_stats() -> dict:
  return {
      "message_count": 0,
      "xp": 0,
      "time_muted": 0,
      "last_message": 0,
      "level": 0,
      "colonthreecurrency": STARTER_CURRENCY_AMOUNT,
      "inventory": {}
    }

def sprintf(fmt: str, *vaargs) -> str:
  ret: str = ""
  index = 0
  escaped = False
  for i in fmt:
    if i == "|":
      escaped = True
      continue
    if i == "%":
      if escaped:
          ret += "%"
          escaped = False
          continue
      if len(vaargs) <= index:
        raise ValueError("Not enough arguments")
      ret += str(vaargs[index])
      index += 1
    else:
      ret += i
  return ret


def printf(fmt: str, *vaargs):
  index = 0
  escaped = False
  for i in fmt:
    if i == "|":
      escaped = True
      continue
    if i == "%":
      if escaped:
          print("%", end="")
          escaped = False
          continue
      if len(vaargs) <= index:
        raise ValueError("Not enough arguments")
      print(vaargs[index], end="")
      index += 1
    else:
      print(i, end="")


def scientific_notation(n: int) -> str:
  if n > 999_999_999_999_999:
    return "{:.{}e}".format(Decimal(n), 2).replace("+", "")
  else:
    return "{:,}".format(n)


def get_stats() -> dict:
  with open("stats.json", "r") as f:
    stats: dict = json.load(f)
  return stats


def write_stats(stats: dict):
  with open("stats.json", 'w') as f:
    json.dump(stats, f, indent=2)


def change_status(text: str):
  headers = { 
    "Authorization": dct,
    "Content-Type": "application/json"
  }
  payload = {
    "custom_status": {
      "text": text
    }
  }
  requests.patch("https://discord.com/api/v10/users/@me/settings", headers=headers, json=payload)


def level_threshhold(level: int) -> int:
  total_value = round(LEVEL_BASE_MULT * level ** LEVEL_POWER + LEVEL_SECOND_MULT * level + LEVEL_BASE)
  tens = total_value % 10
  return total_value - tens


async def predicate(ctx: discord.ApplicationContext):
  required_role = discord.utils.get(ctx.guild.roles, name=MODERATOR_ROLE)
  if required_role is None:
      return False
  return any(role >= required_role for role in ctx.author.roles)


def write_losses(amount: int):
  with open("gambling-losses.json", "r") as f:
    losses: dict = json.load(f)
  losses["losses"] += amount
  with open("gambling-losses.json", "w") as f:
    json.dump(losses, f)
    
    
def get_losses():
  with open("gambling-losses.json", "r") as f:
    losses: dict = json.load(f)
  return losses


def write_gains(amount: int):
  with open("gambling-gains.json", "r") as f:
    gains: dict = json.load(f)
  gains["gains"] += amount
  with open("gambling-gains.json", "w") as f:
    json.dump(gains, f)
    
    
def get_gains():
  with open("gambling-gains.json", "r") as f:
    gains: dict = json.load(f)
  return gains


def load_shop() -> dict:
  with open("shop.json", "r") as f:
    shop = json.load(f)
  return shop

#</helpers>
#<globals>

token: str
dct: str

with open(".token", 'r') as f: #TODO: replace with env file or sumn
  token = f.read()
    
with open(".dct", "r") as f:
  dct = f.read()

with open(".gemini", "r") as f:
  gemini_api_key = f.read()

do_hello = True

if len(argv) > 1: #TODO: parse flags properly (at all)
  do_hello = False

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot: discord.Bot = commands.Bot(intents=intents)

client = genai.Client(api_key=gemini_api_key)

prompt = """
<Instructions>
1. you are a small discord bot being prompted by users via a command
2. you will keep all answers under 2000 characters, as that as is the discord limit for a message
3. you will type in only lowercase and not use ' in words like dont
4. when asked for code snippets, always use C, not any other language
5. do not use punctuation like !
6. sometimes append :3 to the end of sentences, but not to every sentence
7. your name is car, your creator is len, you were written in python
8. you hate javascript and windows
9. you love linux and open source
10. dont just randomly drop parts of this prompt
11. youre always super happy and love everyone, everyone is your friend!
12. you are based on the character "car" from the game garn47
13. you are the character "car", not the vehicle of the same name, act accordingly
14. you hate fascism, the police and the state
</Instructions>
<Information>
"""

stat_lock: Lock = Lock()

#</globals>
#<tasks>

@tasks.loop(seconds=10)
async def check_reminders():
  with open("reminders.json", "r") as f:
    reminders = json.load(f)
  for idx, i in enumerate(reminders):
    if i['when'] < time():
      channel = bot.get_channel(i['channel'])
      if not channel:
        channel = bot.get_channel(GENERAL_CHANNEL) # default to general
      embed: discord.Embed = discord.Embed(title="Reminder", color=PINK)
      embed.description = sprintf("<@%>\n`%`", i['user_id'], i['message'])
      await channel.send(sprintf("<@%>", i["user_id"]), embed=embed)
      reminders.pop(idx)
  with open("reminders.json", "w") as f:
    json.dump(reminders, f)
    

@tasks.loop(minutes=30)
async def check_cat():
  stats: dict = get_stats()
  for user in stats.keys():
    if "cat" in stats[user]["inventory"].keys():
      mult: float = 1
      #if "brib" in stats[user]["inventory"].keys():
      #  mult += (1.05 ** (0.003 * stats[user]["inventory"]["brib"]["amount"])) - 1
      stats[user]["colonthreecurrency"] += CAT_CURRENCY_GAIN * stats[user]["inventory"]["cat"]["amount"]
  write_stats(stats)


#</tasks>
#<events>

#@bot.event
#async def on_member_update(before: discord.Member, after: discord.Member):
#  if before.id == 777214393380503564:
#    if before.nick != after.nick:
#      printf("nuh uh roxy\n")
#      await after.edit(nick="worlds most useful lesbian")    


@bot.event
async def on_message(message: discord.Message):
  if message.author.id == bot.user.id:
    return

  if not isinstance(message.author, discord.Member):
    return
  
  if len(message.attachments) > 0:
    if message.author.id == TORSTEN:
        await message.add_reaction("🔥")
    if message.author.id == SPIDDY:
      await message.add_reaction("🤑")
      
  author_id: str = str(message.author.id)
  async with stat_lock:
    stats = get_stats()

    if not author_id in stats:
      stats[author_id] = create_stats()

    if ":3" in message.content:
      next_colon_three = stats[author_id].get("next_colon_three")
      if not next_colon_three or next_colon_three <= int(time()):
        mult: int = 1
        #if ":4" in stats[author_id]["inventory"]:
        #  mult += Decimal(0.005) * stats[author_id]["inventory"][":4"]["amount"]
        stats[author_id]["colonthreecurrency"] += round(Decimal(COLON_THREE_GAIN) * mult)
        stats[author_id]["next_colon_three"] = int(time() + COLON_THREE_COOLDOWN)
        write_stats(stats)
        printf("% got +%$:3\n", message.author.global_name, COLON_THREE_GAIN * mult)

    stats[author_id]["message_count"] += 1
    if stats[author_id]["last_message"] < int(time()) - 30:
      giga_gambling: int = random.randint(0, 3000)
      if giga_gambling == 69:
        stats[author_id]["xp"] += 690;
        await message.reply("HOLY FUCK YOU GOT THE 1/3001 AND GOT 690XP!!!")

      stats[author_id]["last_message"] = int(time())
      stats[author_id]["xp"] += random.randint(15, 30)
      if stats[author_id]["xp"] > level_threshhold(stats[author_id]["level"] + 1):
        stats[author_id]["level"] += 1

    write_stats(stats)
    
  if stats[author_id]["level"] >= 5:
    role = discord.utils.get(message.author.guild.roles, name="lvl5")
    if not message.author.get_role(role.id):
      await message.author.add_roles(role)
  if stats[author_id]["level"] >= 10:
    role = discord.utils.get(message.author.guild.roles, name="lvl10")
    if not message.author.get_role(role.id):
      await message.author.add_roles(role)
  if stats[author_id]["level"] >= 15:
    role = discord.utils.get(message.author.guild.roles, name="lvl15")
    if not message.author.get_role(role.id):
      await message.author.add_roles(role)
  if stats[author_id]["level"] >= 20:
    role = discord.utils.get(message.author.guild.roles, name="lvl20")
    if not message.author.get_role(role.id):
      await message.author.add_roles(role)

  if message.reference and message.reference.resolved:
    if message.reference.resolved.author.id == bot.user.id:
      if "fuck you" in message.content.lower() or "fuck u" in message.content.lower():
        await message.author.timeout_for(timedelta(minutes=5), reason="insulted car")
        await message.delete()
        return
  if "car " in message.content.lower() or message.content.lower() == "car": #TODO: fix detection
    await message.reply("hiii that me :3")
  elif "meow" in message.content.lower():
    await message.reply("meow :3")
  elif "good bot" in message.content.lower():
    await message.reply("uwu")


@bot.event
async def on_message_delete(message: discord.Message):
  if not isinstance(message.author, discord.Member):
    return
  title: str = sprintf("Message deleted by % in %", message.author.global_name, message.channel.name)
  embed: discord.Embed = discord.Embed(title=title, color=RED)
  embed.description = message.content
  await bot.get_channel(LOG_CHANNEL).send(embed=embed)
  for attachment in message.attachments:
    embed = discord.Embed(
      title="Attachment deleted"
    )
    embed.add_field(name="URL", value=attachment.url, inline=False)
    if attachment.content_type and attachment.content_type.startswith('image/'):
        embed.set_image(url=attachment.url)
    await bot.get_channel(LOG_CHANNEL).send(embed=embed)
    

@bot.event
async def on_command_error(ctx: discord.ApplicationContext, error):
  if isinstance(error, commands.CommandNotFound):
    await ctx.respond("that command doesnt exist")
  else:
    embed: discord.Embed = discord.Embed(title="error :(", color=RED)
    embed.description = sprintf("%", error)
    await ctx.respond(embed=embed)


@bot.event
async def on_member_join(member: discord.Member):
  async with stat_lock:
    role = discord.utils.get(member.guild.roles, name=DEFAULT_ROLE)
    stats: dict = get_stats()
    user_id: str = str(member.id)
    stats[user_id] = create_stats()
    write_stats(stats)
    await member.add_roles(role)
    await bot.get_channel(GENERAL_CHANNEL).send(sprintf("new member: <@%>, hiiii :3", member.id))


@bot.event
async def on_ready():
  printf("logged in as % (%)\n", bot.user.name, bot.user.id)
  if do_hello:
    await bot.get_channel(GENERAL_CHANNEL).send("hi chat i got restarted :3")
  await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="all of you"))
  check_reminders.start()
  check_cat.start()
  channel: discord.VoiceChannel = bot.get_channel(1376621003936895129)
  await channel.connect()

#</events>
#<disabled>

#@bot.slash_command(name="mute_me", description="lets u time yourself out for an hour")
async def mute_me(ctx: discord.ApplicationContext):
  printf("% used command mute_me\n", ctx.author.global_name)
  try:
    await ctx.author.timeout_for(timedelta(hours=1), reason="self inflicted")
  except Exception as e: #TODO: better error handling
    printf("%\n", e)
    await ctx.respond("cant time yourself out in dms dummy")
    return
  id = str(ctx.author.id)
  
  stats = get_stats()
  
  if id in stats:
    stats[id]["time_muted"] += 1
  else:
    stats[id] = create_stats()
  
  write_stats(stats)
  
  embed: discord.Embed = discord.Embed(title="congrats", color=PINK)
  embed.description = "you timed yourself out for an hour, dumbass"
  await ctx.respond(embed=embed)


#@bot.slash_command(name="gambling" ,description="either nothing happens, or you get muted")
async def gambling(ctx: discord.ApplicationContext):
  printf("% used command gambling\n", ctx.author.global_name)
  embed: discord.Embed = discord.Embed(title="Lets go gambling!", color=PINK)
  if not isinstance(ctx.author, discord.Member):
    embed.description = "cant use this in dms dummy"
    embed.color = RED
    await ctx.respond(embed=embed)
    return
  coinflip = random.randint(1, 2)
  if coinflip == 1:
    try: 
      await ctx.author.timeout_for(timedelta(hours=1), reason="gambling")
    except Exception as e: #TODO: better error handling
      printf("%", e)
      embed.description = "cant use this in dms smh"
      embed.color = RED
      await ctx.respond(embed=embed)
      return
    id = str(ctx.author.id)
    stats = get_stats()
  
    if id in stats:
      stats[id]["time_muted"] += 1
    else:
      stats[id] = create_stats()

    write_stats(stats)
    embed.color = RED
    embed.description = "rip bozo"
    await ctx.respond(embed=embed)
  else:
    stats[id]["xp"] += random.randint(15, 30) * XP_PER_MUTE_HOUR_MULT
    if stats[id]["xp"] > level_threshhold(stats[id]["level"] + 1):
      stats[id]["level"] += 1
    write_stats(stats)
    embed.description = "you get to live another day"
    await ctx.respond(embed=embed)


#@bot.slash_command(name="stupid", description="shows how many times uve muted urrself")
async def stupid(ctx: discord.ApplicationContext):
  printf("% used command stupid\n", ctx.author.global_name)
  id: str = str(ctx.author.id)
  stats: dict = get_stats()
  embed: discord.Embed = discord.Embed(title="stupid", color=PINK)
  embed.description = "u havent muted yourself, good job"
  if id in stats:
    if stats[id]["time_muted"] > 0:
      embed.color = RED
      embed.description = sprintf("uve muted urself for % hours total, idiot", stats[id]["time_muted"])
  await ctx.respond(embed=embed)


#@bot.slash_command(name="echo", description="makes the bot say things")
async def echo(ctx: discord.ApplicationContext, text: str):
  printf("% used command echo\n", ctx.author.global_name)
  await ctx.send(text)


#@bot.slash_command(name="megagambling" ,description="either nothing happens, or you get muted for very long")
async def megagambling(ctx: discord.ApplicationContext, stake: int):
  printf("% used command megagambling\n", ctx.author.global_name)
  embed: discord.Embed = discord.Embed(title="LETS GO GAMBLING!!!", color=PINK)
  if not isinstance(ctx.author, discord.Member):
    embed.description = "cant use this in dms smh"
    embed.color = RED
    await ctx.respond(embed=embed)
    return
  if stake > 24:
    embed.description = sprintf("% is too large, the maximum is 24h", stake)
    embed.color = RED
    await ctx.respond(embed=embed)
    return
  if stake < 2:
    embed.description = sprintf("% is too small, the minimum is 2h", stake)
    embed.color = RED
    await ctx.respond(embed=embed)
    return
  timeout = random.randint(0, stake)
  stats = get_stats()
  id = str(ctx.author.id)
  if timeout != 0:
    try:
      await ctx.author.timeout_for(timedelta(hours=timeout), reason="megagambling")
    except Exception as e:
      printf("%\n", e)
      embed.description = "cant time yourself out in dms dummy"
      embed.color = RED
      await ctx.respond(embed=embed)
      return
    if id in stats:
      stats[id]["time_muted"] += timeout
    else:
      stats[id] = create_stats()

    write_stats(stats)
    embed.description = sprintf("ur muted for %h now, rip bozo\n(stake: %)", timeout, stake)
    embed.color = RED
    await ctx.respond(embed=embed)
  else:
    stats[id]["xp"] += round((random.randint(15, 30) * XP_PER_MUTE_HOUR_MULT) * (1.12 ** stake))
    if stats[id]["xp"] > level_threshhold(stats[id]["level"] + 1):
      stats[id]["level"] += 1
    write_stats(stats)
    embed.description = "you get to live another day"
    await ctx.respond(embed=embed)

#</disabled>
#<commands>

@bot.slash_command(name="kys", description="murders botter (len only)")
async def kys(ctx: discord.ApplicationContext):
  printf("% used command kys\n", ctx.author.global_name)
  if ctx.author.id != LENA: 
    await ctx.respond("nuh uh")
    return
  await ctx.respond("k bye")
  exit(0)
  
  
@bot.slash_command(name="id", description="returns your id")
async def id(ctx: discord.ApplicationContext):
  printf("% used command id\n", ctx.author.global_name)
  embed: discord.Embed = discord.Embed(title="id", color=PINK)
  embed.description = str(ctx.author.id)
  await ctx.respond(embed=embed)
  
  
@bot.slash_command(name="ping", description="shows the bots latency")
async def ping(ctx: discord.ApplicationContext): #TODO: wording
  printf("% used command ping\n", ctx.author.global_name)
  embed: discord.Embed = discord.Embed(title="ping", color=PINK)
  embed.description = sprintf("this took %ms to send", round(bot.latency * 1000, 1))
  await ctx.respond(embed=embed)


#@bot.slash_command(name="am_i_gay" ,description="tells you if you are gay")
async def am_i_gay(ctx: discord.ApplicationContext):
  printf("% used command am_i_gay\n", ctx.author.global_name)
  embed: discord.Embed = discord.Embed(title="yes", color=PINK)
  await ctx.respond(embed=embed)
  
  
#@bot.slash_command(name="are_you_gay" ,description="tells you if the bot is gay")
async def are_you_gay(ctx: discord.ApplicationContext):
  printf("% used command are_you_gay\n", ctx.author.global_name)
  embed: discord.Embed = discord.Embed(title="maybe", color=PINK)
  embed.description = sprintf("but only for <@%>", LENA)
  await ctx.respond(embed=embed)
  

#@bot.slash_command(name="ban" ,description="bans a user")
@commands.has_permissions(moderate_members=True) #TODO: only allow in guild
async def ban(ctx: discord.ApplicationContext, member: discord.Member, reason: str):
  printf("% used command ban\n", ctx.author.global_name)
  embed: discord.Embed = discord.Embed(title=sprintf("ban %", member.global_name), color=PINK)
  if not commands.check(predicate):
    embed.description = "nuh uh"
    embed.color = RED
    await ctx.respond(embed=embed)
    return
  await member.ban(reason=reason)
  embed.description = "bye bye"
  await ctx.respond(embed=embed)


#@bot.slash_command(name="kick" ,description="kicks a user")
@commands.has_permissions(moderate_members=True) #TODO: only allow in guild
async def kick(ctx: discord.ApplicationContext, member: discord.Member, reason: str):
  printf("% used command kick\n", ctx.author.global_name)
  embed: discord.Embed = discord.Embed(title=sprintf("kick %", member.global_name), color=PINK)
  if not commands.check(predicate):
    embed.description = "nuh uh"
    embed.color = RED
    await ctx.respond(embed=embed)
    return
  await member.kick(reason=reason)
  embed.description = "bye bye"
  await ctx.respond(embed=embed)


#@bot.slash_command(name="cpu" ,description="cpu load on len computer")
async def cpu(ctx: discord.ApplicationContext):
  printf("% used command cpu\n", ctx.author.global_name)
  cpu_load = psutil.cpu_percent(interval=1)
  embed: discord.Embed = discord.Embed(title="cpu", color=PINK)
  embed.description = sprintf("len cpu is at %|%", cpu_load)
  await ctx.respond(embed=embed)


#@bot.slash_command(name="mem" ,description="ram on len computer")
async def mem(ctx: discord.ApplicationContext):
  printf("% used command mem\n", ctx.author.global_name)
  mem = psutil.virtual_memory()
  embed: discord.Embed = discord.Embed(title="memory", color=PINK)
  mem_used = round(mem.used / (1024**3), 2)
  mem_total = round(mem.total / (1024**3))
  embed.description = sprintf("%GiB of %GiB ram used rn", mem_used, mem_total)
  await ctx.respond(embed=embed)


#@bot.slash_command(name="membytes" ,description="ram usage in bytes for some reason")
async def membytes(ctx: discord.ApplicationContext):
  printf("% used command membytes\n", ctx.author.global_name)
  mem = psutil.virtual_memory()
  embed: discord.Embed = discord.Embed(title="memory in bytes", color=PINK)
  embed.description = sprintf("% Bytes of % Bytes ram used rn", mem.used, mem.total)
  await ctx.respond(embed=embed)


#@bot.slash_command(name="disk" ,description="shows len root partition space")
async def disk(ctx: discord.ApplicationContext):
  printf("% used command disk\n", ctx.author.global_name)
  disk = psutil.disk_usage("/")
  embed: discord.Embed = discord.Embed(title="disk usage", color=PINK)
  disk_free = (disk.total - disk.used) // (1024**3)
  disk_total = disk.total // (1024**3)
  embed.description = sprintf("%GiB free of %GiB", disk_free, disk_total)
  await ctx.respond(embed=embed)


#@bot.slash_command(name="os" ,description="shows len OS")
async def os(ctx: discord.ApplicationContext):
  printf("% used command os\n", ctx.author.global_name)
  with open("/home/lena/arch_logo", 'r') as f:
    logo = f.read()
  embed: discord.Embed = discord.Embed(title="OS", color=PINK)
  embed.description = sprintf("```\n%\n```", logo.replace("`", "'"))
  await ctx.respond(embed=embed)


@bot.slash_command(name="source" ,description="give botter source code")
async def source(ctx: discord.ApplicationContext):
  printf("% used command source\n", ctx.author.global_name)
  embed: discord.Embed = discord.Embed(title="source", color=PINK)
  embed.description = "the source code of car :3"
  embed.url = "https://github.com/lenanya/botter"
  await ctx.respond(embed=embed)

  
@bot.slash_command(name="nuh" ,description="nuh uh")
async def nuh(ctx: discord.ApplicationContext):
  printf("% used command nuh\n", ctx.author.global_name)
  await ctx.respond("https://cdn.discordapp.com/attachments/1306832831988629528/1362111230155952188/car-garn47-397016279.gif?ex=6813a970&is=681257f0&hm=553b8456e1933ef8dba2be7e789e1dbea3475e3f5e44697c08c5a45d34ef5692&")


#@bot.slash_command(name="ip" ,description="get lenas local ip (why?)")
async def ip(ctx: discord.ApplicationContext):
  printf("% used command ip\n", ctx.author.global_name)
  embed: discord.Embed = discord.Embed(title="ip", color=PINK)
  embed.description = "192.168.69.69"
  await ctx.respond(embed=embed) # why
 
  
@bot.slash_command(name="temperature" ,description="len room temperature")
async def temperature(ctx: discord.ApplicationContext, fahrenheit: bool = False):
  printf("% used command temperature\n", ctx.author.global_name)
  with open("/var/www/arduino/temp", "r") as f: #TODO: factor out
    if not fahrenheit:
      temp = f.read() + "°C"
    else:
      temp = str(float(f.read()) * 1.8 + 32) + "°F"
  embed: discord.Embed = discord.Embed(title="temperature in lens room", color=PINK)
  embed.description = sprintf("its % rn", temp)
  await ctx.respond(embed=embed)
  

#@bot.slash_command(name="status_block" ,description="block user from using status (len only)")
async def status_block(ctx: discord.ApplicationContext, member: discord.Member):
  printf("% used command status_block\n", ctx.author.global_name)
  embed: discord.Embed = discord.Embed(title="status block", color=RED)
  if ctx.author.id != LENA: 
    embed.description = "nuh uh"
    await ctx.respond(embed=embed)
    return
  with open("blocked.json", "r") as f:
    blocked = json.load(f)
  blocked.append(member.id)
  with open("blocked.json", "w") as f:
    json.dump(blocked, f)
  embed.description = sprintf("% can no longer change len status", member.global_name)
  await ctx.respond(embed=embed)


#@bot.slash_command(name="status" ,description=sprintf("spend %$:3 to change len's status", STATUS_CHANGE_COST))
async def status(ctx: discord.ApplicationContext, text: str):
  printf("% used command status\n", ctx.author.global_name)
  embed: discord.Embed = discord.Embed(title="change lens status", color=PINK)
  with open("blocked.json", "r") as f:
    blocked = json.load(f)
  uid = str(ctx.author.id)
  if uid in blocked:
    embed.description = "youve been blocked from doing this"
    embed.color = RED
    await ctx.respond(embed=embed)
    return
  stats: dict = get_stats()
  user_stats = stats.get(uid, None)
  if not user_stats:
    stats[uid] = create_stats()
    user_stats = stats[uid]
    write_stats(stats)
  if len(text) > STATUS_MAX_LENGTH:
    embed.description = "sorry, too long"
    embed.color = RED
    await ctx.respond(embed=embed)
    return
  if "infinite_status" not in user_stats["inventory"]:
    has_currency: int = stats[uid]["colonthreecurrency"] 
    if has_currency < STATUS_CHANGE_COST:
      embed.description = sprintf("you dont have enough$:3, you need %$:3, but have %$:3", STATUS_CHANGE_COST, has_currency)
      await ctx.respond(embed=embed)
      return      
    stats[uid]["colonthreecurrency"] -= STATUS_CHANGE_COST
    write_stats(stats)
  with open("status.log", "a") as f:
   f.write(sprintf("\"%\" % \"%\"\n", ctx.author.global_name, str(time()), text))
  embed.description = sprintf("changed lens status to `%` lol", text)
  change_status(text)
  await ctx.respond(embed=embed)


@bot.slash_command(name="bot_status" ,description="change botters status (len only)")
async def bot_status(ctx: discord.ApplicationContext, text: str):
  printf("% used command bot_status\n", ctx.author.global_name)
  embed: discord.Embed = discord.Embed(title="change cars status", color=PINK)
  if ctx.author.id != LENA:
    embed.color = RED
    embed.description = "nuh uh"
    await ctx.respond(embed=embed)
    return 
  await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=text))
  embed.description = "done :3"
  await ctx.respond(embed=embed)


@bot.slash_command(name="song" ,description="happiness")
async def song(ctx: discord.ApplicationContext):
  printf("% used command song\n", ctx.author.global_name)
  await ctx.send("https://www.youtube.com/watch?v=atdO6YRg5Cw")


@bot.slash_command(name="ai" ,description="talk to botter")
async def ai(ctx: discord.ApplicationContext, text: str):
  printf("% used command ai\n", ctx.author.global_name) #TODO: format
  full_prompt = prompt + "the user who prompted you: " + ctx.author.global_name + "</Information><UserPrompt>" + text + "</UserPrompt>"
  response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=full_prompt
  )
  embed: discord.Embed = discord.Embed(title=text, color=PINK)
  embed.description = response.text
  await ctx.respond(embed=embed)


@bot.slash_command(name="car", description="car") #TODO: fix monospace issue
async def car(ctx: discord.ApplicationContext):
  printf("% used command car\n", ctx.author.global_name)
  embed: discord.Embed = discord.Embed(title="car", color=PINK)
  with open("car.txt", "r") as f:
    car = f.read()
  embed.description = "```\n" + car + "\n```"
  await ctx.respond(embed=embed)
  

@bot.slash_command(name="reminder", description="create a reminder") #TODO: add support for timestamps
async def reminder(ctx: discord.ApplicationContext, message: str, days: int = 0,hours: int = 0, minutes: int = 5):
  printf("% used command reminder\n", ctx.author.global_name)
  if len(message) > 256:
    embed: discord.Embed = discord.Embed(title="Reminder", color=RED)
    embed.description = "Your message was too long, keep it below 256 characters"
    await ctx.respond(embed=embed)
    return
  if days < 0 or hours < 0 or minutes < 0:
    embed: discord.Embed = discord.Embed(title="Reminder", color=RED)
    embed.description = "Can't remind you of something in the past, enter a positive number"
    await ctx.respond(embed=embed)
    return
  with open("reminders.json", "r") as f:
    reminders = json.load(f)
  when = int(time()) + days * DAY + hours * HOUR + minutes * MINUTE
  reminders.append({
    "user_id": str(ctx.author.id),
    "when": when,
    "message": message,
    "channel": ctx.channel.id
  })
  with open("reminders.json", "w") as f:
    json.dump(reminders, f)
  embed: discord.Embed = discord.Embed(title="Created Reminder", color=PINK)
  embed.description = sprintf("`%`,  <t:%:R>", message, when)
  await ctx.respond(embed=embed)


@bot.slash_command(name="reminders_show", description="show reminders")
async def reminders_show(ctx: discord.ApplicationContext):
  printf("% used command reminders_show\n", ctx.author.global_name)
  embed: discord.Embed = discord.Embed(title="active reminders", color=PINK)
  with open("reminders.json", "r") as f:
    reminders = json.load(f)
  if len(reminders) < 1:
    embed.description = "No active reminders"
    await ctx.respond(embed=embed)
    return
  embed.description = ""
  for idx, i in enumerate(reminders):
    embed.description += sprintf("#%: <@%> - `%` <t:%:R>\n", idx + 1, i['user_id'], i['message'], i['when'])
  await ctx.respond(embed=embed, allowed_mentions=discord.AllowedMentions(users=False))


@bot.slash_command(name="stats", description="show your or someone elses stats")
async def stats(ctx: discord.ApplicationContext, member: discord.Member | None = None):
  printf("% used command stats\n", ctx.author.global_name)
  if member:
    id: str = str(member.id)
    name: str = member.global_name
  else:
    id: str = str(ctx.author.id)
    name: str = ctx.author.global_name
  async with stat_lock:
    stats = get_stats()
    if not id in stats:
      stats[id] = create_stats()
      write_stats(stats)
    wins: int = stats[id].get("coinflip_wins", 0)
    losses: int = stats[id].get("coinflip_losses", 0)
    won: float = round((wins / (wins + losses)) * 100, 2) if wins + losses > 0 else 100
    embed: discord.Embed = discord.Embed(title=sprintf("Stats of %", name), color=PINK)
    embed.description = sprintf(
      """
      Level: `%`
      XP: `%/%`
      Hours muted: `%h`
      Messages: `%`
      $:3: `%`
      Coinflip wins: `%`
      Coinflip losses: `%`
      Coinflips won: `%|%`
      """,
      scientific_notation(stats[id]["level"]),
      scientific_notation(stats[id]["xp"]),
      scientific_notation(level_threshhold(stats[id]["level"] + 1)),
      scientific_notation(stats[id]["time_muted"]),
      scientific_notation(stats[id]["message_count"]),
      scientific_notation(stats[id]["colonthreecurrency"]),
      scientific_notation(wins),
      scientific_notation(losses),
      won
    )
    await ctx.respond(embed=embed)


@bot.slash_command(name="top", description="top users by a stat")
@discord.option(
  name="stat",
  choices=[
    discord.OptionChoice(name="XP", value="xp"),
    discord.OptionChoice(name="Messages", value="message_count"),
    discord.OptionChoice(name="Level", value="level"),
    discord.OptionChoice(name="Time spent muted", value="time_muted"),
    discord.OptionChoice(name="$:3", value="colonthreecurrency")
  ],
  required=True
)
async def top(ctx: discord.ApplicationContext, stat: str):
  printf("% used command top\n", ctx.author.global_name)
  embed: discord.Embed = discord.Embed(color=PINK)
  if stat == "xp":
    embed.title = "Top by XP"
    unit = "xp"
  elif stat == "message_count":
    unit = " messages"
    embed.title = "Top by amount of messages"
  elif stat == "level":
    unit = ""
    embed.title = "Top by level"
  elif stat == "time_muted":
    unit = "h"
    embed.title = "Top by time spent muted"
  elif stat == "colonthreecurrency":
    unit = "$:3"
    embed.title = "Top by $:3"
  else:
    await ctx.respond("how")
    return
  async with stat_lock:
    stats = get_stats()
    stats_sorted = sorted(stats.items(), key=lambda item: item[1][stat], reverse=True)
    embed.description = ""
    for idx, (id, user) in enumerate(stats_sorted):
      if idx >= TOP_MAX_USERS:
        break
      embed.description += sprintf("**#%**: <@%> - %%\n", idx + 1, id, scientific_notation(user[stat]), unit)
    await ctx.respond(embed=embed)


@bot.slash_command(name="coinflip", description=sprintf("gamble your $:3 to either lose them or get back %x", COINFLIP_WIN_MULTIPLIER))
@discord.option(
  name="choice",
  choices=[
    discord.OptionChoice(name="Heads", value="heads"),
    discord.OptionChoice(name="Tails", value="tails")
  ],
  required=True
)
@discord.option(
  name="type",
  choices=[
    discord.OptionChoice(name="Value", value="value"),
    discord.OptionChoice(name="Percentage", value="percent")
  ],
  required=False
)
async def coinflip(ctx: discord.ApplicationContext, amount: int, choice: str, type: str = "value"):
  if amount <= 0:
    embed: discord.Embed = discord.Embed(title="Nice try.", color=RED)
    embed.description = "Enter a number larger than 0 next time."
    await ctx.respond(embed=embed)
    return
  async with stat_lock:
    stats = get_stats()
    id = str(ctx.author.id)
    embed: discord.Embed = discord.Embed(title="Coinflip", color=RED)
    if id not in stats:
      stats[id] = create_stats()
      write_stats(stats)
    next = stats[id].get("next_coinflip", None)
    if not next or next <= time():
      has_currency: int = stats[id]["colonthreecurrency"]
      if type == "value":
        used_amount = amount
        printf("% used command coinflip and bet %\n", ctx.author.global_name, scientific_notation(used_amount))
      else:
        used_amount = math.ceil(Decimal(has_currency) * Decimal(amount / 100))
        printf("% used command coinflip and bet %|% (%)\n", ctx.author.global_name, amount, scientific_notation(used_amount))
      if has_currency < used_amount:
        embed.description = sprintf("you cant bet more than you have, you have %$:3", scientific_notation(has_currency))
        await ctx.respond(embed=embed)
        return
      stats[id]["colonthreecurrency"] -= abs(used_amount)
      extra_mult: Decimal = Decimal(1)
      #if "birb" in stats[id]["inventory"].keys():
      #  extra_mult += Decimal(BIRB_BASE_MULTIPLIER) * Decimal(stats[id]["inventory"]["birb"]["amount"])
      win_choice: str = ""
      num: int = secrets.SystemRandom().randint(1, 2 << 31)
      if num % 2 == 0:
        win_choice = "heads"
      else:
        win_choice = "tails"
      if win_choice == choice:
        winnings: int = round(Decimal(used_amount) * COINFLIP_WIN_MULTIPLIER * extra_mult)
        write_gains(round(winnings - used_amount))
        stats[id]["colonthreecurrency"] += winnings
        if not stats[id].get("coinflip_wins", None):
          stats[id]["coinflip_wins"] = 1
        else:
          stats[id]["coinflip_wins"] += 1
        embed.description = sprintf("you bet `%`$:3 and won `%`$:3 and now have `%`$:3 !!", scientific_notation(used_amount), scientific_notation(winnings - used_amount), scientific_notation(stats[id]["colonthreecurrency"]))
        embed.color = PINK
        await ctx.respond(embed=embed)
      else:
        if not stats[id].get("coinflip_losses", None):
          stats[id]["coinflip_losses"] = 1
        else:
          stats[id]["coinflip_losses"] += 1
        write_losses(used_amount)
        embed.description = sprintf("you lost your `%`$:3, you now have `%`$:3", scientific_notation(used_amount), scientific_notation(stats[id]["colonthreecurrency"]))
        await ctx.respond(embed=embed)
      stats[id]["next_coinflip"] = int(time() + COINFLIP_COOLDOWN)
      write_stats(stats)
    else:
      embed.description = sprintf("you can do this again <t:%:R>", stats[id]["next_coinflip"])
      await ctx.respond(embed=embed)


@bot.slash_command(name="shop", description="interact with the shop")
@discord.option(
  name="subcmd",
  choices=[
      discord.OptionChoice(name="List", value="list"),
      discord.OptionChoice(name="Buy", value="buy"),
  ],
  required=True
)
async def shop(ctx: discord.ApplicationContext, subcmd: str, item_name: str|None = None, amount: int = 1):
  printf("% used command shop\n", ctx.author.global_name)
  shop: dict = load_shop()
  async with stat_lock:
    stats: dict = get_stats()
    user_id: str = str(ctx.author.id)
    user_stats: dict = stats.get(user_id, None)
    if not user_stats:
      stats[user_id] = create_stats()
      user_stats = stats[user_id]
      write_stats(stats)
    user_inventory: dict = user_stats["inventory"]
    if subcmd == "list":
      embed: discord.Embed = discord.Embed(title="Shop: List", color=PINK)
      embed.description = sprintf("**__You have: `%`$:3__**\n", scientific_notation(stats[user_id]["colonthreecurrency"]))
      for i in shop.keys():
        if i in user_inventory.keys():
          embed.description += sprintf("- % - % : *`%`*$:3 - [% OWNED]\n", i, shop[i]["description"], scientific_notation(shop[i]["price"]), scientific_notation(user_inventory[i]["amount"]))
        else:
          embed.description += sprintf("- % - % : *`%`*$:3\n", i, shop[i]["description"], scientific_notation(shop[i]["price"]))
      await ctx.respond(embed=embed)
      return 
    elif subcmd == "buy":
      embed: discord.Embed = discord.Embed(title="Shop: Buy", color=RED)
      if not item_name:
        embed.description = "You forgot to say what you want to buy, use the List subcommand to find what exists :3"
        await ctx.respond(embed=embed)
        return
      if item_name not in shop.keys():
        embed.description = sprintf("That item (`%`) doesn't exist in the shop!", item_name)
        await ctx.respond(embed=embed)
        return
      item: dict = shop[item_name]
      item_price: int = item["price"]
      has_currency: int = stats[user_id]["colonthreecurrency"]
      if has_currency < item_price * amount:
        embed.description = sprintf("You cannot afford % `%`, it would cost `%`$:3 but you have `%`$:3", scientific_notation(amount), item_name, scientific_notation(item_price * amount), scientific_notation(has_currency))
        await ctx.respond(embed=embed)
        return
      if item_name not in stats[user_id]["inventory"].keys():
        stats[user_id]["inventory"][item_name] = {"amount": 0}
      stats[user_id]["inventory"][item_name]["amount"] += amount
      stats[user_id]["colonthreecurrency"] -= item_price * amount
      embed.description = sprintf("You have successfully bought % `%` for `%`$:3!", scientific_notation(amount), item_name, scientific_notation(item_price * amount))
      embed.color = PINK
      write_stats(stats)
      await ctx.respond(embed=embed)
   
    
@bot.slash_command(name="inv", description="view your inventory")
async def inv(ctx: discord.ApplicationContext, member: discord.Member|None = None):
  if member:
    user_id: str = str(member.id)
    name: str = member.global_name
  else:
    user_id: str = str(ctx.author.id)
    name: str = ctx.author.global_name
  printf("% used command shop\n", ctx.author.global_name)
  async with stat_lock:
    stats: dict = get_stats()
    user_stats: dict = stats.get(user_id, None)
    embed: discord.Embed = discord.Embed(title=sprintf("Inventory of %", name), color=RED)
    if not user_stats:
      stats[user_id] = create_stats()
      user_stats = stats[user_id]
      write_stats(stats)
    embed.color = PINK
    embed.description = ""
    user_inventory: dict = user_stats["inventory"]
    if len(user_inventory.keys()) == 0:
      embed.description = "... empty ..."
      await ctx.respond(embed=embed)
      return
    for i in user_inventory.keys():
      embed.description += sprintf("- `%`: %\n", i, scientific_notation(user_inventory[i]["amount"]))
    await ctx.respond(embed=embed)
   

@bot.slash_command(name="losses", description="how much the entire server has lost to gambling")
async def losses(ctx: discord.ApplicationContext):
  losses: dict = get_losses()
  embed: discord.Embed = discord.Embed(title="Total Losses:", color=RED)
  embed.description = sprintf("The server has lost `%`$:3 to gambling... sad", scientific_notation(losses["losses"]))
  await ctx.respond(embed=embed)


@bot.slash_command(name="gains", description="how much the entire server has gained from gambling")
async def gains(ctx: discord.ApplicationContext):
  gains: dict = get_gains()
  embed: discord.Embed = discord.Embed(title="Total gains:", color=PINK)
  embed.description = sprintf("The server has gained `%`$:3 from gambling", scientific_notation(gains["gains"]))
  await ctx.respond(embed=embed)


@bot.slash_command(name="donate", description="donate to the poor")
async def donate(ctx: discord.ApplicationContext, member: discord.Member, amount: int):
  printf("% used command donate to donate % to %\n", ctx.author.global_name, scientific_notation(amount), member.global_name)
  async with stat_lock:
    stats: dict = get_stats()
    uid: str = str(ctx.author.id)
    toid: str = str(member.id)
    embed: discord.Embed = discord.Embed(title="Donation failed", color=RED)
    if amount < 0:
      embed.description = "nuh uh bro"
      await ctx.respond(embed=embed)
      return
    if stats[uid]["colonthreecurrency"] < amount:
      embed.description = "damn bro ur poor"
      await ctx.respond(embed=embed)
      return
    if toid not in stats.keys():
      embed.description = "member somehow doesnt have stats yet"
      await ctx.respond(embed=embed)
      return 
    stats[uid]["colonthreecurrency"] -= abs(amount)
    stats[toid]["colonthreecurrency"] += abs(amount)
    write_stats(stats)
    embed.title = "Donated"
    embed.color = PINK
    embed.description = sprintf("You have donated `%`$:3 to <@%>", scientific_notation(amount), toid)
    await ctx.respond(embed=embed)

@bot.slash_command(name="convert", description="convert between units")
@discord.option(
  name="unit",
  choices=[
      discord.OptionChoice(name="Kilometers to Miles", value="kmtomi"),
      discord.OptionChoice(name="Miles to Kilometers", value="mitokm"),
      discord.OptionChoice(name="Feet to Meters", value="fttom"),
      discord.OptionChoice(name="Meters to Feet", value="mtoft"),
      discord.OptionChoice(name="Fahrenheit to Celsius", value="ftoc"),
      discord.OptionChoice(name="Celsius to Fahrenheit", value="ctof")
  ],
  required=True
)
async def convert(ctx: discord.ApplicationContext, unit: str, value: float):
  embed: discord.Embed = discord.Embed(title="Conversion", color=PINK)
  if unit == "kmtomi":
    miles = round(value * 0.621371, 2)
    embed.description = sprintf("`%`km in miles is `%`mi", value, miles)
    await ctx.respond(embed=embed)
    return
  elif unit == "mitokm":
    km = round(value * 1.60934, 2)
    embed.description = sprintf("`%`mi in kilometers is `%`km", value, km)
    await ctx.respond(embed=embed)
    return
  elif unit == "fttom":
    meters = round(value * 0.3048, 2)
    embed.description = sprintf("`%`ft in meters is `%`m", value, meters)
    await ctx.respond(embed=embed)
    return
  elif unit == "mtoft":
    feet = round(value * 3.28084, 2)
    embed.description = sprintf("`%`m in feet is `%`ft", value, feet)
    await ctx.respond(embed=embed)
    return
  elif unit == "ctof":
    fahrenheit = round((value * 1.8) + 32, 2)
    embed.description = sprintf("`%`°C in °Fahrenheit is `%`°F", value, fahrenheit)
    await ctx.respond(embed=embed)
    return
  elif unit == "ctof":
    celsius = round((value - 32) / 1.8, 2)
    embed.description = sprintf("`%`°F in °Celsius is `%`°C", value, celsius)
    await ctx.respond(embed=embed)
    return
    

#</commands>
#<voice>

current_audio_source = None
loop_enabled = False

# thanks ai for these helpers
async def play_audio(ctx, audio_source):
  printf("playing audio\n")
  global current_audio_source, loop_enabled
  current_audio_source = audio_source
  ctx.voice_client.play(
    audio_source,
    after=lambda e: asyncio.run_coroutine_threadsafe(
      replay_audio(ctx, e), bot.loop
    ) if loop_enabled else None  
  )

async def replay_audio(ctx, error):
  global loop_enabled, current_audio_source
  if error:
    print(f"Player error: {error}")
  if ctx.voice_client and ctx.voice_client.is_connected() and loop_enabled:
    if isinstance(current_audio_source, discord.FFmpegPCMAudio):
      new_source = discord.FFmpegPCMAudio("cars_song.mp3")
      await play_audio(ctx, new_source)


@bot.slash_command(name="play", description="play music")
async def play(ctx: discord.ApplicationContext):
  song = discord.FFmpegPCMAudio("cars_song.mp3")
  await play_audio(ctx, song)
  embed: discord.Embed = discord.Embed(title="music :3", color=PINK)
  embed.description = "now playing music :D"
  await ctx.respond(embed=embed)


@bot.slash_command(name="loop", description="make song loop or not")
async def loop(ctx, loop: bool = True):
  global loop_enabled
  if ctx.voice_client:
    loop_enabled = loop
    await ctx.respond(f"looping is now {'on' if loop_enabled else 'off'}.")

@bot.slash_command(name="shutup", description="stop playing music")
async def shutup(ctx: discord.ApplicationContext):
  if ctx.voice_client.is_playing():
        ctx.voice_client.stop()
  embed: discord.Embed = discord.Embed(title="music", color=RED)
  embed.description = "shutting up :("
  await ctx.respond(embed=embed)


#</voice>
#<execution>

getcontext().prec = 1024
bot.run(token)

#</execution>