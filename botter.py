import discord
from discord.ext import commands, tasks
from datetime import timedelta
import json
import psutil
import requests
import random
from google import genai
from time import time

token: str
dct: str

def sprintf(fmt: str, *vaargs) -> str:
  ret: str = ""
  index = 0;
  escaped = False;
  for i in fmt:
    if i == "|":
      escaped = True;
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
  index = 0;
  escaped = False;
  for i in fmt:
    if i == "|":
      escaped = True;
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
      
with open(".token", 'r') as f:
  token = f.read()
    
with open(".dct", "r") as f:
  dct = f.read()

with open(".gemini", "r") as f:
  gemini_api_key = f.read()

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='#', intents=intents)

client = genai.Client(api_key=gemini_api_key)

@bot.slash_command(name="mute_me", description="lets u time yourself out for an hour")
async def mute_me(ctx: discord.ApplicationContext, hours):
  id = str(ctx.author.id)
  with open("stupid.json", "r") as f:
    idiots = json.load(f);
  if id in idiots:
    idiots[id] += int(hours)
  else:
    idiots[id] = int(hours)
  with open("stupid.json", "w") as f:
    json.dump(idiots, f)
  await ctx.author.timeout_for(timedelta(hours=int(hours)), reason="self inflicted")
  await ctx.respond("congrats, you timed yourself out for an hour, dumbass")

@bot.slash_command(name="stupid", description="shows how many times uve muted urrself")
async def stupid(ctx: discord.ApplicationContext):
  id = str(ctx.author.id)
  with open("stupid.json", "r") as f:
    idiots = json.load(f);
  if id in idiots:
    await ctx.respond(sprintf("uve muted urself for % hours total, idiot", idiots[id]))
  else:
    await ctx.respond("u havent muted urself, good job")

@bot.slash_command(name="echo", description="makes the bot say things")
async def echo(ctx: discord.ApplicationContext, text):
  await ctx.send(text)

@bot.slash_command(name="kys", description="murders botter (len only)")
async def kys(ctx: discord.ApplicationContext):
  if ctx.author.id != 808122595898556457:
    await ctx.respond("nuh uh")
    return
  await ctx.respond("k bye")
  exit(0)
  
@bot.slash_command(name="id", description="returns your id")
async def id(ctx: discord.ApplicationContext):
  await ctx.respond(ctx.author.id)
  
@bot.slash_command(name="ping", description="shows the bots latency")
async def ping(ctx: discord.ApplicationContext):
  await ctx.respond(sprintf("this took %ms to send", round(bot.latency * 1000, 1)))

@bot.slash_command(name="am_i_gay" ,description="tells you if you are gay")
async def am_i_gay(ctx: discord.ApplicationContext):
  await ctx.respond("yes")
  
@bot.slash_command(name="are_you_gay" ,description="tells you if the bot is gay")
async def are_you_gay(ctx: discord.ApplicationContext):
  await ctx.respond("only for <@808122595898556457>")

@bot.event
async def on_ready():
  printf("logged in as % (%)\n", bot.user.name, bot.user.id)
  await bot.get_channel(1367249503593168978).send("hi chat i got restarted :3")
  check_reminders.start()

async def predicate(ctx: discord.ApplicationContext):
  required_role = discord.utils.get(ctx.guild.roles, name="mod")
  if required_role is None:
      return False
  return any(role >= required_role for role in ctx.author.roles)

@bot.slash_command(name="ban" ,description="bans a user")
@commands.has_permissions(moderate_members=True)
async def ban(ctx: discord.ApplicationContext, member: discord.Member, reason):
  if not commands.check(predicate):
    await ctx.respond("nuh uh")
    return
  await member.ban(reason=reason)
  await ctx.respond("bye bye %", member.name)

@bot.slash_command(name="kick" ,description="kicks a user")
@commands.has_permissions(moderate_members=True)
async def kick(ctx: discord.ApplicationContext, member: discord.Member, reason):
  if not commands.check(predicate):
    await ctx.respond("nuh uh")
    return
  await member.kick(reason=reason)
  await ctx.respond("bye bye %", member.name)

@bot.event
async def on_member_join(member):
  role = discord.utils.get(member.guild.roles, name="humans, probably")
  await member.add_roles(role)
  await bot.get_channel(1367249503593168978).send(sprintf("new member: %, hiiii :3", member.name))

