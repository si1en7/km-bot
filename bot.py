import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
import mail_parse as mp
import requests
import sys
import database as DB
import re

import logging

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# used for creating reactions with number of parse errors
emojimap = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣"]

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

bot = commands.Bot(command_prefix='!')

# when the bot is ready, show which servers are connected
@bot.event
async def on_ready():
    for guild in bot.guilds:
        print(f'Connected to: {guild.name}:{guild.id}')
        game = discord.Game("!kmhelp")
        await bot.change_presence(status=discord.Status.online,activity=game)


# allow the database class to be used in any scope
global kmdb
kmdb = DB.KMDB()

# commands can only be used in the channels specified by the database settings
def is_km_channel():
    def predicate(ctx):
        channels = kmdb.checkchannels(ctx.guild.id)
        
        return str(ctx.channel.id) in channels
    return commands.check(predicate)

# fix commands can only be used in specific channel from the database settings
def is_fix_channel():
    def predicate(ctx):
        channels = kmdb.checkchannels(ctx.guild.id)
        return str(ctx.channel.id) == channels[2]
    return commands.check(predicate)

# allow only specified roles to access some commands
def is_role_allowed():
    def predicate(ctx):
        roles = kmdb.checkroles(ctx.guild.id)
        roles = roles.split(",")
        for role in ctx.author.roles:
            if str(role.id) in roles:
                return True
    return commands.check(predicate)

# due to the nature of having to check every message for attachements, there is an on_messsage event. 
# Standard commands are triggered at the end of this function if there's no attachment
@bot.event
async def on_message(message):
    if bot.user != message.author:
        if message.attachments:
            count = 0
            for attachment in message.attachments:
                
                if attachment.filename.endswith(".png") or attachment.filename.endswith(".jpg") or attachment.filename.endswith(".jpeg"):
                    # add reaction to show image is being processed
                    await message.add_reaction('🔎')
                    # get the file and save it locally
                    file = requests.get(attachment.url,allow_redirects=True, stream=True)
                    file.raw.decode_content = True
                    open(f'screenshots/{message.id}_{attachment.filename}',"wb").write(file.content)
                    # begin processing the screenshot
                    parser = mp.Parser()
                    result = parser.processkm(f'{message.id}_{attachment.filename}',message.id, message.guild.id)
                    # check to see if server has reactions enabled
                    if kmdb.checkreactions(message.guild.id) == 1:
                        # image sucessfully procesed
                        if result == 0:
                            await message.remove_reaction('🔎',bot.user)
                           await message.add_reaction('✅')
                        # image partially processed
                        if result < 8 and result > 0:
                            await message.remove_reaction('🔎',bot.user)
                            await message.add_reaction(emojimap[result-1])
                            await message.add_reaction('⚠️')
                        # image did not match a known template or was already cropped and did not process
                        if result == 8:
                            await message.remove_reaction('🔎',bot.user)
                            await message.add_reaction('❌')
                        # found this screenshot already in the database
                        if result == 99:
                            await message.remove_reaction('🔎',bot.user)
                            await message.reply(f"This killmail was already processed: {attachment.filename}")
                            break
                        if result == 98:
                            await message.remove_reaction('🔎',bot.user)
                            break
                    else:
                        await message.remove_reaction('🔎',bot.user)
                    if kmdb.checkdebug(message.guild.id) == 1:
                        await message.channel.send(kmdb.getbymid(message.id))
                    count = count+1
        await bot.process_commands(message)

@bot.command(name='kmhelp')
@is_km_channel()
async def kmhelp(ctx):
    embedVar = discord.Embed(title="Kill Mail Bot Commands", description="A list of bot commands", color=0x5d91b3)
    embedVar.add_field(name="!kmhelp", value="display this help message", inline=False)
    embedVar.add_field(name="!kmtoday [loss]", value="get current 24-hour isk kill/loss totals. [loss] is optional", inline=False)
    embedVar.add_field(name="!kmdate [date] [loss]", value="get ISK kill/loss value for a specific day. Must be YYYY/MM/DD format. [loss] is optional", inline=False)
    embedVar.add_field(name="!kmdatebetwwen [date1] [date2] [loss]", value="get ISK kill/loss value for a date range. Must be YYYY/MM/DD format. [loss] is optional", inline=False)
    embedVar.add_field(name="!kmcorp [CORP] [loss]", value="get Isk kill/loss value for specified corp for all available data. Do not include [brackets] for corp name. [loss] is optional", inline=False)
    embedVar.add_field(name="!kmpilot \"[pilot]\" [loss]", value="get Isk kill/loss value for specified pilot for all available data. Pilot name **must** be in quotes. [loss] is optional", inline=False)
    embedVar.add_field(name="!kmfix", value="Displays a single record to be fixed", inline=False)
    embedVar.add_field(name="!kmfixfield [name] \"[value]\"", value="Fix a single field for a given record. Value **must** be in quotes.", inline=False)
    embedVar.add_field(name="!kmfixdone", value="Close record after fixing and commit changes to database", inline=False)
    embedVar.add_field(name="!kmdebug", value="Turn on debug output for parsed kill/loss mail", inline=False)
    await ctx.send(embed=embedVar)

