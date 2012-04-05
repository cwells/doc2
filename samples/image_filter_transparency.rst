=======
image_filter_transparency
========
 
Syntax: **image_filter_transparency** ``on``|``off`` 
Default: ``on`` 
Context: ``http, server, location`` 

 Defines whether transparency should be preserved when transforming PNG images with colors specified by a palette, or in GIF images. The loss of transparency allows to obtain images of a better quality. The alpha channel transparency in PNG is always preserved.   