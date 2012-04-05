=========================
image_filter_jpeg_quality
========================= 
Syntax: **image_filter_jpeg_quality** *quality* 
Default: ``75`` 
Context: ``http, server, location`` 

 Sets the desired ``quality`` of the transformed JPEG images. Acceptable values are in the 1..100 range. Lesser values usually imply both lower image quality and less data to transfer. The maximum recommended value is 95. Value of the parameter can contain variables.   