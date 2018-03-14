# stan
A chat bot to help with staging and deployment

This is the famous chat bot that's supposed to make shipbuilder a lot easier to use.

# How to setup

1. Clone the repo
2. Fill in your credentials in the stanrc
3. Load stanrc into your dev environment `source stanrc`
4. Run bot_main.py (first time you run this, it'll take a while since the bot will try to discover all your git branches and map them)
5. Invite the bot to the devops channel
6. Or just DM it

# Commands?
There are no commands per se but here as some examples of input and what the bot will do

`list all free servers` - displays all servers that can be used to deploy
`going to <server name>` - this will cause the bot to allocate the server you specified to you and it will keep it as "reserved" for 2 days or until you release it
`release <server name>` - releases the box you're using
`help` - displays example commands
`status of <server name>` - prints the details of the reservation/status of the server
`update from history` - reads all messages in the given chat starting 2 weeks back and updates the bot's reservations list with that info
`list all servers` - unless you add in the "free" word this will just print the current status of servers that the bot knows about
`vm me <component name>` - finds a free box for the specified component (ui, optic, retina..blah blah) and assigns it to you. Use this if you're too lazy to pick a box yourself
