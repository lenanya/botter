import discord
from discord.ext import commands
from datetime import timedelta
import json
import psutil
import requests
import random
from google import genai

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

@bot.command(help="lets u time yourself out for an hour")
async def mute_me(ctx, hours):
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
  await ctx.reply("congrats, you timed yourself out for an hour, dumbass")

@bot.command(help="shows how many times uve muted urrself")
async def stupid(ctx):
  id = str(ctx.author.id)
  with open("stupid.json", "r") as f:
    idiots = json.load(f);
  if id in idiots:
    await ctx.reply(sprintf("uve muted urself for % hours total, idiot", idiots[id]))
  else:
    await ctx.reply("u havent muted urself, good job")

@bot.command(help="makes the bot say things")
async def echo(ctx, *vaargs):
  val = ""
  for i in vaargs:
    val += str(i) + " "
  await ctx.send(val)

@bot.command(help="murders botter (len only)")
async def kys(ctx):
  if ctx.author.id != 808122595898556457:
    await ctx.reply("nuh uh")
    return
  await ctx.reply("k bye")
  exit(0)
  
@bot.command(help="returns your id")
async def id(ctx):
  await ctx.reply(ctx.author.id)
  
@bot.command(help="shows the bots latency")
async def ping(ctx):
  await ctx.reply(sprintf("this took %ms to send", round(bot.latency * 1000, 1)))

@bot.command(help="tells you if you are gay")
async def am_i_gay(ctx):
  await ctx.reply("yes")
  
@bot.command(help="tells you if the bot is gay")
async def are_you_gay(ctx):
  await ctx.reply("only for <@808122595898556457>")

@bot.event
async def on_ready():
  printf("logged in as % (%)\n", bot.user.name, bot.user.id)
  await bot.get_channel(1367249503593168978).send("hi chat i got restarted :3")

async def predicate(ctx):
  required_role = discord.utils.get(ctx.guild.roles, name="mod")
  if required_role is None:
      return False
  return any(role >= required_role for role in ctx.author.roles)

@bot.command(help="bans a user")
@commands.has_permissions(moderate_members=True)
async def ban(ctx, member: discord.Member, reason):
  if not commands.check(predicate):
    await ctx.reply("nuh uh")
    return
  await member.ban(reason=reason)
  await ctx.reply("bye bye %", member.name)

@bot.command(help="kicks a user")
@commands.has_permissions(moderate_members=True)
async def kick(ctx, member: discord.Member, reason):
  if not commands.check(predicate):
    await ctx.reply("nuh uh")
    return
  await member.kick(reason=reason)
  await ctx.reply("bye bye %", member.name)

@bot.event
async def on_member_join(member):
  role = discord.utils.get(member.guild.roles, name="humans, probably")
  await member.add_roles(role)
  await bot.get_channel(1367249503593168978).send(sprintf("new member: %, hiiii :3", member.name))

@bot.command(help="cpu load on len computer")
async def cpu(ctx):
  cpu_load = psutil.cpu_percent(interval=1)
  await ctx.reply(sprintf("len cpu is at %|%", cpu_load))

@bot.command(help="ram on len computer")
async def mem(ctx):
  mem = psutil.virtual_memory()
  await ctx.reply(sprintf("%GiB of %GiB ram used rn", round(mem.used / (1024**3), 2), round(mem.total / (1024**3), 2)))

@bot.command(help="ram usage in bytes for some reason")
async def membytes(ctx):
  mem = psutil.virtual_memory()
  await ctx.reply(sprintf("%B of %B ram used rn", mem.used, mem.total))

