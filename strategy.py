"""
A set of strategies for our bot
"""
import math
from typing import List
from regression_games import RGBot, FindResult, Item, Entity, Vec3, RGCTFUtils
from utilities import move_toward_position, use_potion_of_type, get_potion_of_type, use_potion

def handle_low_health(bot: RGBot, rg_ctf_utils: RGCTFUtils, opponents: List[Entity], teammates: List[Entity]) -> bool:
    if bot.mineflayer().health <= 7:
        #near death, see if I can use a potion to make the opponent die with me
        nearby_opponents = [o for o in opponents if o.position.distanceSquared(bot.position()) <= 16]
        near_opponent = nearby_opponents[0] if nearby_opponents else None
        if near_opponent:
            potion: Item = get_potion_of_type(bot, 'ninja')
            if potion:
                # look at their feet before throwing down a ninja potion
                bot.mineflayer().lookAt(near_opponent.position.offset(0, -1, 0)) # TODO: WAS AWAIT
                return use_potion(bot, potion) # TODO: WAS AWAIT
    elif bot.mineflayer().health <= 15:
        # just need a top up
        print('[Health] Need to use potion while my health is low')
        return use_potion_of_type(bot, 'health') # TODO: WAS AWAIT
    return False

def handle_attack_flag_carrier(bot: RGBot, rg_ctf_utils: RGCTFUtils, opponents: List[Entity], teammates: List[Entity]) -> bool:
    """
    find out if the flag is available
    """
    flag_location: Vec3 = rg_ctf_utils.getFlagLocation()
    if flag_location is None:
        print(f'Checking {len(opponents)} opponents in range for flag carriers')
        # see if one of these opponents is holding the flag
        opponents_with_flag = [o for o in opponents if o.heldItem and rg_ctf_utils.FLAG_SUFFIX in o.heldItem.name]
        opponent_with_flag = opponents_with_flag[0] if opponents_with_flag else None

        if opponent_with_flag:
            print(f'Attacking flag carrier {opponent_with_flag.name} at position: ${bot.vecToString(opponent_with_flag.position)}')
            use_potion_of_type(bot, 'movement') # run faster to get them
            # TODO: Once I get in range of attack, should I use a combat potion ? should I equip a shield ?
            bot.attackEntity(opponent_with_flag)
            return True
    return False

def handle_attack_nearby_opponent(bot: RGBot, rg_ctf_utils: RGCTFUtils, opponents: List[Entity], teammates: List[Entity]) -> bool:
    outnumbered = len(teammates) + 1 < len(opponents)
    yolo = len(teammates) == 0

    my_position = bot.position()

    # opportunistically kill any player in close range even if that means dropping the flag to do it
    # within range 10 regular, 5 if I have the flag
    the_opponents = [o for o in opponents if o.position.distanceSquared(my_position) <= (25 if rg_ctf_utils.hasFlag() else 100)]

    print(f'Checking {len(the_opponents)} opponents in range to murder')
    if the_opponents:
        first_opponent = the_opponents[0]

        # Attack if a teammate is nearby only, otherwise move toward team-mate
        if not outnumbered or yolo:
            print(f'Attacking opponent at position: {bot.vecToString(first_opponent.position)}')
            # TODO: Once I get in range of attack, should I use a combat potion ? should I equip a shield ?
            bot.attackEntity(first_opponent)
            return True
        else:
            print('Outnumbered, running to nearest team-mate for help')
            # TODO: Do I need to use potions ? un-equip my shield to run faster ?
            move_toward_position(bot, teammates[0].position, 3)
            return True
    return False

def handle_scoring_flag(bot: RGBot, rg_ctf_utils: RGCTFUtils, opponents: List[Entity], teammates: List[Entity]) -> bool:
    if rg_ctf_utils.hasFlag():
        # TODO: Do I need to use potions ? un-equip my shield to run faster ?
        print('I have the flag, running to score')
        my_team_name = bot.getMyTeam()
        my_score_location =  rg_ctf_utils.BLUE_SCORE_LOCATION if my_team_name == 'BLUE' else rg_ctf_utils.RED_SCORE_LOCATION
        move_toward_position(bot, my_score_location, 1)
        return True
    return False

