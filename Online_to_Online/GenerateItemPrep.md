## Notebook Code

This code creates the initial input list for the copy items code in this repository. 
Code
  - Connects to the source portal
  - loops through each user's content, including folders, adds to a list
  - loops through groups identifying the layers shared, and adds the group ID to the item list
  - exports the list as an XLSX file

From there you can use the output as the input for the copy_items routine.  The XLSX can be edited to remove items you don't need to copy

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

## First time prep inventory
This section of code develops a list of all content from all users on the old site
You may take the output of this and modify the XLS prep document to only include items you want to copy to the new site. 

```python
# Get source users source_users = source.users.search('!esri_ & !admin',max_users=99999)
source_users = source.users.search('!esri_ & !esri_livingatlas',max_users=99999)
source_groups = source.groups.search("!owner:esri_* & !Basemaps",max_groups=99999)

source_items_by_id = []
for user in source_users:
    #if not user.username == "Ahjung.Kim_pepco":
        #continue
    num_items = 0
    num_folders = 0
    print("Collecting item ids for {}".format(user.username), end="\t\t")
    user_content = user.items(max_items=9999)
    
    # Get item ids from root folder first
    for item in user_content:
        num_items += 1
        source_item = {}
        source_item["itemID"] = item.id
        source_item["title"] = item.title 
        source_item["type"] = item.type 
        source_item["owner"] = item.owner
        source_item['groups'] = []
        source_items_by_id.append(source_item)
    
    # Get item ids from each of the folders next
    folders = user.folders
    for folder in folders:
        num_folders += 1
        folder_items = user.items(folder=folder['title'], max_items=9999)
        for item in folder_items:
            num_items += 1
            source_item = {}
            source_item["itemID"] = item.id
            source_item["title"] = item.title 
            source_item["type"] = item.type 
            source_item["owner"] = item.owner
            source_item["groups"] = []
            source_items_by_id.append(source_item)
    
    print("Number of folders {} # Number of items {}".format(str(num_folders), str(num_items)))
    logging.info("Number of folders {} # Number of items {}".format(str(num_folders), str(num_items)))
```

Add groups for each item
```python
for group in source_groups:
    #iterate through each item shared to the source group
    for group_item in group.content():
        try:
            print ("Group: {} :: Item: {}".format(group.title, group_item.title))
            item = next(x for x in source_items_by_id if x["itemID"] == group_item.id)
            print (item["itemID"])
            groups = item["groups"]
            groups.append(group.id)
            item["groups"] = groups
            itemnum = source_items_by_id.index(item)
            source_items_by_id[itemnum] = item
        except:
            print("Cannot find item : " + group_item.itemid)
     logging.info("Group reviewed: {}".format(group.title))
```
Export to XLSX
```python
sourceDF = pd.DataFrame.from_dict(source_items_by_id)

with pd.ExcelWriter(itemsXLS, engine='openpyxl') as writer:
    sourceDF.to_excel(writer)
    
logging.info("Prep file created:  {}".format(itemsXLS))
```


