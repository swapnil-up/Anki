## Introduction

This is an attempt to quickly add cards when you're just using the internet, reading a pdf or ebook, or wanting to remember a line of code. It was inspired from how ankidroid allows users to select some text then quickly open it within the anki add dialog box.
It requires ankiconnect to be running, along with anki to at least be open in the background.

### Problems

 This project still has too many hijinks such as:
	1. The cards don't open in the add dialog box before getting sent to the deck.
	
	2. I like cloze deletions but that option is unavailable without at least one deletion. But since I am selecting a block of text ankiconnect just passes the whole thing. My simple workaround is to add an empty cloze at the end of the highlighted text before passing so that all I need to do is delete that before making my cloze deletions. 
		'cloze_text="$highlighted_text {{c1::}}"' 
		
	3. The anki app needs to be open. Did a check to open if it is not open. 
		'# Check if Anki is running
			if ! pgrep -x "anki" > /dev/null
			then
				echo "Anki is not running. Launching Anki..."
				anki &
				# Wait for a few seconds to ensure Anki is up and running
				sleep 10
			fi'
			
	4. I use i3 as my window manager. So I create a shortcut that triggers this script. It didn't run directly, hence my need for creating a wrapper script and connecting the shortcut to the wrapper. 
	
### Other things tested

I did try to get the add cards editor to open via use of xdotool, which uses predefined prompts that are executed. I scraped this idea because of two reasons:
	1. The anki window needed to be open in the same window as highlighted text. Window space is precious and this defeats a part of the purpose of a WM.
	2. If the active screen was changed then the xdotool commands would execute in the other places. It needed to be specifically run from the home screen of anki too. 
	3. Too slow. There were manual wait times that I had to encode. I couldn't do anything else during either. This was not async, which turned me off the idea. 

### Thoughts

The anki incremental reading add-on is great in my opinion. This is just for when sites have a cloudflare protection that does not allow the content to be scraped. For moments when you're lazy. For the moments when an innocuous read was inspirational but you don't wish to set everything up for cloze deletion. 

Would just having the add card editor manually open in a fourth of the screen not work? 
It probably would. Most of the time that solution is my own answer. or IR. But it is a lil clunky to say the least. Adding then removes you from the enjoyment of the reading at the moment. Besides I just really wanted to build this. :P

You could probably create a simple plain text note type and make this into an extraction feature too, now that I think of it.  

### Configurations for you

I was testing this idea out, hence I made the Testing Deck. You could import the cards into a dump deck. 

Cloze is king. But if you wanted to make this a basic type you'd just have to change the parameters around a lil to work with basic, or whatever your notetype is. 

### Future Revisions
	
	1. Open that damn add cards dialog box.
	2. Maybe add a date time into the extra column.
	3. Ooh, also where I took the highlight from. Maybe application name and the article piece name written within. 