def handle_collecting_flag(bot: RGBot, rg_ctf_utils: RGCTFUtils, opponents: List[Entity], teammates: List[Entity]) -> bool:
    flag_location: Vec3 = rg_ctf_utils.getFlagLocation()
    if flag_location:
        print(f'Moving toward the flag at {bot.vecToString(flag_location)}')
        # TODO: Do I need to use potions ? un-equip my shield to run faster ?
        move_toward_position(bot, flag_location, 1)
        return True
    return False

placeable_block_display_names = ['Gravel', 'Grass Block', 'Dirt', 'Stripped Dark Oak Wood']

# bridge blockade
blue_block_placements = [Vec3(81,65,-387), Vec3(81, 66, -387), Vec3(81,65,-385), Vec3(81, 66, -385)]

# bridge blockade
red_block_placements = [Vec3(111,65,-387), Vec3(111, 66, -387), Vec3(111,65,-385), Vec3(111, 66, -385)]

def handle_placing_blocks(bot: RGBot, rg_ctf_utils: RGCTFUtils, opponents: List[Entity], teammates: List[Entity]) -> bool:
    my_position = bot.position()
    my_team_name = bot.getMyTeam()

    # only consider bots on the same y plane not those down in the tunnel, and within range 15
    the_opponents = [o for o in opponents if abs(o.position.y - my_position.y) < 5 and o.position.distanceSquared(my_position) < 225]

    print(f'Checking {len(the_opponents)} opponents in range before getting items or placing blocks')
    if len(the_opponents) == 0:
        # If I have blocks to place, go place blocks at strategic locations if they aren't already filled
        block_in_inventory = [i for i in bot.getAllInventoryItems() if i.displayName in placeable_block_display_names]

        if block_in_inventory:
            print(f'I have a "{block_in_inventory.displayName}" block to place')
            block_placements = blue_block_placements if my_team_name == 'BLUE' else red_block_placements
            for location in block_placements:
                # if I'm within 20 blocks of a place to put blocks
                block = bot.mineflayer().blockAt(location)
                range_sq = location.distanceSquared(my_position)
                print(f'Checking for block: {block and block.type} at range_sq: {range_sq}')
                if range_sq <= 400:
                    if not block or block.type == 0: # air
                        print(f'Moving to place block "{block_in_inventory.displayName}" at: {location}')
                        move_toward_position(bot, location, 3)
                        # if I'm close, then place the block
                        if location.distanceSquared(my_position) < 15:
                            print(f'Placing block "{block_in_inventory.displayName}" at: {location}')
                            # TODO: RGBot.placeBlock should handle this for us once a defect is fixed
                            bot.mineflayer().equip(block_in_inventory, 'hand')
                            # place block on top face of the block under our target
                            bot.mineflayer().placeBlock(bot.mineflayer().blockAt(location.offset(0, -1, 0)), Vec3(0, 1, 0))
                        return True
        else:
            print('No placeable blocks in inventory')
    return False

def handle_looting_items(bot: RGBot, rg_ctf_utils: RGCTFUtils, opponents: List[Entity], teammates: List[Entity]) -> bool:
    my_position = bot.position()
    items = bot.findItemsOnGround({
        'maxDistance': 33,
        'maxCount': 5,
        # prioritize items I don't have that are the closest
        'itemValueFunction': lambda block_name: 999999 if bot.inventoryContainsItem(block_name) else 1,
        'sortValueFunction': lambda distance, point_value: distance * point_value
    })
    # TODO: Should I let my bots run down into the tunnel for better loot ?
    #       or keep them on the top only
    items = [i.result for i in items if abs(i.result.position.y - my_position.y) < 5]
    item = items[0] if items else None

    if item:
        print(f'Going to collect item: {item.name} at: {bot.vecToString(item.position)}')
        # TODO: Do I need to use potions ? un-equip my shield to run faster ?
        move_toward_position(bot, item.position, 1)
        return True
    return False

def handle_bot_idle_position(bot: RGBot, rg_ctf_utils: RGCTFUtils, opponents: List[Entity], teammates: List[Entity]) -> bool:
    # TODO: Is this really the best place to move my bot towards ?
    # Hint: This is where most of Macro game strategy gets implemented
    # Do my bots spread out to key points looking for items or opponents ?
    # Do my bots group up to control key areas of the map ?
    # Do those areas of the map change dependent on where the flag currently is ?
    print(f'Moving toward center point: ${bot.vecToString(rg_ctf_utils.FLAG_SPAWN)}')
    move_toward_position(bot, rg_ctf_utils.FLAG_SPAWN, 1)
    return True
