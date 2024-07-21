## Introduction

#### What is this?
This is a bash script that you can run via the terminal. It will convert all .txt files in a directory into .csv files, if they are in the format that kindle uses to convert its highlights into the stored MyClippings.txt. 

The idea is to then import this into anki and use the powerful inbuilt editor to add in the cloze deletions. 

### Why make this?
The anki import kindle clippings from the myclippings.txt add-on is very clunky. Especially as a predominantly keyboard user. 

This solution uses bash scripting to convert any .txt files that it sees in the directory it is stored and creates a csv file that separates the quote and the date added into two columns.

### Will this even work?
Kindles (at least the old ones) always creates a MyClippings.txt file. The highlights saved within are always in a predefined format. By leveraging this format we are indeed able to create distinct entries into a csv file.


## How to use this. 

1. First give it editing privileges. Via terminal that's chmod +x highlights-clipping.sh

2. Run the file. In the terminal that'd simply be ./highlights-clipping.sh

You'll then get a .csv file which has all your clippings.

## Other details to mention

1. The separator in the file is the pipe key (|). This seems like an easy distinction not commonly found within texts, especially novels.

2. The file name doesn't have to be MyClippings.txt in case you have multiple books that you'd like to subdivide into different csv files. I apparently had highlights back from 2017, hence this consideration. 

3. There's a little bit of redundancy that I did not remove which is that there's a line like quote|added, and another for the name of the clippings at the top. Feel free to edit this or add a pull request. 

4. Testing was done on an Ubuntu jammy 22.04 x86_64. The terminal uses bash. This should not be a major concern. I have checked with a few files, but there may indeed be a few errors within the .csv files. Be sure to run a blind check with a few quotes!!
