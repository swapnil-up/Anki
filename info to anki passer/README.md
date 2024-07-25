## Introduction

This is an attempt to quickly add cards when you're just using the internet, reading a pdf or ebook, or wanting to remember a line of code. It was inspired from how ankidroid allows users to select some text then quickly open it within the anki add dialog box.
It requires ankiconnect to be running, along with anki to at least be open in the background. If you don't the script will open it for you though.

Anki Connect is great. It turned out to single-handedly have all of the functions within it.

Special thanks to reddit user u/xalbo who pointed out that Connect has the option to just add it then and there. 

### Problems

 This project still has too many hijinks such as:

1. ~~The cards don't open in the add dialog box before getting sent to the deck.~~ ~~The workaround was that I used zenity and the neovim as a dialog box to add in edits.~~ Connect has the code that open the GUI component .

	~~1.1. Because of these new custom dialog boxes, the problem then became that I needed to type {{c1:: }} everytime which is annoying. Have got neither working, though neovim should be easier to get this working with.~~ No longer a problem.
	
2. ~~I like cloze deletions but that option is unavailable without at least one deletion. But since I am selecting a block of text ankiconnect just passes the whole thing. My simple workaround is to add an empty cloze at the end of the highlighted text before passing so that all I need to do is delete that before making my cloze deletions. 
		'cloze_text="$highlighted_text {{c1::}}"' ~~ solved as neovim and zenity allow me to type in as needed.
		
3. ~~The anki app needs to be open.~~ Did a check to open if it is not open. 
		'# Check if Anki is running
			if ! pgrep -x "anki" > /dev/null
			then
				echo "Anki is not running. Launching Anki..."
				anki &
				# Wait for a few seconds to ensure Anki is up and running
				sleep 10
			fi'
			
4. ~~I use i3 as my window manager. So I create a shortcut that triggers this script. It didn't run directly, hence my need for creating a wrapper script and connecting the shortcut to the wrapper.~~ Somewhere along the development process this started working. 
	
### Other things tested

I did try to get the add cards editor to open via use of xdotool, which uses predefined prompts that are executed. I scraped this idea because of two reasons:

1. The anki window needed to be open in the same window as highlighted text. Window space is precious and this defeats a part of the purpose of a WM.

2. If the active screen was changed then the xdotool commands would execute in the other places. It needed to be specifically run from the home screen of anki too. 

3. Too slow. There were manual wait times that I had to encode. I couldn't do anything else during either. This was not async, which turned me off the idea. 

4. Other editors like Geany, Notepadqq, YAD. Either the screen was too convoluted or in the case of YAD custom keybindings weren't supported.

### Thoughts

The anki incremental reading add-on is great in my opinion. This is just for when sites have a cloudflare protection that does not allow the content to be scraped. For moments when you're lazy. For the moments when an innocuous read was inspirational but you don't wish to set everything up for cloze deletion. 

Would just having the add card editor manually open in a fourth of the screen not work? 
It probably would. Most of the time that solution is my own answer. or IR. But it is a lil clunky to say the least. Adding then removes you from the enjoyment of the reading at the moment. Besides I just really wanted to build this. :P

You could probably create a simple plain text note type and make this into an extraction feature too, now that I think of it.  

### Configurations for you

I was testing this idea out, hence I made the Testing Deck. You could import the cards into a dump deck. 

Cloze is king. But if you wanted to make this a basic type you'd just have to change the parameters around a lil to work with basic, or whatever your notetype is. 

### Future Revisions
	
	- [X] 1. Open that damn add cards dialog box. (Made a simplified one)
	- [ ] 2. Maybe add a date time into the extra column.
	- [ ] 3. Ooh, also where I took the highlight from. Maybe application name and the article piece name written within. 
	
	
	
## Misc

This was what was in the i3 script when I was using zenity:
	
	'#globally take a highlighted text and put it in anki
	bindsym Mod1+o exec --no-startup-id ~/run_add_to_anki.sh'


This is what I have now that I'm using neovim:
	'bindsym Mod1+o exec --no-startup-id gnome-terminal -e ~/add_to_anki.sh'
	
	
###### Tested and Running on 
	an Ubuntu jammy 22.04 x86_64
	an i3-wm as the windows manager
