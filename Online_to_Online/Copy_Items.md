## Notebook Code

This code creates items that exist on a source ArcGIS Online org to a target org. 
   - Changes the name if necessary
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
logging.basicConfig(filename = r".\CopyUsers_log.txt", level=logging.INFO)
now = datetime.datetime.now()
logging.info("{}  Begin user migration".format(str(now)))

basePath = r"."
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
target = GIS(target_portal_url, target_admin_username, target_password, verify_cert = False)
logging.info("Connected to target portal "+target_portal_url+" as "+target_admin_username)
```

## Import user and group mapping 
Usernames may not be the same from org to org
Group IDs in the target must be mapped to the IDs from the source

```python
#Get user mapping from exported XLSX (generated in CopyUsers notebook)
userDF = pd.read_excel(userXLS, engine='openpyxl')
#Get user mapping from exported XLSX (generated in CopyGroups notebook)
groupDF = pd.read_excel(groupXLS,  engine='openpyxl')
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
```
Export to XLSX
```python
sourceDF = pd.DataFrame.from_dict(source_items_by_id)

with pd.ExcelWriter(itemsXLS, engine='openpyxl') as writer:
    sourceDF.to_excel(writer)
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

def copy_item(target, source_item, copydata=True):
    try:

        item_properties = {}
        #Get actual item
        item = source.content.get(source_item["itemID"])

        #FIND ITEM OWNER
        source_item_owner = source.users.get(item.owner)
        target_owner = getNewUsername(item.owner)
        if target_owner == None:
            print ("Target User not Found")
            target_owner = target_admin_username
        target_item_owner = target.users.get(target_owner)

        #FIND ITEM FOLDER
        item_folder_titles = [f['title'] for f in source_item_owner.folders 
                              if f['id'] == item.ownerFolder]
        folder_name = None
        if len(item_folder_titles) > 0:
            folder_name = item_folder_titles[0]

        #if folder does not exist for target user, create it
        if folder_name:
            target_user_folders = [f['title'] for f in target_item_owner.folders
                                   if f['title'] == folder_name]
            if len(target_user_folders) == 0:
                #create the folder
                target.content.create_folder(folder_name, target_item_owner.username)
        
    except Exception as copy_ex:
        print("\tError in copy setup " + source_item['title'])
        print("\t" + str(copy_ex))
        return None
    
    try:
        # CLONE THE ITEM to the target portal, assign owner and folder
        cloned_item = target.content.clone_items(items=[item],
                                                  owner=target_item_owner.username,
                                                 folder=folder_name,
                                                copy_data=copydata)[0]
    except Exception as copy_ex:
        print("\tError in copying " + source_item['title'])
        print("\t" + str(copy_ex))
        return None
    
    try:
        newtitle = "{}_{}".format(org, source_item['title'])
        print ("Changing name to {}".format(newtitle))
        cloned_item.update(item_properties={'title':newtitle})
        
        #Set sharing (privacy) information
        print ("Set sharing for item {}".format(cloned_item.title))
        share_everyone = item.access == 'public'
        share_org = item.access in ['org', 'public']
        share_groups = []
        if 'groups' in source_item:
            print ("creating sharing groups...")
            share_groups = groupIDsList(source_item["groups"])
        print (share_everyone, share_org, share_groups)
        cloned_item.share(everyone=share_everyone, org=share_org, groups=share_groups)
        
        categories = source_item["Categories"]
        itemlist = [{cloned_item.id:{"categories": ["/Categories/{}".format(categories)]}}]
        target.content.categories.assign_to_items(items=itemlist)
        

    except Exception as copy_ex:
        print("\tError sharing " + source_item['title'])
        print("\t" + str(copy_ex))

    return cloned_item
```

## Loop through items from xls prep and clone

```python
itemsXLS = os.path.join(basePath, "Pepco_Migration", "Pepco_Item_Prep_Run1Fix.xlsx")
itemsDF = pd.read_excel(itemsXLS,  engine='openpyxl')
itemsDF

#**********************************************************
#*****  CYCLE THROUGH DICTIONARY AND COPY ITEMS  **********
#**********************************************************
source_target_itemId_map = []  #Title, SourceID, Type, TargetID
#iterations = 1000
for index, source_item in itemsDF.iterrows():
#for source_item in source_items_by_id:
    
    source_target_dict = {}
    source_target_dict["Title"] = source_item["title"]
    source_target_dict["SourceID"] = source_item["itemID"]
    source_target_dict["Type"] = source_item["type"]
    source_target_dict["Owner"] = source_item["owner"]
    source_target_dict["TargetID"] = ""
    #check if already there
    exists = False
    for x in target.content.search(source_item["title"]):
        sourcekey = [s for s in x.typeKeywords if 'source' in s]
        if not sourcekey:
            continue
        if source_item["itemID"] == sourcekey[0].partition("-")[2]:
            print ("{}: {} is already in target".format(source_item["title"], source_item["type"]))
            source_target_dict["TargetID"] = x.id
            exists = True
    if not exists and not source_item["type"] in ['Operation View', 'Application', 'Notebook', 'Web Experience']:
        print("Copying {}: Type: {}  for {}".format(source_item["title"], source_item["type"], source_item["owner"]))
        target_item = copy_item(target, source_item)
        if target_item:
            source_target_dict["TargetID"] = target_item.id
        else:
            source_target_dict["TargetID"] = "Failed To Copy"
        
    source_target_itemId_map.append(source_target_dict)
```


## Output to XLS file
A record of what happened.  Items not copied will indicate they didn't copy

```python
itemsXLS = os.path.join(basePath, "Pepco_Migration", "FixApps_item_mapping.xlsx")
df = pd.DataFrame.from_dict(source_target_itemId_map)
with pd.ExcelWriter(itemsXLS, engine='openpyxl') as writer:
    df.to_excel(writer)
```