@bot.command(name='kmtoday')
@is_km_channel()
async def kmtoday(ctx, loss=""):
    if loss == "loss":
        await ctx.send(kmdb.getiskday("now","loss"))
    else:
        await ctx.send(kmdb.getiskday("now","kill"))

@bot.command(name='kmdate')
@is_km_channel()
async def kmdate(ctx, searchdate, loss=""):
    if loss != "loss":
        loss="kill"
    result = re.search(r'[0-9]{4}/[0-1]?[0-9]/[0-3]?[0-9]', searchdate)
    if not result:
        await ctx.send("Imvalid date. Please enter a date like YYYY/MM/DD.")
    else:
        kmdb = DB.KMDB()
        
        await ctx.send(kmdb.getiskday(searchdate, loss))
@bot.command(name='kmdatebetween')
@is_km_channel()
async def kmdatebetween(ctx, dateleft, dateright, loss=""):
    if loss != "loss":
        loss="kill"
    resultleft = re.search(r'[0-9]{4}/[0-1]?[0-9]/[0-3]?[0-9]', dateleft)
    resultright = re.search(r'[0-9]{4}/[0-1]?[0-9]/[0-3]?[0-9]', dateright)
    if not resultleft:
        await ctx.send("Invalid date. Please enter a date like YYYY/MM/DD.")
    elif not resultright:
        await ctx.send("Invalid date. Please enter a date like YYYY/MM/DD.")
    else:
        kmdb = DB.KMDB()
        result = kmdb.getiskrange(dateleft, dateright, loss)
        if result == 99:
            await ctx.send("First date is greater than second date. Please try again.")
        else:
            await ctx.send(result)

@bot.command(name='kmcorp')
@is_km_channel()
async def kmcorp(ctx, corp, loss=""):
    if loss != "loss":
        loss="kill"
          
    await ctx.send(kmdb.getbycorp(corp, loss))

@bot.command(name='kmpilot')
@is_km_channel()
async def kmpilot(ctx, pilot, loss=""):
    if loss != "loss":
        loss="kill"
          
    await ctx.send(kmdb.getbypilot(pilot, loss))

@bot.command(name='kmfix')
@commands.check_any(commands.is_owner(),is_role_allowed())
@is_fix_channel()
async def kmfix(ctx):
    skip = ["id","message_id","guild_id","errors","filename"]
    result = kmdb.fixkm(ctx.guild.id)
    if result:
        message = ""
        for name, value in result.items():
            if name not in skip:
                message = message + f'{name}: {value}\n'
        await ctx.send(content=message, file=discord.File(open(f'processed/{result["filename"]}', "br"), result['filename']))
    else:
        await ctx.send("There are currently no reports to process. :tada:")

@bot.command(name='kmfixfield')
@is_fix_channel()
@commands.check_any(commands.is_owner(),is_role_allowed())
async def kmfix(ctx, field, value):
    if kmdb.fixfield(ctx.guild.id,field,value) == 1:
        await ctx.send(f'Field **{field}** has been updated. If you are done fixing this report, use **!kmfixdone** to save and close it.')
    else:
        await ctx.send(f'Ran into an issue trying to update {field} with {value}. Please try again.')

@bot.command(name='kmfixdone')
@is_fix_channel()
@commands.check_any(commands.is_owner(),is_role_allowed())
async def kmfixdone(ctx):
    if kmdb.closekm(ctx.guild.id):
        await ctx.send(f'Report was closed successfully.')
    else:
        await ctx.send(f'Unable to close report. Please try again.')

@bot.command(name='kmimporthist')
@is_km_channel()
@commands.check_any(commands.is_owner(),is_role_allowed())
async def kmimporthist(ctx):
    await ctx.send(f'Starting channel import. This will take a _long_ time.')
    async for message in ctx.channel.history(oldest_first=True):
        if bot.user != message.author:
            if message.attachments:
                for attachment in message.attachments:
                    if attachment.filename.endswith(".png") or attachment.filename.endswith(".jpg") or attachment.filename.endswith(".jpeg"):
                        await message.add_reaction('🔎')
                        file = requests.get(attachment.url,allow_redirects=True, stream=True)
                        file.raw.decode_content = True
                        open("screenshots/{}_{}".format(message.id,attachment.filename),"wb").write(file.content)
                        parser = mp.Parser()
                        parser.processkm("{}_{}".format(message.id,attachment.filename),message.id, message.guild.id)
    await ctx.send(f'Channel import completed. Please use **!kmfix** to review any reports that are partially imported.')

@bot.command(name='kmdebug')
@is_km_channel()
@is_role_allowed()
async def kmdebug(ctx):
    await ctx.send(kmdb.toggledebug(ctx.guild.id))
    
           
bot.run(TOKEN)