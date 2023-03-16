from rg_javascript import require, On

RG_BOT_VERSION = '1.10.0'
RG_CTF_UTILS_VERSION = '1.0.5'
MINEFLAYER_VERSION = '4.5.1'

# Because of how we load these JS modules to be used in Python, we 
# define everything here to abstract away the "JS"-ness of it
# TODO: We can attach types here for easier development
mineflayer_pathfinder = require('mineflayer-pathfinder')
mineflayer = require('mineflayer', MINEFLAYER_VERSION)
rg_match_info = require('rg-match-info')
Vec3 = require('vec3').Vec3
RGBot = require('rg-bot', RG_BOT_VERSION).RGBot
FindResult = require('rg-bot', RG_BOT_VERSION).FindResult
RGCTFUtils = require('rg-ctf-utils', RG_CTF_UTILS_VERSION).RGCTFUtils
CTFEvent = require('rg-ctf-utils', RG_CTF_UTILS_VERSION).CTFEvent
armorManager = require('mineflayer-armor-manager')
Item = require('prismarine-item').Item
Entity = require('prismarine-entity').Entity
goals = mineflayer_pathfinder.goals
RGEventHandler = On
