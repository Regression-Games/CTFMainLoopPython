# Python Bot (Regression Games)

This template is a starting point for our experimental Python language support in Regression Games. Build Python bots to compete in Minecraft challenges on Regression Games!

* See the [start.py](#start.py) file for starting code

## Requirements

To make a valid bot, you must:

* Have a file called `start.py`
* Have a function with signature `configure_bot(bot)`

## Known Limitations

Python bots on Regression Games work by integrating into our JavaScript bots. This means that the Python calls to the bot are complete via calls to a Node/JavaScript backend. There are some known limitations to the current setup.

* The bot may be slower than JavaScript bots
* There is limited support for code written in separate files

Please see this note for more limitations: https://regressiongg.notion.site/Python-Common-Errors-34ea3ed2e5de4cd29529c49638a92a42

_Please provide us with feedback and suggestions for which limitations are blockers, and any other thoughts you may have!_