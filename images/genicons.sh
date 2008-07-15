#!/bin/bash

INKSCAPE=inkscape

for i in `cat icons.svg |grep -o -e '%%[^%]*%%'|sed 's/%//g'` 
do
 if [ $i.png -nt icons.svg ]; then
 	echo "Skip $i"
 else
	rm  -f $i.png
	echo "$INKSCAPE" icons.svg -z -e $i.png -i $i
	"$INKSCAPE" icons.svg -z -e $i.png -i $i
 fi
done

cp ico24.png brz.png
# doesn't work... cannot set 8bpp alpha. use gimp instead
#convert ico*.png brz.ico
#rm -f ico*.png
