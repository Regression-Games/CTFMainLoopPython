"""
An example of a bot that uses a main loop to make decisions
on almost every tick of the game.
"""

import logging
import json
import traceback

logging.basicConfig(level=logging.NOTSET)

import os, sys
sys.path.append(os.path.dirname(__file__))


def configure_bot(bot):
    """
    configure_bot is called by Regression games - this is where you configure
    how your bot behaves
    """

    from regression_games import RGBot, RGCTFUtils, armorManager, RGEventHandler, Vec3, Entity
    from utilities import get_unbreakable_blocks, name_for_item, nearest_teammates, throttle_runtime
    from strategy import handle_attack_flag_carrier, handle_attack_nearby_opponent, handle_bot_idle_position, handle_looting_items, handle_low_health, handle_placing_blocks, handle_scoring_flag, handle_collecting_flag


    #  Disable rg-bot debug logging.  You can enable this to see more details about rg-bot api calls
    bot.setDebug(False)

    # Allow parkour so that our bots pathfinding will jump short walls and optimize their path for sprint jumps.
    bot.allowParkour(True)

    # We recommend disabling this on as you can't dig the CTF map.  Turning this on can lead pathfinding to get stuck.
    bot.allowDigWhilePathing(False)

    # Setup the rg-ctf-utils with debug logging
    rg_ctf_utils = RGCTFUtils(bot)
    rg_ctf_utils.setDebug(True)

    # Load the armor-manager plugin (https://github.com/PrismarineJS/MineflayerArmorManager)
    bot.mineflayer().loadPlugin(armorManager)

    # default to true in-case we miss the start
    match_in_progress = True

    # Information about the unbreakable block types
    unbreakable = get_unbreakable_blocks(bot)

    @RGEventHandler(bot, 'match_ended')
    def match_ended(self, match_info, *args):
        if match_info:
            players = [p for p in match_info.players if p.username == bot.username()]
            player = players[0] if players else None
            if player:
                points = player.metadata.score
                captures = player.metadata.flagCaptures
                print(f'The match has ended - I had {captures} captures and scored {points} points')
        match_in_progress = False

    @RGEventHandler(bot, 'match_started')
    def match_started(self, match_info, *args):
        print("The match has started")
        match_in_progress = True

    # Part of using a main loop is being careful not to leave it running at the wrong time.
    # It is very easy to end up with 2 loops running by accident.
    # Here we track the mainLoop instance count and update on key events.
    main_loop_instance_tracker = 0


    @RGEventHandler(bot, 'playerLeft')
    def player_left(self, player, *args):
        if (player.username == bot.username()):
            print("I have left the match")
            main_loop_instance_tracker += 1

    @RGEventHandler(bot, 'end')
    def end(self, *args):
        print("I have disconnected")
        main_loop_instance_tracker += 1

    @RGEventHandler(bot, 'kicked')
    def kicked(self, *args):
        print("I have been kicked")
        main_loop_instance_tracker += 1

    @RGEventHandler(bot, 'death')
    def death(self, *args):
        print("I have died")
        main_loop_instance_tracker += 1
        try:
            # Try to stop any goal currently going on
            bot.mineflayer().pathfinder.setGoal(None)
            bot.mineflayer().pathfinder.stop()
        except Exception:
            pass

    # Take a look at the spawn event handler at the end
    def main_loop(): 
        current_main_loop_instance = main_loop_instance_tracker
        is_active_function = lambda: match_in_progress and current_main_loop_instance == main_loop_instance_tracker
        while is_active_function():

            try:
                # always throttle the runtime first to make sure we don't execute too frequently and waste CPU
                throttle_runtime(bot)

                if not bot.matchInfo():
                    print("Match info not available yet, waiting")
                    continue

                #find out which team I'm on
                my_team_name: str = bot.getMyTeam()
                other_team_names: str = [t for t in bot.matchInfo().teams if t.name != my_team_name]
                other_team_name = other_team_names[0].name if other_team_names else None

                # get my current position and log information about my state
                my_position: Vec3 = bot.position()
                print(f'My team: {my_team_name}, my position: {bot.vecToString(my_position)}, my inventory: ${json.dumps([name_for_item(item) for item in bot.getAllInventoryItems()])}')

                # find any opponents in range
                opponent_names: list[str] = list(bot.getOpponentUsernames())
                print(f'Found the following opponents: {opponent_names}')
                print(opponent_names if opponent_names else ['...'])
                opponents_results = bot.findEntities({
                    # opNames can be empty in practice mode where there is no other team
                    # if we don't pass some array to match, then this will return all entities instead
                    'entityNames': opponent_names if opponent_names else ['...'],
                    'attackable': True,
                    'maxCount': 3,
                    'maxDistance': 33, # Bots can only see ~30 +/1 blocks, so no need to search far
                    # override the default value function here as we aren't using this value in the sortValueFunction
                    'entityValueFunction': lambda entity_name: 0,
                    # just sort them by distance for now... We'll filter them by decision point later
                    'sortValueFunction': lambda distance, entity_value, health, defense, toughness: distance
                })
                opponents: list[Entity] = [o.result for o in opponents_results]

                # find any teammates in range
                teammates: list[Entity] = nearest_teammates(bot, 33, True)

                # equip my best armor
                bot.mineflayer().armorManager.equipAll()

                # Only take 1 action per main loop pass.  There are exceptions, but this is best practice as the
                # game server can only process so many actions per tick
                did_something: bool = False

                if not did_something:
                    # Check if I'm low on health
                    did_something = handle_low_health(bot, rg_ctf_utils, opponents, teammates)

                if not did_something:
                    # if someone has the flag, hunt down player with flag if it isn't a team-mate
                    did_something = handle_attack_flag_carrier(bot, rg_ctf_utils, opponents, teammates)

                if not did_something:
                    # do I need to attack a nearby opponent
                    did_something = handle_attack_nearby_opponent(bot, rg_ctf_utils, opponents, teammates)

                if not did_something:
                    # if I have the flag, go score
                    did_something = handle_scoring_flag(bot, rg_ctf_utils, opponents, teammates)

                if not did_something:
                    # go pickup the loose flag
                    did_something = handle_collecting_flag(bot, rg_ctf_utils, opponents, teammates)

                if not did_something:
                    # If no-one within N blocks, place blocks
                    did_something = handle_placing_blocks(bot, rg_ctf_utils, opponents, teammates)

                if not did_something:
                    # see if we can find some items to loot
                    did_something = handle_looting_items(bot, rg_ctf_utils, opponents, teammates)

                if not did_something:
                    # we had nothing to do ... move towards the middle
                    did_something = handle_bot_idle_position(bot, rg_ctf_utils, opponents, teammates)
            except Exception as exc:
                # if we get anything other than a pathfinding change error, log it so that we can fix our bot
                if 'GoalChanged' not in str(exc) or 'PathStopped' not in str(exc):
                    print("An exception occurred while running this turn of logic")
                    print(traceback.format_exc())
                    # wait 1 seconds before looping again to avoid tight loops on errors
                    bot.wait(20)

        print(f'Ended loop that ran for instance {main_loop_instance_tracker} of the bot')

    @RGEventHandler(bot, 'spawn')
    def on_spawn(self, *args):
        bot.chat('I have come to win Capture The Flag with my main loop.')
        main_loop()