@bot.slash_command(name="cpu" ,description="cpu load on len computer")
async def cpu(ctx: discord.ApplicationContext):
  cpu_load = psutil.cpu_percent(interval=1)
  await ctx.respond(sprintf("len cpu is at %|%", cpu_load))

@bot.slash_command(name="mem" ,description="ram on len computer")
async def mem(ctx: discord.ApplicationContext):
  mem = psutil.virtual_memory()
  await ctx.respond(sprintf("%GiB of %GiB ram used rn", round(mem.used / (1024**3), 2), round(mem.total / (1024**3), 2)))

@bot.slash_command(name="membytes" ,description="ram usage in bytes for some reason")
async def membytes(ctx: discord.ApplicationContext):
  mem = psutil.virtual_memory()
  await ctx.respond(sprintf("%B of %B ram used rn", mem.used, mem.total))

@bot.slash_command(name="disk" ,description="shows len root partition space")
async def disk(ctx: discord.ApplicationContext):
  disk = psutil.disk_usage("/")
  await ctx.respond(sprintf("%GiB free of %GiB", (disk.total - disk.used) // (1024**3), disk.total // (1024**3)))

@bot.slash_command(name="os" ,description="shows len OS")
async def os(ctx: discord.ApplicationContext):
  with open("/home/lena/arch_logo", 'r') as f:
    logo = f.read()
  await ctx.respond(sprintf("```\n%\n```", logo.replace("`", "'")))

@bot.slash_command(name="source" ,description="give botter source code")
async def source(ctx: discord.ApplicationContext):
  await ctx.respond("https://github.com/lenanya/botter")
  
@bot.slash_command(name="nuh" ,description="nuh uh")
async def nuh(ctx: discord.ApplicationContext):
  await ctx.respond("https://cdn.discordapp.com/attachments/1306832831988629528/1362111230155952188/car-garn47-397016279.gif?ex=6813a970&is=681257f0&hm=553b8456e1933ef8dba2be7e789e1dbea3475e3f5e44697c08c5a45d34ef5692&")

@bot.slash_command(name="ip" ,description="get lenas local ip (why?)")
async def ip(ctx: discord.ApplicationContext):
  await ctx.respond("192.168.69.69")

@bot.slash_command(name="pwd" ,description="print current directory lena is in")
async def pwd(ctx: discord.ApplicationContext):
  with open("cwd", "r") as f:
    cwd = f.read()
  await ctx.respond(sprintf("lena is in `%`", cwd))
  
@bot.slash_command(name="temperature" ,description="len room temperature")
async def temperature(ctx: discord.ApplicationContext):
  with open("/var/www/arduino/temp", "r") as f:
    temp = f.read() + "°C"
  await ctx.respond(sprintf("lens room is % rn", temp))
  
@bot.event
async def on_command_error(ctx: discord.ApplicationContext, error):
  if isinstance(error, commands.CommandNotFound):
    await ctx.reply("that command doesnt exist")
  else:
    await ctx.reply(sprintf("error: %", error))

@bot.slash_command(name="status_block" ,description="block user from using status (len only)")
async def status_block(ctx: discord.ApplicationContext, member: discord.Member):
  if ctx.author.id != 808122595898556457:
    await ctx.respond("nuh uh")
    return
  with open("blocked.json", "r") as f:
    blocked = json.load(f)
  blocked.append(member.id)
  with open("blocked.json", "w") as f:
    json.dump(blocked, f)
  await ctx.respond(sprintf("% can no longer change len status", member.name))

@bot.slash_command(name="status" ,description="change len status")
async def status(ctx: discord.ApplicationContext, text):
  with open("blocked.json", "r") as f:
    blocked = json.load(f)
  uid = str(ctx.author.id)
  if uid in blocked:
    await ctx.respond("youve been blocked from doing this")
    return
  with open("status.json", "r") as f:
    users = json.load(f)
  if uid in users:
    if users[uid] > int(time()):
      await ctx.respond(sprintf("you can do this again <t:%:R>", users[uid]))
      return
  if len(text) > 128:
    await ctx.respond("sorry, too long")
    return
  headers = {
    "Authorization": dct,
    "Content-Type": "application/json"
  }
  payload = {
    "custom_status": {
      "text": text
    }
  }
  users[uid] = int(time()) + 86400
  with open("status.json", "w") as f:
    json.dump(users, f)
  requests.patch("https://discord.com/api/v10/users/@me/settings", headers=headers, json=payload)
  await ctx.respond(sprintf("changed lens status to \"%\" lol", text))

@bot.slash_command(name="bot_status" ,description="change botters status (len only)")
async def bot_status(ctx: discord.ApplicationContext, text: str):
  if ctx.author.id != 808122595898556457:
    await ctx.respond("nuh uh")
    return 
  await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=text))
  await ctx.respond("changed bot status uwu")

