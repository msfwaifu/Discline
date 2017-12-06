from os import system
import sys
from blessings import Terminal
from line import Line
from settings import *
from globals import *
from discord import ChannelType
import discord
from userlist import print_userlist

# maximum number of lines that can be on the screen
# is updated every cycle as to allow automatic resizing
MAX_LINES = 0
# the index in the channel log the user is at
INDEX = 0
# buffer to allow for double buffering (stops screen flashing)
screen_buffer = []

# text that can be set to be displayed for 1 frame
display = ""

async def print_screen():
    global display
    # Get ready to redraw the screen
    left_bar_width = await get_left_bar_width()
    await clear_screen()

    await print_top_bar()

    if server_log_tree is not None and client.get_current_channel() is not None:
        await print_channel_log(left_bar_width)

    await print_bottom_bar()

    # Print the buffer. NOTE: the end="" is to prevent it
    # printing a new line character, which would add whitespace
    # to the bottom of the terminal
    with term.location(0, 1):
        print("".join(screen_buffer), end="")

    await print_left_bar(left_bar_width)

    if display is not None:
        print(display)

    display = ""

async def print_top_bar():
    topic = ""
    try: 
        if client.get_current_channel().topic is not None:
            topic = client.get_current_channel().topic
    # if there is no channel topic, just print the channel name
    except: 
        try:
            topic = client.get_current_channel().name
        except: pass


    with term.location(1,0):
        print("Server: " + await get_color(SERVER_DISPLAY_COLOR) \
                         + client.get_current_server_name() + term.normal, end="")

    with term.location(term.width // 2 - len(topic) // 2, 0):
        print(topic, end="")

    online_text = "Users online: "
    online_count = str(await client.get_online())
    online_length = len(online_text) + len(online_count)

    with term.location(term.width - online_length - 1, 0):
        print(await get_color(SERVER_DISPLAY_COLOR) + online_text \
              + term.normal + online_count, end="")

    divider = await get_color(SEPARATOR_COLOR) \
            + ("-" * term.width) + "\n" + term.normal

    screen_buffer.append(divider)


async def set_display(string):
    global display
    display = string

async def print_left_bar(left_bar_width):
    for i in range(2, term.height - MARGIN):
        print(term.move(i, left_bar_width) + await get_color(SEPARATOR_COLOR) + "|" \
              + term.normal)

    # Create a new list so we can preserve the server's channel order
    channel_logs = []
    # buffe to print
    buffer = []
    count = 0

    for servlog in server_log_tree:
        if servlog.get_name().lower() == client.get_current_server_name().lower():
            for chanlog in servlog.get_logs():
                channel_logs.append(chanlog)

    # sort channels to match the server's default chosen positions
    def quick_sort(channel_logs):
        if len(channel_logs) <= 1: return channel_logs
        else:
            return quick_sort([e for e in channel_logs[1:] \
                if e.get_channel().position <= channel_logs[0].get_channel().position]) + \
                [channel_logs[0]] + quick_sort([e for e in channel_logs[1:] \
                if e.get_channel().position > channel_logs[0].get_channel().position])

    channel_logs = quick_sort(channel_logs)
            
            
    for log in channel_logs:
        # don't print categories or voice chats
        # TODO: this will break on private messages
        if log.get_channel().type != discord.ChannelType.text: continue
        text = log.get_name()
        if len(text) > left_bar_width:
            text = text[0:left_bar_width - 4]
            text = text + "..."
        if log.get_channel() is client.get_current_channel():
            buffer.append(" " + term.green + text + term.normal + "\n")
        else: 
            if log.get_channel() is log.get_server().default_channel:
                text = text + "\n"
            else: 
                text = " " + text + "\n"

            if log.unread and log.get_channel() is not client.get_current_channel():
                buffer.append(term.blink_red(text))
            else: buffer.append(text)
        

        count += 1
        # should the server have *too many channels!*, stop them
        # from spilling over the screen
        if count == term.height - 5: break

    with term.location(1, 2):
        print("".join(buffer))


async def print_bottom_bar():
    screen_buffer.append(await get_color(SEPARATOR_COLOR) + ("-" * term.width) + "\n" \
                         + term.normal)

    if client.get_prompt() == DEFAULT_PROMPT:
            prompt = await get_color(PROMPT_BORDER_COLOR) + "[" + " " \
                    + await get_color(PROMPT_COLOR) + DEFAULT_PROMPT + " " \
                    + await get_color(PROMPT_BORDER_COLOR) + "]: " + term.normal
    else:
        prompt = await get_color(PROMPT_BORDER_COLOR) + "["  + \
                await get_color(PROMPT_COLOR) + "#" + client.get_prompt() \
                + await get_color(PROMPT_BORDER_COLOR) + "]: " + term.normal

    if len(input_buffer) > 0: screen_buffer.append(prompt + "".join(input_buffer))
    else: screen_buffer.append(prompt)

async def clear_screen():

    # instead of "clearing", we're actually just overwriting
    # everything with white space. This mitigates the massive
    # screen flashing that goes on with "cls" and "clear"
    del screen_buffer[:]
    wipe = (" " * (term.width) + "\n") * term.height
    print(term.move(0,0) + wipe, end="")

async def print_channel_log(left_bar_width):
    global INDEX
    
    # If the line would spill over the screen, we need to wrap it
    # NOTE: term.width is calculating every time this function is called.
    #       Meaning that this will automatically resize the screen.
    MAX_LENGTH = term.width - (left_bar_width + MARGIN*2)
    # For wrapped lines, offset them to line up with the previous line
    offset = 0
    # List to put our *formatted* lines in, once we have OK'd them to print
    formatted_lines = []
 
    for server_log in server_log_tree:
        if server_log.get_server() == client.get_current_server():
            for channel_log in server_log.get_logs():
                if channel_log.get_channel() == client.get_current_channel():

                    for msg in channel_log.get_logs():
                        # The lines of this unformatted message
                        msg_lines = []

                        color = ""
                        
                        try: 
                            r = msg.author.top_role
                            if r.name.lower() == "admin":
                                color = await get_color(ADMIN_COLOR)
                            elif r.name.lower() == "mod": 
                                color = await get_color(MOD_COLOR)
                            elif r.name.lower() == "bot": 
                                color = await get_color(BOT_COLOR)
                            elif CUSTOM_ROLE is not None and r.name == CUSTOM_ROLE:
                                color = await get_color(CUSTOM_ROLE_COLOR)
                            elif CUSTOM_ROLE_2 is not None and r.name == CUSTOM_ROLE_2:
                                color = await get_color(CUSTOM_ROLE_2_COLOR)
                            elif CUSTOM_ROLE_3 is not None and r.name == CUSTOM_ROLE_3:
                                color = await get_color(CUSTOM_ROLE_3_COLOR)
                            elif NORMAL_USER_COLOR is not None:
                                color = await get_color(NORMAL_USER_COLOR)
                            else: color = term.green
                        # if this fails, the user either left or was banned
                        except: 
                            if NORMAL_USER_COLOR is not None:
                                color = await get_color(NORMAL_USER_COLOR)
                            else: color = term.green

                        prefix_length = len(msg.author.display_name)
                        author_prefix = color + msg.author.display_name + ": "

                        proposed_line = author_prefix + term.white(msg.clean_content.strip())

                        # If our message actually consists of
                        # of multiple lines separated by new-line
                        # characters, we need to accomodate for this.
                        # --- Otherwise: msg_lines will just consist of one line
                        msg_lines = proposed_line.split("\n")

                        for line in msg_lines:

                            # strip leading spaces - LEFT ONLY
                            line = line.lstrip()

                            # If our line is greater than our max length,
                            # that means the author has a long-line comment
                            # that wasn't using new line chars...
                            # We must manually wrap it.
                            if len(line) > MAX_LENGTH:

                                # Loop through, wrapping the lines until it behaves
                                while len(line) > MAX_LENGTH:

                                    line = line.strip()

                                    # Take a section out of the line based on our max length
                                    sect = line[:MAX_LENGTH - offset]

                                    # Make sure we did not cut a word in half 
                                    sect = sect[:sect.strip().rfind(' ')]
                                    
                                    # If this section isn't the first line of the comment,
                                    # we should offset it to better distinguish it
                                    offset = 0
                                    if author_prefix not in sect:
                                        if line != msg_lines[0]:
                                            offset = prefix_length + 2

                                    # add in now formatted line!
                                    formatted_lines.append(Line(sect.strip(), offset))
                                
                                    # since we just wrapped a line, we need to make sure
                                    # we don't overwrite it next time

                                    # Split the line between what has been formatted, and
                                    # what still remains needing to be formatted
                                    if len(line) > len(sect):
                                        line = line.split(sect)[1]


                            # Once here, the string was either A: already short enough
                            # to begin with, or B: made through our while loop and has
                            # since been chopped down to less than our MAX_LENGTH
                            if len(line) > 0:
                                
                                offset = 0
                                if author_prefix not in line:
                                    offset = prefix_length + 2

                                formatted_lines.append(Line(line.strip(), offset))
                                
                    # Once all lines have been formatted, we may now print them
                    # the max number of lines that can be shown on the screen
                    MAX_LINES = await get_max_lines()
                    # where we should start printing from
                    if INDEX < MAX_LINES: INDEX = MAX_LINES 

                    # ----- Trim out list to print out nicely ----- #
                    # trims off the front of the list, until our index
                    del formatted_lines[0:(len(formatted_lines) - INDEX)]
                    # retains the amount of lines for our screen, deletes remainder
                    del formatted_lines[MAX_LINES:]

                    step = MARGIN // 2
                    for line in formatted_lines:
                        screen_buffer.append(" " * (left_bar_width + MARGIN + line.offset) + line.text + "\n")
   
                        step += 1

                    # return as not to loop through all channels unnecessarily
                    return

async def get_max_lines():
    return term.height - MARGIN * 2

async def get_left_bar_width():
    left_bar_width = term.width // LEFT_BAR_DIVIDER
    if left_bar_width < 8:
        return  8
    else: return left_bar_width

async def print_serverlist():

    if len(client.servers) == 0:
        print("Error: You are not in any servers.")
        return

    buffer = []
    for server in client.servers:
        buffer.append(server.name + "\n")
            
    clear_screen()
    system("echo '" + "Available Servers: \n" \
        + "---------------------------- \n \n" \
        + "".join(buffer) \
        + "\n \n" \
        + "(press \'q\' to quit this dialog) \n" \
        + "' | less")

async def print_channellist():
    if len(client.servers) == 0:
        print("Error: You are not in any servers.")
        return
    
    if len(client.get_current_server().channels) == 0:
        print("Error: Does this server not have any channels?")
        return

    buffer = []
    for channel in client.get_current_server().channels:
        if channel.type == ChannelType.text:
            buffer.append(channel.name + "\n")

    clear_screen()
    system("echo '" + "Available Channels in " \
           + client.get_current_server_name() + ": \n" \
           + "---------------------------- \n \n" \
           + "".join(buffer) \
           + "\n \n" \
           + "(press \'q\' to quit this dialog) \n" \
           + "' | less")

