"""
A set of utilities for Regression Games and Capture the Flag
"""
from regression_games import RGBot, Entity, Vec3, goals, Item
import time
from typing import Union, List
import json


def get_unbreakable_blocks(bot: RGBot) -> list:
    """
    Returns a list of all unbreakable block types in the RG CTF mode.
    :param bot: The bot being configured
    """
    blocks_by_name = bot.mcData.blocksByName
    return [
        # materials used for castles
        blocks_by_name.stone_bricks.id,
        blocks_by_name.stone_brick_slab.id,
        blocks_by_name.stone_brick_stairs.id,
        blocks_by_name.stone_brick_wall.id,
        blocks_by_name.ladder.id,
        blocks_by_name.cracked_stone_bricks.id,
        blocks_by_name.white_carpet.id,

        # blue castle
        blocks_by_name.blue_carpet.id,
        blocks_by_name.light_blue_carpet.id,
        blocks_by_name.blue_stained_glass_pane.id,
        blocks_by_name.light_blue_stained_glass_pane.id,
        blocks_by_name.soul_torch.id,
        blocks_by_name.soul_wall_torch.id,
        blocks_by_name.soul_lantern.id,
        blocks_by_name.lapis_block.id,
        blocks_by_name.blue_glazed_terracotta.id,

        # red castle
        blocks_by_name.red_carpet.id,
        blocks_by_name.pink_carpet.id,
        blocks_by_name.red_stained_glass_pane.id,
        blocks_by_name.pink_stained_glass_pane.id,
        blocks_by_name.redstone_torch.id,
        blocks_by_name.redstone_wall_torch.id,
        blocks_by_name.lantern.id,
        blocks_by_name.red_wool.id,
        blocks_by_name.red_glazed_terracotta.id,

        # item spawns + flag barrier
        blocks_by_name.polished_andesite.id,
        blocks_by_name.polished_andesite_slab.id,
        blocks_by_name.polished_andesite_stairs.id,

        # arena, obstacles, and underwater tunnel
        blocks_by_name.snow_block.id,
        blocks_by_name.snow.id,
        blocks_by_name.glass.id,
        blocks_by_name.glass_pane.id,
        blocks_by_name.white_stained_glass_pane.id,
        blocks_by_name.spruce_fence.id
    ]


def nearest_teammates(bot: RGBot, max_distance=33, bots_only=True) -> List[Entity]:
    """
    Finds any teammates I have within the maxDistance.  Results are sorted by closest distance from my bot.
    Note: The bot can only see ~30 +/- blocks.  So you may have a team-mate at 40 blocks away but this API won't find them.
    You could share information between bots via in game whispers if you want to share location information beyond the bot
    sight range.

    Args:
      bot: RGBot instance
      max_distance: The maximum distance to look for a teammate. Don't set larger than 33. Defaults to 33
      bots_only: Whether to select only bots or also human players on the same team. Defaults to True.

    Returns: The list of teammates that are nearby
    """
    match_info = bot.matchInfo()
    if match_info:
        bot_name = bot.username()
        team_name = bot.teamForPlayer(bot_name)
        print(f'Checking for any team-mates in range: {max_distance}')
        if team_name:
            teammates = [p for p in match_info.players if p.team == team_name and (
                not bots_only or p.isBot) and p.username is not bot_name]
            if teammates:
                my_position = bot.position()
                entities = bot.findEntities({
                    'entityNames': [p.username for p in teammates],
                    'attackable': True,
                    'maxDistance': max_distance
                })
                entities = [e.result for e in entities]
                return sorted(entities, key=lambda t: t.position.distanceSquared(my_position))
    return []


last_move_position: Vec3 = None


