## Notebook Code

This is like the initial input list for the copy items code, but we're including a usage attribute.  ArcGIS Online allows you to poll how often a content item is used. 
With little effort, you can get the last entry for this content, indicating the last time the content was used. 
In this case we are limiting the search to a year.  The longer you look back the less efficient it gets. 
Code
  - Connects to the source portal
  - loops through each user's content, including folders, adds to a list
    - includes usage data
  - exports the list as an XLSX file


## Setup Code

```python
from arcgis.gis import GIS
from getpass import getpass

import pandas as pd
import logging
from datetime import datetime
import sys, os
import tempfile
import traceback
import openpyxl

# Source Portal information
source_admin_username = 'adminuser'
source_portal_url = 'https://sourceorg.maps.arcgis.com'
#source_password = getpass(prompt='Please enter the password for the source Portal') # This will prompt you for the password rather then storing it
source_password = 'password'

# Log file location - specify the location of the log file to be created
basePath = r"."
logging.basicConfig(filename = os.path.join(basePath, "GeneratePrep_log.txt"), level=logging.INFO)
now = datetime.now()
logging.info("{}  Begin item prep".format(str(now)))

itemsXLS = os.path.join(basePath,  "Item_Prep.xlsx")

```

## Connect to source and target portals

```python
# Instantiate Portal connections - use verify_cert = False to use self signed SSL
source = GIS(source_portal_url, source_admin_username, source_password, verify_cert = False, expiration = 9999)
logging.info("Connected to source portal "+source_portal_url+" as "+source_admin_username)
```

## Inventory
This section of code develops a list of all content from all users on the old site

```python
source_users = source.users.search('!esri_ & !esri_livingatlas',max_users=99999)

source_items_by_id = []
for user in source_users:
    #if not user.username == "Person_to_exclude":
        #continue
    num_items = 0
    num_folders = 0
    print("Collecting item ids for {}".format(user.username), end="\t\t")
    user_content = user.items(max_items=9999)
    
    # Get item ids from root folder first
    for item in user_content:
        usage = item.usage(date_range='1Y', as_df=True)
        x = usage.query('Usage != 0')
        if len(x) > 0:
            dt = x.iloc[-1:].Date.item()
        else:
            dt = 'Null'
        
        num_items += 1
        source_item = {}
        source_item["itemID"] = item.id
        source_item["title"] = item.title 
        source_item["type"] = item.type 
        source_item["owner"] = item.owner
        source_item['lastuse'] = dt
        source_items_by_id.append(source_item)
    
    # Get item ids from each of the folders next
    folders = user.folders
    for folder in folders:
        num_folders += 1
        folder_items = user.items(folder=folder['title'], max_items=9999)
        for item in folder_items:
            usage = item.usage(date_range='1Y', as_df=True)
            x = usage.query('Usage != 0')
            if len(x) > 0:
                dt = x.iloc[-1:].Date.item()
            else:
                dt = 'Null'
            
            num_items += 1
            source_item = {}
            source_item["itemID"] = item.id
            source_item["title"] = item.title 
            source_item["type"] = item.type 
            source_item["owner"] = item.owner
            source_item["lastuse"] = dt
            source_items_by_id.append(source_item)
    
    print("Number of folders {} # Number of items {}".format(str(num_folders), str(num_items)))
    logging.info("Number of folders {} # Number of items {}".format(str(num_folders), str(num_items)))
```

Export to XLSX
```python
sourceDF = pd.DataFrame.from_dict(source_items_by_id)

with pd.ExcelWriter(itemsXLS, engine='openpyxl') as writer:
    sourceDF.to_excel(writer)
    
logging.info("Prep file created:  {}".format(itemsXLS))
```



