## Notebook Code

This code modifies items that have been copied by the copy_items routine and need to be updated to reflect the following. 
   - Change the name if necessary
   - Sets ownership based on name mapping
   - Adds to groups using group ID mapping
   - Adds categories if desired (in prep xls)

Uses a user name map created with the Create Users script in this code repository. 
Alternatively the XLSX can be created manually:
Columns in the User_Mapping.xlsx:
   - sourcename
   - fullname
   - targetname

Uses a group name map created with the Create Groups script in this code repository. 
Alternatively the XLSX can be created manually:
Columns in the Group_Mapping.xlsx:
   - groupname
   - sourceID
   - targetID

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

# Target Portal information
target_admin_username = 'adminuser'
target_portal_url = 'https://targetorg.arcgis.com'
#target_password = getpass(prompt='Please enter the password for the target Portal') # This will prompt you for the password rather then storing it
target_password = 'password'

# Log file location - specify the location of the log file to be created
basePath = r"C:\somewhere"
logging.basicConfig(filename = os.path.join(basePath, "UpdateItems_log.txt"), level=logging.INFO)
now = datetime.datetime.now()
logging.info("{}  Begin user migration".format(str(now)))

userXLS = os.path.join(basePath,  "User_Mapping.xlsx")
groupXLS = os.path.join(basePath,  "Group_Mapping.xlsx")
itemsXLS = os.path.join(basePath,  "Item_Prep.xlsx")
itemMapXLS = os.path.join(basePath,  "Item_Mapping.xlsx")

#Are we replicating item properties?
assignOwner = True
assignSharing = True
assignCategories = True
```

## Connect to source and target portals

```python
# Instantiate Portal connections - use verify_cert = False to use self signed SSL
source = GIS(source_portal_url, source_admin_username, source_password, verify_cert = False, expiration = 9999)
logging.info("Connected to source portal "+source_portal_url+" as "+source_admin_username)

target = GIS(target_portal_url, target_admin_username, target_password, verify_cert = False, expiration = 9999)
logging.info("Connected to target portal "+target_portal_url+" as "+target_admin_username)
```

## Import user and group mapping 
Usernames may not be the same from org to org
Group IDs in the target must be mapped to the IDs from the source

```python
userDF = pd.read_excel(userXLS, engine='openpyxl')  # User mapping XLS
groupDF = pd.read_excel(groupXLS,  engine='openpyxl')  # Group mapping XLS
itemsDF = pd.read_excel(itemsXLS,  engine='openpyxl')  # Item Prep XLS
newitemsDF = pd.read_excel(newitemsXLS,  engine='openpyxl')  #Item Mapping XLS
```


## Functions
   - getNewUsername uses the imported XLS user mapping to find the new name
   - groupIDsList gets the list of target groups the item is shared with based on the source groups
   - Copy_item is the main block setting up and copying each item. 


```python
def getNewUsername(username):
    newuser = userDF.loc[userDF.sourcename == username].values[0]
    return newuser[2]

def groupIDsList(groups):
    texttolist = ast.literal_eval(groups)
    grouplist = []
    for group in texttolist:
        newgroups = groupDF.loc[groupDF.sourceID == group]
        if len(newgroups) > 0:
            newgroup = newgroups.values[0]
            grouplist.append(newgroup[3])
        else:
            print ("Cannot identify new group for {}".format(group))
    return grouplist

def updateProperties(source_item, item):

    target_item = target.content.get(item["TargetID"])
    
    print("Setting items for {}: Type: {}  for {}".format(source_item["title"], source_item["type"], source_item["owner"]))
    logging.info("Setting items for {}: Type: {}  for {}".format(source_item["title"], source_item["type"], source_item["owner"]))

    orig_item = source.content.get(source_item["itemID"])

    #Update Item Owner
    newOwner = getNewUsername(source_item["owner"])
    print ("Updating owner to {}".format(newOwner))
    target_item.reassign_to(newOwner)

    #Source ID from old ORG so other related cloned maps and apps will find it
    print ("  Update Keywords")
    keywords = target_item.typeKeywords
    targetMap = [s for s in keywords if 'source-' in s]
    if targetMap:
        targetMapParse = targetMap[0].partition("-")[2]
        print ("  Source keyword exists: {}".format(targetMapParse))
    else:
        keywords.append('source-{}'.format(source_item['itemID']))
        target_item.update(item_properties={'typeKeywords':keywords})
        print ("  keywords applied:  {}".format(keywords))

    #Set sharing (privacy) information
    print ("Set sharing for item {}".format(target_item.title))
    share_everyone = orig_item.access == 'public'
    share_org = orig_item.access in ['org', 'public']
    share_groups = []
    if 'groups' in source_item:
        print ("creating sharing groups...")
        share_groups = groupIDsList(source_item["groups"])
    print (share_everyone, share_org, share_groups)
    target_item.share(everyone=share_everyone, org=share_org, groups=share_groups)

    #might need to check if categories keyword exists if org has no categories
    categories = source_item["Categories"]
    itemlist = [{target_item.id:{"categories": ["/Categories/{}".format(categories)]}}]
    if len(categories) > 0:
        target.content.categories.assign_to_items(items=itemlist)
```

## Loop through items from xls prep and clone

```python
for index, target_item in newitemsDF.iterrows():
    sourceID = target_item["SourceID"]
    source_items = itemsDF.loc[(itemsDF.itemID == sourceID)]
    
    updateProperties(source_items.iloc[0], target_item)
```
