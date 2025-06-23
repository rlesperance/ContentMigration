General repository of scripts related to migrating content from Portal to Portal.  Could be ArcGIS Enterprise or ArcGIS Online.
One caveat to doing this with Enterprise is that the CLONE_ITEMS() method on content managers does not carry referenced services to a new Portal.  So if you have a map image service (with or without a feature layer) it reconstitutes each separately.  

Follow the steps below to use the notebooks.  It's suggested that the notebooks be run in Jupyter Notebook on a computer with the arcgis libraries (Pro or Server).   
You can use it in ArcGIS Online or Pro, but the use of XLSX documents to guide the process makes using Online difficult.  
