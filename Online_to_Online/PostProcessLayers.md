## Notebook Code

This code modifies items that have been copied by the copy_items routine and need to be updated to reflect the following. 
   - Change the name if necessary
   - Sets ownership based on name mapping
   - Adds to groups using group ID mapping

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
import sys, os, ast
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
newitemsDF = pd.read_excel(itemMapXLS,  engine='openpyxl')  #Item Mapping XLS
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

def updateProperties(orig_item, target_item):
    
    print("Setting items for {}: Type: {}  for {}".format(orig_item.title, orig_item.type, orig_item.owner))
    logging.info("Setting items for {}: Type: {}  for {}".format(orig_item.title, orig_item.type, orig_item.owner))

    #Update Item Owner
    newOwner = getNewUsername(orig_item.owner)
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
        keywords.append('source-{}'.format(orig_item.itemid))
        target_item.update(item_properties={'typeKeywords':keywords})
        print ("  keywords applied:  {}".format(keywords))

    #Set sharing (privacy) information
    print ("Set sharing for item {}".format(target_item.title))
	orig_sharing = orig_item.sharing 
	target_sharing = target_item.sharing 
	
	target_sharing.sharing_level = orig_sharing.sharing_level 
	
    share_groups = orig_sharing.groups
    for group in share_groups.list():
	newID = groupDF.loc[groupDF.sourceID == group.id]
        if len(newIDs) > 0:
            newgroup = gis.groups.get(newID[0])
            target_sharing.groups.add(newgroup)
        else:
            print ("Cannot identify new group for {}".format(group))


    #might need to check if categories keyword exists if org has no categories
    categories = orig_item.categories
    itemlist = [{target_item.id:{"categories": categories}}]
    if len(categories) > 0:
        target.content.categories.assign_to_items(items=itemlist)
```

## Loop through items from xls prep and clone

```python
for index, target_row in newitemsDF.iterrows():
	orig_item = source.content.get(target_row["SourceID"])
	
	target_item = target.content.get(target_row["TargetID"])
    
   updateProperties(orig_item, target_item)
```
