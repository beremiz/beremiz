Widget Types
============


HMI:Animate
-----------


HMI:Animaterotation
-------------------


HMI:Assign
----------


HMI:Back
--------


HMI:Button
----------


HMI:Circularbar
---------------


HMI:Circularslider
------------------


HMI:Custom
----------


HMI:Customhtml
--------------


HMI:Display
-----------


HMI:Dropdown
------------


HMI:Foreach
-----------


HMI:Image
---------
| It is an SVG Image element with label
| ``HMI:Image:variable``
| where ``variable`` contains the HTTP GET path to the image it should display.


HMI:Input
---------


HMI:JsonTable
-------------
| It is a SVG (group) element with label
| ``HMI:JsonTable:path@notify_var@range_var@position_var@visible_var@filter_var``
| where:
* ``path`` is HTTP POST path used to fetch JSON list response
* ``range_var`` is a variable containing number of elements in a list
* ``position_var`` is a variable containing index of the first element from the list shown in the table
* ``visible_var`` is a variable with number of elements to be displayed in the table
* ``filter_var`` is a variable containing the string which is posted in a request for JSON response, and it's used to filter the results
| On render request, the widget does a POST request to the path. That request contains all the variables listed above.
| Handler for the request should be written in such manner that it returns a JSON list containing defined number of elements.
| Elements are objects with keys and values defined by a user.
| SVG element itself contains another element group ``data``. All of the elements in that group are also groups, with name ``[i]`` where ``i`` goes from 0 to ``visible_var - 1``. Only the last one is actually created, others are just copy of it.
| Elements from ``data`` can be placed in such manner to depict table rows.
| Elements in ``[i]`` can emulate columns. They can be:
* HMI:TextStyleList (label dictates the style and text content)
* Image (label dictates path to the image)
* Other SVG elements
| Any of the above elements can have label with ``onClick[acknowledge]=var`` which means that on a click on such element, the same POST request is invoked, but among ``options`` posted now there is a variable ``onClick[acknowledge]`` and its value is ``var``
| Beside ``data`` element, there can also be ``action_reset`` group element with similar behavior as stated above: click invokes POST with ``action_reset`` among ``options``.
| If it's needed to display images in a table, and those images should be loaded dynamically, one may use GET handler to load and return appropriate image.

HMI:Jump
--------


HMI:Keypad
----------


HMI:List
--------


HMI:Listswitch
--------------


HMI:Meter
---------


HMI:Multistate
--------------


HMI:Page
--------


HMI:Pathslider
--------------


HMI:Scrollbar
-------------


HMI:Slider
----------


HMI:Switch
----------


HMI:Textlist
------------


HMI:Textstylelist
-----------------


HMI:Tooglebutton
----------------


HMI:Xygraph
-----------