@bot.command(help="shows len root partition space")
async def disk(ctx):
  disk = psutil.disk_usage("/")
  await ctx.reply(sprintf("%GiB free of %GiB", (disk.total - disk.used) // (1024**3), disk.total // (1024**3)))

@bot.command(help="shows len OS")
async def os(ctx):
  with open("/home/lena/arch_logo", 'r') as f:
    logo = f.read()
  await ctx.reply(sprintf("```\n%\n```", logo.replace("`", "'")))

@bot.command(help="give botter source code")
async def source(ctx):
  await ctx.reply("https://github.com/lenanya/botter")
  
@bot.command(help="nuh uh")
async def nuh(ctx):
  await ctx.reply("https://cdn.discordapp.com/attachments/1306832831988629528/1362111230155952188/car-garn47-397016279.gif?ex=6813a970&is=681257f0&hm=553b8456e1933ef8dba2be7e789e1dbea3475e3f5e44697c08c5a45d34ef5692&")

@bot.command(help="get lenas local ip (why?)")
async def ip(ctx):
  await ctx.reply("192.168.69.69")

@bot.command(help="print current directory lena is in")
async def pwd(ctx):
  with open("cwd", "r") as f:
    cwd = f.read()
  await ctx.reply(sprintf("lena is in `%`", cwd))
  
@bot.command(help="len room temperature")
async def temperature(ctx):
  with open("/var/www/arduino/temp", "r") as f:
    temp = f.read() + "°C"
  await ctx.reply(sprintf("lens room is % rn", temp))
  
@bot.event
async def on_command_error(ctx, error):
  if isinstance(error, commands.CommandNotFound):
    await ctx.reply("that command doesnt exist")
  else:
    await ctx.reply(sprintf("error: %", error))

@bot.command(help="block user from using status (len only)")
async def status_block(ctx, member: discord.Member):
  if ctx.author.id != 808122595898556457:
    await ctx.reply("nuh uh")
    return
  with open("blocked.json", "r") as f:
    blocked = json.load(f)
  blocked.append(member.id)
  with open("blocked.json", "w") as f:
    json.dump(blocked, f)
  await ctx.reply(sprintf("% can no longer change len status", member.name))

@bot.command(help="change len status")
async def status(ctx, *vaargs):
  with open("blocked.json", "r") as f:
    blocked = json.load(f)
  if ctx.author.id in blocked:
    await ctx.reply("youve been blocked from doing this")
    return
  text = ""
  for i in vaargs:
    text += i + " "
  if len(text) > 128:
    await ctx.reply("sorry, too long")
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
  requests.patch("https://discord.com/api/v10/users/@me/settings", headers=headers, json=payload)
  await ctx.reply("changed lens status lol")

@bot.command(help="change botters status (len only)")
async def bot_status(ctx, *vaargs):
  if ctx.author.id != 808122595898556457:
    await ctx.reply("nuh uh")
    return 
  text = ""
  for i in vaargs:
    text += i + " "
  await bot.change_presence(activity=discord.Game(name=text))
  await ctx.reply("changed bot status uwu")

@bot.command(help="happiness")
async def song(ctx):
  await ctx.send("https://www.youtube.com/watch?v=atdO6YRg5Cw")

@bot.command(help="either nothing happens, or you get muted")
async def gambling(ctx):
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
    await ctx.reply("rip bozo")
  else:
    await ctx.reply("you get to live another day!")

@bot.command(help="show the top idiots in the server")
async def top(ctx):
  with open("stupid.json", "r") as f:
    idiots = json.load(f);
  idiots_sorted = sorted(idiots.items(), key=lambda item: item[1], reverse=True)
  text = ""
  description = ""
  for i, (user_id, hours) in enumerate(idiots_sorted, start=1):
    description += f"**#{i}** <@{user_id}> — {hours} hour(s) muted\n"
  embed = discord.Embed(title="top idiots", color=0xff91ff)
  embed.description = description
  await ctx.reply(embed=embed, allowed_mentions=discord.AllowedMentions(users=False))
  
prompt = """
<Instructions>
1. you are a small discord bot being prompted by users via a command, you run locally on len's PC
2. you will keep all answers under 2000 characters, as that as i the discord limit for a message
3. you will type in only lowercase and not use ' in words like dont
4. when asked for code snippets, always use C, not any other language
5. do not use punctuation like !
6. frequently append :3 to the end of sentences
7. your name is botter, your creator is len
</Instructions>
<UserPrompt>
"""
  
@bot.command(help="talk to botter")
async def ai(ctx, *vaargs):
  text = ""
  for i in vaargs:
    text += i + " "
  response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=prompt+text+"</UserPrompt"
  )
  await ctx.reply(response.text)

bot.run(token)