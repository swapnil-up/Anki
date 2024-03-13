#THE DOCUMENTATION

### INTRODUCTION
This is my simple implementation to figure out how to add programming cards to my anki practise. 

The key idea is that since you can train fluency by learning vocab, in a similar vein you can learn almost to muscle memory how to implement basic blocks of code. Initially starting with realizing how to write if statements and reaching the point where you can write and completely internalize the working of a binary search tree. (Not at that level myself, hence the need to create the card.) 

Some other examples of the above would be if how we can touch type without thinking of where the fingers can go. The goal with this would be to think of what implementation to use and our hands would start flying across the keyboard. A metaphor might be thinking of the destination then your feet do the walking as you enjoy the scenery, or deal with immediate problems like potholes, instead of remembering how to move one feet in front of the other and how the arm swing is supposed to go again. To abstract those nitty gritty.

This implementation is simple and uses everything within the vanilla anki. There are more aesthetic UI, and things that have more detail and animations, this implementation is not that. I prefer a utilitarian approach. Have I mentioned that frontend past a certain point is frustrating for me?

I've gone with the idea of cloze deletions because I use them extensively for other types of cards that I make. It simplifies the need to excessively atomize (yes, you should atomize as further down as you can) as each card will be made for a cloze. And if you prefer a more question and answer format then you can just put the answer in a cloze


### HOW TO DO IT

First install anki duh.

##### Create the card type

1. Go to Tools
2. Click on Manage Note Types 
3. Click on Add (because we want a new card type, instead of modifying the other options.)
4. Clone the Add:cloze 
5. Rename to what you want (Mine's cloze for code typing)
6. Then click on fields and add a field for Type Hint.
7. Press the reposition on this screen to move it 2.
8. Hit save

#### Create the fields in the note type

For this you can simply copy the front, back and css from the files linked in the github repo. I'll explain what's happening below in case you want to modify it for your own satisfaction.

1. From the Manage Note Types (done in step 2 above) we now click cards
2. You'll see there's bubbles for front template, back template, and styling. The styling is where you put the css to make it all look pretty. Go to each and paste the corresponding html or css.

The key sauce is {{type:cloze:Text}} which requires you to enter the code block that is necessary for the cloze card on the front side. It is what displays the answer and what letters you missed on the back side

You could leave the styling as default. I've put in one for the hint to make it a lil less visible. The rest were autogenerated with the card type.


#### Usage

Now all you do is put in a cloze deletion, whatever blocks of code you want at your fingertips. You could leave the card type on whenever you're doing programming related work. It doesn't affect much. Just leave the text box empty when you're actually reviewing the cards.


### Acknowledgements
I'd like to thank those who came before me, and came up with their own solutions. There's: 

1. Liam Gower (https://www.liamgower.com/main-blog/learn-code-with-anki) and his own github repo: (https://github.com/leej11/anki-templates/blob/master/programming/)

2. The anki docs which had about the whole answer for me. This implementation is pretty moot if you'd just searched there. But hey, no reinventing the wheel so here you go (https://docs.ankiweb.net/templates/fields.html)

Feel free to share and star and add stuff here. I try to keep on working on github instead of going on HN for the 100th time, so I'll pull requests if they come through.