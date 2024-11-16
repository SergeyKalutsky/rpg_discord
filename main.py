from discord.ext import commands
from dotenv import load_dotenv
from game_data import msgs
import database as db
import discord
import os

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.command(name='start')
async def start(ctx):

    player_id = str(ctx.author.id)

    # Загружаем данные игрока из базы данных
    player_data = db.load_player(player_id)

    if not player_data:
        base_values = [100, 100, 15, 0, '', 0]
        # сохранить значния
        db.save_player(player_id, base_values)
        await ctx.send(msgs['welcome'])
        return
    
    await ctx.send(msgs['started'].format(ctx.author.mention))
    

@bot.command(name='status')
async def status(ctx):
    player_id = str(ctx.author.id)
    player_data = db.load_player(player_id)
    if not player_data:
        await ctx.send(msgs['start'].format(ctx.author.mention))
        return

    # Извлекаем данные игрока
    current_hp = player_data['current_hp']
    max_hp = player_data['max_hp']
    damage = player_data['damage']
    player_loc_id = player_data['current_location_id']

    # Список пройденных локаций
    passed_locations = player_data['passed_locations'].split(',') if player_data['passed_locations'] else []
    current_loc = 'Дорога в деревню'
    passed_locs = []

    locs_data = db.load_locations()
    for loc in locs_data:
        loc_id = str(loc['id'])

        if loc_id == str(player_loc_id):
            current_loc = loc['name']

        if loc_id in passed_locations:
            passed_locs.append(loc['name'])

    if not passed_locs:
        passed_locs = ['Нет пройденных локаций']

    await ctx.send(msgs['status'].format(
        ctx.author.mention, 
        current_hp, 
        max_hp, 
        damage, 
        current_loc, 
        ', '.join(passed_locs))
        )            


@bot.command(name='go')
async def go(ctx, *, location_name: str = None):
    # Лес, 2
    # Check if location name was provided
    if not location_name:
        await ctx.send(msgs['goerror'].format(ctx.author.mention))
        return

    player_id = str(ctx.author.id)
    player_data = db.load_player(player_id)
    # '2' -> 
    # Check if the player exists in the database
    if not player_data:
        await ctx.send(msgs['start'].format(ctx.author.mention))
        return

    location_data = db.load_locations(loc_id=int(location_name) if location_name.isdigit() else None, loc_name=location_name)

    if not location_data:
        await ctx.send(msgs['wrongloc'].format(ctx.author.mention, location_name))
        return
    location_data = location_data[0]

    # Check if the player is already at the location
    if player_data['current_location_id'] == location_data['id']:
        await ctx.send(msgs['alreadyonloc'].format(ctx.author.mention, location_name))
        return

    # Check if location has already been passed
    passed_locations = player_data['passed_locations'].split(',') if player_data['passed_locations'] else []
    if location_data['name'] in passed_locations:
        await ctx.send(msgs['onpassedloc'].format(ctx.author.mention, location_name))
        return

    # Update the player's current location in the database
    db.update_location(player_id, location_name)
    db.update_current_boss_hp(player_id=player_id, hp=location_data['boss_hp'])

    # If the location has a boss, notify the player
    await ctx.send(msgs['bossmeet'].format(ctx.author.mention, location_name, location_data['boss_name'], location_data['boss_hp'], location_data['boss_dmg']))


@bot.command(name='attack')
async def attack(ctx):
    player_id = str(ctx.author.id)
    player_data = db.load_player(player_id)

    # Check if the player exists in the database
    if not player_data:
        await ctx.send(msgs['start'].format(ctx.author.mention))
        return

    if player_data['current_location_id'].isdigit():
        locations = db.load_locations(loc_id=player_data['current_location_id'])
    else:
        locations = db.load_locations(loc_name=player_data['current_location_id'])

    if not locations:
        await ctx.send(msgs['wrongloc'].format(ctx.author.mention, ''))
        return

    loc = locations[0]
    if not loc['boss_name']:
        await ctx.send(msgs['noenemy'])
        return
        
    if loc['boss_hp'] <= 0:
        await ctx.send(msgs['alreadydead'].format(ctx.author.mention, loc['boss_name']))
        return

    boss_hp = loc['boss_hp']
    boss_hp = boss_hp - player_data['damage']

    if boss_hp <= 0:
        db.pass_location(player_id, loc['id'])
        db.add_bonus(player_id, loc['hp_bonus'], loc['dmg_bonus'])
        await ctx.send(msgs['bossdefeat'].format(loc['boss_name']))
        db.restore_hp(player_id)
        player_data = db.load_player(player_id)
        await ctx.send(msgs['bonus'].format(ctx.author.mention, player_data['current_hp'], loc['hp_bonus'], player_data['damage'], loc['dmg_bonus']))

        if db.check_win(player_data['passed_locations']):
            await ctx.send(msgs['win'].format(ctx.author.mention))
            db.delete_player(player_id)
        return
    
    await ctx.send(msgs['attack'].format(loc['boss_name'], ctx.author.mention, loc['boss_dmg']))
    if player_data['current_hp'] <= 0:
        await ctx.send(msgs['gameover'].format(ctx.author.mention))
        db.delete_player(player_id)
        return
    
    db.update_current_boss_hp(player_id, boss_hp)
    db.update_hp(player_id, player_data['current_hp'], boss_hp)
    await ctx.send(msgs['fightstatus'].format(boss_hp, player_data['current_hp']))


# Написать команду help, которая вывод в чат сообщение msgs['help']
@bot.command(name='helps')
async def help(ctx):
    await ctx.send(msgs['help'])


@bot.command(name='map')
async def map(ctx):
    player = ctx.author
    player_id = str(player.id)

    player_data = db.load_player(player_id)
    locs_data = db.load_locations()

    if not player_data:
        await ctx.send(msgs['start'].format(player.mention))
        return
    
    msg_data = [f'{player.mention}']

    passed_locs = player_data['passed_locations'].split(',') if player_data['passed_locations'] else []
    current_loc_id = str(player_data['current_location_id'])

    for loc in locs_data:
        loc_id = str(loc['id'])

        # Определяем статус игрока на локации
        if loc_id == current_loc_id:
            status = '🟢 Текущая локация'
        elif loc_id in passed_locs:
            status = '🟡 Пройдено'
        else:
            status = '🔴 Не пройдено'
        
        msg = msgs['locinfo'].format(
            loc['id'],
            loc['name'],
            status,
            loc['boss_name'],
            loc['boss_hp'],
            loc['boss_dmg'],
            loc['hp_bonus'],
            loc['dmg_bonus'],
        )
        msg_data.append(msg)
    
    await ctx.send('\n'.join(msg_data))
        


if __name__ == '__main__':
    bot.run(os.getenv('TOKEN'))