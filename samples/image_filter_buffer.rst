===================
image_filter_buffer
=================== 

:Syntax: 
    **image_filter_buffer** *size*
 
:Default:
     ``1M`` 
 
:Context: 
   ``http`` 
 
   ``server`` 
 
   ``location`` 
 

Sets the maximum size of the buffer used for reading images. When a size is exceeded the server will return error ``415 (Unsupported Media Type)`` .   