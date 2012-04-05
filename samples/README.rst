=======
image_filter
========
 
Syntax: **image_filter** ``off`` 
        **image_filter** ``test`` 
        **image_filter** ``size`` 
        **image_filter** ``rotate`` ``90`` | ``180`` | ``270`` 
        **image_filter** ``resize`` *width* *height* 
        **image_filter** ``crop`` *width* *height* 
Default: ```` 
Context: ``location`` 

 Sets the type of transformation to perform on images: 
     
    ``off``         
         turns off module processing in a surrounding location.      
    ``test``         
         ensures that responses are images in either JPEG, GIF, or PNG format. Otherwise, the error ``415 (Unsupported Media Type)`` is returned.      
    ``size``         
         outputs information about images in a JSON format, e.g.:     
    
    ::
    { "img" : { "width": 100, "height": 100, "type": "gif" } }
    
    
In case of an error, the following is output:
    
    
    ::
    {}
    
    
     
    ``rotate`` ``90``|``180``|``270``          
         rotates images counter-clockwise by the specified number of degrees. Value of the parameter can contain variables. Can be used either alone, or along with the ``resize`` and ``crop`` transformations.      
    ``resize`` ``width`` ``height``          
         proportionally reduces an image to the specified sizes. To reduce by only one dimension, another dimension can be specified as "``-``". In case of an error, the server will return code ``415 (Unsupported Media Type)``. Values of parameters can contain variables. When used along with the ``rotate`` parameter, the rotation happens **after** reduction.      
    ``crop`` ``width`` ``height``          
         proportionally reduces an image to the size of the largest side and crops extraneous edges by another side. To reduce by only one dimension, another dimension can be specified as "``-``". In case of an error, the server will return code ``415 (Unsupported Media Type)``. Values of parameters can contain variables. When used along with the ``rotate`` parameter, the rotation happens **before** reduction.  
   