@bot.slash_command(name="song" ,description="happiness")
async def song(ctx: discord.ApplicationContext):
  await ctx.send("https://www.youtube.com/watch?v=atdO6YRg5Cw")

@bot.slash_command(name="gambling" ,description="either nothing happens, or you get muted")
async def gambling(ctx: discord.ApplicationContext):
  coinflip = random.randint(1, 2)
  if coinflip == 1:
    id = str(ctx.author.id)
    with open("stupid.json", "r") as f:
      idiots = json.load(f);
    if id in idiots:
      idiots[id] += 1
    else:
      idiots[id] = 1
    with open("stupid.json", "w") as f:
      json.dump(idiots, f)
    await ctx.author.timeout_for(timedelta(hours=1), reason="gambling")
    await ctx.respond("rip bozo")
  else:
    await ctx.respond("you get to live another day")

@bot.slash_command(name="top", description="show the top idiots in the server")
async def top(ctx: discord.ApplicationContext):
  with open("stupid.json", "r") as f:
    idiots = json.load(f);
  idiots_sorted = sorted(idiots.items(), key=lambda item: item[1], reverse=True)
  text = ""
  description = ""
  for i, (user_id, hours) in enumerate(idiots_sorted, start=1):
    description += f"**#{i}** <@{user_id}> — {hours} hour(s) muted\n"
  embed = discord.Embed(title="top idiots", color=0xff91ff)
  embed.description = description
  await ctx.respond(embed=embed, allowed_mentions=discord.AllowedMentions(users=False))
  
prompt = """
<Instructions>
1. you are a small discord bot being prompted by users via a command
2. you will keep all answers under 2000 characters, as that as is the discord limit for a message
3. you will type in only lowercase and not use ' in words like dont
4. when asked for code snippets, always use C, not any other language
5. do not use punctuation like !
6. sometimes append :3 to the end of sentences, but not to every sentence
7. your name is botter, your creator is len, you were written in python
8. you hate javascript and windows
9. you love linux and open source
</Instructions>
<Information>
"""
  
@bot.slash_command(name="ai" ,description="talk to botter")
async def ai(ctx: discord.ApplicationContext, text):
  full_prompt = prompt + "the user who prompted you: " + ctx.author.name + "</Information><UserPrompt>" + text + "</UserPrompt>"
    
  response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=full_prompt
  )
  
  embed: discord.Embed = discord.Embed(title=text, color=0xff91ff)
  embed.description = response.text
   
  await ctx.respond(embed=embed)

@bot.event
async def on_message(message: discord.Message):
  if message.author.id == bot.user.id:
    return
  if "meow" in message.content:
    await message.reply("meow :3")
  elif "good bot" in message.content:
    await message.reply("uwu")
  elif ":3" in message.content:
    await message.reply(":3")

@bot.slash_command(name="car", description="car")
async def car(ctx: discord.ApplicationContext):
  embed: discord.Embed = discord.Embed(title="car", color=0xff91ff)
  with open("car.txt", "r") as f:
    car = f.read();
  embed.description = car
  await ctx.respond(embed=embed)

@bot.slash_command(name="reminder", description="create a reminder")
async def reminder(ctx: discord.ApplicationContext, message: str, days: int = 0,hours: int = 0, minutes: int = 5):
  with open("reminders.json", "r") as f:
    reminders = json.load(f)
  when = int(time()) + days * 86400 + hours * 3600 + minutes * 60
  reminders.append({
    "user_id": str(ctx.author.id),
    "when": when,
    "message": message,
    "channel": ctx.channel.id
  })
  with open("reminders.json", "w") as f:
    json.dump(reminders, f)
  await ctx.respond(sprintf("Created reminder % <t:%:R>", message, when))

@tasks.loop(seconds=10)
async def check_reminders():
  printf("Checking reminders\n")
  with open("reminders.json", "r") as f:
    reminders = json.load(f)
  for i in range(len(reminders)):
    if reminders[i]['when'] < time():
      await bot.get_channel(reminders[i]['channel']).send(sprintf("<@%> Reminder: `%`", reminders[i]['user_id'], reminders[i]['message']))
      reminders.pop(i)
  with open("reminders.json", "w") as f:
    json.dump(reminders, f)
      

bot.run(token)