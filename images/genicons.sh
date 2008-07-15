#!/bin/bash

INKSCAPE=inkscape

for i in `cat icons.svg |grep -o -e '%%[^%]*%%'|sed 's/%//g'` 
do
 echo "$INKSCAPE" icons.svg -z -e $i.png -i $i
 rm  -f $i.png
 "$INKSCAPE" icons.svg -z -e $i.png -i $i
done

cp ico24.png brz.png
# doesn't work... cannot set 8bpp alpha. use gimp instead
#convert ico*.png brz.ico
#rm -f ico*.png
