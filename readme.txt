Dependencies:
    python 3
    PyGObject (pip3 install pygobject)

usage: python3 annotateImages.py [-h] [-i str] [-t str] [-p str]

    GUI to annotate images.

    optional arguments:
      -h, --help            show this help message and exit
      -i str, --images str  Folder with images (str).
      -t str, --types  str  File with point types in csv (str).
      -p str, --points str  File of saved points in csv (str).

GUI usage:

    Open a image directory with the first button in the toolbox (ctrl-O)
    or only a single image with the next button. (ctrl-I)

    To open the previous image in the folder use 3. button (ctrl-shift-P)
    To open the next image in the folder use 4. button (ctrl-shift-N).

    Open a csv file with the different types of points on the 5. button (ctrl-T).
    Choose the desired type of point in the drop-down (9. button) or using the
    numbers.

    Open a csv file with markings on the 7. button (ctrl-M).
    save a csv file with the markings on the 6. button (ctrl-S).
    save as can be achieved by (ctrl-shift-S)

    Use the up and down arrows button (8. button) to switch between the original
     image and a computer segmented image. (ctrl-<)

    left click to make a marking or left drag to make a size marking.
    right click to remove a marking or size marking (with the mouse over the big circle).
    ctrl left click also removes markings.
    Middle click and drag to scroll.

    zoom in (ctrl-+) and zoom out (ctrl--) on the + or - buttons or zoom to 100%
     using the 1 button (ctrl-0).
    The zoom level can also be adjusted on the slider, by dragging or scrolling
    the mouse wheel when over the slider.
    Page Up, Page Down, Home, End and ctrl-arrow-key can also be used to zoom.
    (can happen that the slider need to be click beforehand)
    Zooming can take some time and the progress bar to the left will show the
    progress and display "done".

    To the left is a table holding a summary of the different images and
    how many points that have been added and of what type.
    It also shows the last marking made.

    In the top left is a status-bar showing relevant information.

    In the app menu bar all actions can be found and there corresponding
    shortcut.

point types file format:
    header: color,type

    example:
        color,type
        #FF0000, Scotch broom
        #0000FF, Giant hogweed

saved markings file format:
    header: image,type,x,y,size,angle,red,green,blue,alpha

    example:
        image,type,x,y,size,angle,red,green,blue,alpha
        ./DJI_0001.JPG,Scotch broom,490.4671223958333,392.4251302083333,,,0.0,0.0,1.0,1
        ./DJI_0001.JPG,Scotch broom,623.2410481770833,223.220458984375,1.3333333333333333,-0.0,1.0,0.0,0.0,1
