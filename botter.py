import discord
from discord.ext import commands
from datetime import timedelta
import json
import psutil

token: str

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
    
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='#', intents=intents)

@bot.command(help="lets u time yourself out for an hour")
async def mute_me(ctx):
  id = str(ctx.author.id)
  with open("stupid.json", "r") as f:
    idiots = json.load(f);
  if id in idiots:
    idiots[id] += 1
  else:
    idiots[id] = 1
  with open("stupid.json", "w") as f:
    json.dump(idiots, f)
  await ctx.author.timeout_for(timedelta(hours=1), reason="self inflicted")

@bot.command(help="shows how many times uve muted urrself")
async def stupid(ctx):
  id = str(ctx.author.id)
  with open("stupid.json", "r") as f:
    idiots = json.load(f);
  if id in idiots:
    await ctx.send(sprintf("uve muted urself for % hours total, idiot", idiots[id]))
  else:
    await ctx.send("u havent muted urself, good job")

@bot.command(help="makes the bot say things")
async def echo(ctx, *vaargs):
  val = ""
  for i in vaargs:
    val += str(i) + " "
  await ctx.send(val)

@bot.command(help="murders botter")
async def kys(ctx):
  if ctx.author.id != 808122595898556457:
    await ctx.send("nuh uh")
    return
  await ctx.send("k bye")
  exit(0)
  
@bot.command(help="returns your id")
async def id(ctx):
  await ctx.send(ctx.author.id)
  
@bot.command(help="shows the bots latency")
async def ping(ctx):
  await ctx.send(sprintf("this took %ms to send", round(bot.latency * 1000, 1)))

@bot.command(help="tells you if you are gay")
async def am_i_gay(ctx):
  await ctx.send("yes")
  
@bot.command(help="tells you if the bot is gay")
async def are_you_gay(ctx):
  await ctx.send("only for <@808122595898556457>")

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
    await ctx.send("nuh uh")
    return
  await member.ban(reason=reason)
  ctx.send("bye bye %", member.name)

@bot.command(help="kicks a user")
@commands.has_permissions(moderate_members=True)
async def kick(ctx, member: discord.Member, reason):
  if not commands.check(predicate):
    await ctx.send("nuh uh")
    return
  await member.kick(reason=reason)
  ctx.send("bye bye %", member.name)

@bot.event
async def on_member_join(member):
  role = discord.utils.get(member.guild.roles, name="lowlies")
  await member.add_roles(role)
  await bot.get_channel(1367249503593168978).send(sprintf("new member: %\nhi", member.name))

@bot.command(help="cpu load on len computer")
async def cpu(ctx):
  cpu_load = psutil.cpu_percent(interval=1)
  await ctx.send(sprintf("len cpu is at %|%", cpu_load))

@bot.command(help="ram on len computer")
async def mem(ctx):
  mem = psutil.virtual_memory()
  await ctx.send(sprintf("%MiB of %MiB ram used rn", mem.used // (1024**2), mem.total // (1024**2)))

@bot.command(help="shows len root partition space")
async def disk(ctx):
  disk = psutil.disk_usage("/")
  await ctx.send(sprintf("%GiB free of %GiB", (disk.total - disk.used) // (1024**3), disk.total // (1024**3)))

@bot.command(help="shows len OS")
async def os(ctx):
  with open("/home/lena/arch_logo", 'r') as f:
    logo = f.read()
  await ctx.send(sprintf("```\n%\n```", logo.replace("`", "'")))

@bot.command(help="give botter source code")
async def source(ctx):
  await ctx.send("https://github.com/lenanya/botter")
  
bot.run(token)