def move_toward_position(bot: RGBot, target_position: Vec3, reach: int = 1, should_wait: bool = False) -> bool:
    """
    Handles movement from a main loop bot.  It is important NOT to change the pathfinding target every loop iteration unless
    it really needs to change.  This function handles only updating the target when the destination has changed.

    Args:
        bot: RGBot instance
        target_position: The pathfinding destination position
        reach: How many blocks away from the target position should I get before pathfinding stops. Defaults to 1.
        should_wait:  should I await pathfinding (true), or let it run asynchronously in the background (false). Defaults to False.

    Returns: True if the bot successfully moved toward the position

    """
    global last_move_position
    is_moving = bot.mineflayer().pathfinder.isMoving()
    if not last_move_position or not is_moving or target_position.distanceSquared(last_move_position) > reach**2:
        print(
            f'[Movement] Moving toward position: {bot.vecToString(target_position)}, isMoving: {is_moving}')
        last_move_position = target_position
        if should_wait:
            bot.approachPosition(
                target_position, {reach: reach})
            print(
                f'[Movement] Reached target position: {bot.vecToString(target_position)}')
        else:
            # DO NOT AWAIT PATHING... WE'LL INTERRUPT IT LATER WITH A NEW TARGET IF NEED BE
            # TODO: START THIS ON A NEW THREAD
            bot.mineflayer().pathfinder.goto(goals.GoalNear(target_position.x, target_position.y, target_position.z, reach))
            print(f'[Movement] Reached target position: ${bot.vecToString(target_position)}')
            last_move_position = None
        return True
    else:
        print('[Movement] Not changing movement target because previous ~= new')
    return False


last_run_time = -1


def throttle_runtime(bot: RGBot):
    """
    Used at the start of each main loop to throttle the runtime.  Minecraft server runs at 20 ticks per second (50ms per tick).
    Thus executing our bot main loop more frequently than every 50ms would re-process stale game state.
    Executing more often that this would waste CPU and starve the other bots on our team, which share our limited CPU resources.
    """
    compute_wait_time = 50

    global last_run_time

    wait_time = (last_run_time + compute_wait_time) - int(time.time()*1000)
    if wait_time > 0:
        print(f'[Throttle] Waiting {wait_time} millis before next loop')
        bot.wait(round(wait_time*20/1000))  # TODO: WAS AWAIT

    last_run_time = int(time.time()*1000)


# sort potions with the ones you want to use first near the front
MOVEMENT_POTIONS = ['Gotta Go Fast', 'Lava Swim']
COMBAT_POTIONS = ['Increased Damage Potion']
NINJA_POTIONS = ['Poison Cloud II', 'Poison Cloud']
HEALTH_POTIONS = ['Totem of Undying', 'Healing Potion', 'Tincture of Life',
                  'Tincture of Mending II', 'Tincture of Mending', 'Golden Apple']

POTION_TYPE = Union['movement', 'combat', 'ninja', 'health']

def get_potion_of_type(bot: RGBot, potion_type: POTION_TYPE) -> Union[str, None]:
    """
    get the potion item from the bot's inventory of the specified type if it exists
    """
    potions = []
    if potion_type == 'movement':
        potions = MOVEMENT_POTIONS
    elif potion_type == 'combat':
        potions = COMBAT_POTIONS
    elif potion_type == 'ninja':
        potions = NINJA_POTIONS
    elif potion_type == 'health':
        potions = HEALTH_POTIONS

    if len(potions) > 0:
        inventory_items = bot.getAllInventoryItems()
        found_potions = [item for item in inventory_items if name_for_item(item) in potions]
        return found_potions[0] if found_potions else None
    return None

def use_potion(bot: RGBot, potion: str) -> bool:
    """
    hold and activate the given potion item from the bot's inventory
    """
    if potion:
        bot.holdItem(potion) # TODO: WAS AWAIT
        print(f"[Potions] Using potion: {name_for_item(potion)}")
        bot.mineflayer().activateItem(False)
        return True
    return False

def use_potion_of_type(bot: RGBot, potion_type: POTION_TYPE) -> bool:
    """
    hold and activate a potion item of the specified type from the bot's inventory
    """
    potion = get_potion_of_type(bot, potion_type)
    return use_potion(bot, potion) # TODO: WAS AWAIT

def name_for_item(item: Item) -> str:
    """
    This will get the CustomName or DisplayName or Name for an item in that preference Order.
    This is important for potions, where the name and displayName for the item are not unique.
    """
    if item.customName:
        try:
            j = json.loads(item.customName)
            return j['extra'][0]['text']
        except:
            pass
    return item.displayName or item.name


def equip_shield(bot: RGBot) -> bool:
    """
    Equip shield from inventory into off-hand if possible
    """
    shields = [item for item in bot.getAllInventoryItems() if ('Shield' in item.displayName or 'shield' in item.name)]
    if shields:
        shield = shields[0]
        print(f'[Shield] Equipping: {shield.displayName}')
        bot.mineflayer().equip(shield, 'off-hand') # TODO: WAS AWAIT
        return True
    return False

def unequip_off_hand(bot: RGBot):
    """
    Un-equip off-hand item like a shield
    """
    bot.mineflayer().unequip('off-hand') # TODO: WAS AWAIT