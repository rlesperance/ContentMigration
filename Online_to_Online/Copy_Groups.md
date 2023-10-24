## Notebook Code

This code creates groups that exist on a source ArcGIS Online org to a target org. 
Also adds users.  Uses a user name map created with the Create Users script on this code repository. 
Alternatively the XLSX can be created manually:
Columns in the User_Mapping.xlsx:
   - sourcename
   - fullname
   - targetname

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
target_portal_url = 'https://targetorg.maps.arcgis.com'
#target_password = getpass(prompt='Please enter the password for the target Portal') # This will prompt you for the password rather then storing it
target_password = 'password'

# Log file location - specify the location of the log file to be created
basePath = r"C:\somewhere"
logging.basicConfig(filename = os.path.join(basePath, "UpdateGroups_log.txt"), level=logging.INFO)
now = datetime.now()
logging.info("{}  Begin group migration".format(str(now)))


basePath = r"C:\Somewhere"
userXLS = os.path.join(basePath, "User_Mapping.xlsx")
groupmapXLS = os.path.join(basePath, "Group_Mapping.xlsx")
```

## Connect to source and target portals

```python
# Instantiate Portal connections - use verify_cert = False to use self signed SSL
source = GIS(source_portal_url, source_admin_username, source_password, verify_cert = False, expiration = 9999)
logging.info("Connected to source portal "+source_portal_url+" as "+source_admin_username)

target = GIS(target_portal_url, target_admin_username, target_password, verify_cert = False, expiration = 9999)
logging.info("Connected to target portal "+target_portal_url+" as "+target_admin_username)
```

## Import user mapping 
Usernames may not be the same from org to org

```python
#Get user mapping from exported XLSX (generated in CopyUsers notebook)
userDF = pd.read_excel(userXLS, engine='openpyxl')
userDF
```

## Functions
   - GetNewUsername uses the imported XLS user mapping to find the new name
   - 

```python
def getNewUsername(username):
    try:
        newuser = userDF.loc[userDF.sourcename == username].values[0]
        return newuser[2]
    except Exception as Ex:
        print("User: {} :: {}".format(username, str(Ex)))
        return None

def copy_group(target, source, source_group):
    
    with tempfile.TemporaryDirectory() as temp_dir:
        target_group = {}
        target_group = {
        'title' : source_group.title,
        'tags' : source_group.tags,
        'description' : source_group.description,
        'snippet' : source_group.snippet,
        'access' : source_group.access,
        #'thumbnail' : source_group.thumbnail,
        'is_invitation_only' : source_group.isInvitationOnly,
        'sort_field' : source_group.sortField,
        'sort_order' : source_group.sortOrder,
        'is_view_only' : source_group.isViewOnly,
        'auto_join' : source_group.autoJoin,
        'provider_group_name' : source_group.providerGroupName,
        'provider' : source_group.provider}

        # if the group has display settings, add that attribute into the dict
        if group.displaySettings['itemTypes']:
            target_group['display_settings'] = source_group.displaySettings['itemTypes']

        thumbnail_file = None
        if 'thumbnail' in source_group:
            target_group['thumbnail'] = source_group.download_thumbnail(temp_dir)

        print ("creating group {}".format(source_group.title))
        
        try:
            #CREATE GROUP IN TARGET
            new_group = target.groups.create_from_dict(target_group)
        except Exception as Ex:
            print(str(Ex))
            print("Unable to create group "+ source_group.title)
            print (str(sys.exc_info()) + "\n")
            print(traceback.format_tb(sys.exc_info()[2])[0] + "\n")
            return None
        
        try:
            #Does the source group allow non-org users?   ARCGIS ONLINE ONLY
            if not hasattr(group, "membershipAccess"):
                updateurl = "https://www.arcgis.com/sharing/rest/community/groups/{}/update".format(new_group.id)
                agoltoken = target._con.token
                parameters = urllib.parse.urlencode({'membershipAccess': None, 'clearEmptyFields': True, 'token':agoltoken, 'f': 'json'}).encode('utf-8')
                parameters
                response = urllib.request.urlopen(updateurl, parameters).read().decode('utf-8')

                jsonResponse = json.loads(response)
                print ("Group changed to open membership: {}".format(jsonResponse['success']))

           #ADD MEMBERS TO GROUP
            print ("   Adding Members - ".format(new_group.title))
            members = source_group.get_members()
            if not members['owner'] == target_admin_username:
                newowner = getNewUsername(members['owner'])
                if not newowner == None:
                    new_group.reassign_to(newowner)
            if members['users']:
                for user in members['users']:
                    newuser = getNewUsername(user)
                    if newuser:
                        if user in members['admins']:
                            new_group.add_users(newuser, admins = newuser)
                        else:
                            new_group.add_users(newuser)
                    else:
                        print ("Inviting user: {}".format(user))  #User isn't in the org
                        new_group.invite_users([user])
        except Exception as Ex:
            print(str(Ex))
            print("Unable to add memebers "+ source_group.title)
            print (str(sys.exc_info()) + "\n")
            print(traceback.format_tb(sys.exc_info()[2])[0] + "\n")
            logging.error(Ex)

        return new_group
```

## Loop through groups from source and create

```python
groupMapping = []
source_groups = source.groups.search(max_groups=9999)
for group in source_groups:
    groupMap = {}
    groupMap["groupname"] = group.title
    groupMap["sourceID"] = group.id
    groupMap["targetID"] = ""
    
    target_groups = target.groups.search(query="title: {}".format(group.title))
    exists = False
    target_group = None
    for tg in target_groups:
        if tg.title == group.title:
            exists = True
            target_group = tg
            
    if exists:  #Add something here to add the users to existing group
        print ("{}:  group already exists".format(group.title))
        groupMap["targetID"] = target_group.id
    else:
        
        target_group = copy_group(target, source, group)
        if target_group:
            groupMap["targetID"] = target_group.id
            print ("  Target group {} created".format(target_group.title))

    groupMapping.append(groupMap)
```


## Output to XLS file
Take note of the format of the output.  This file will be used to add users to groups in the copy_groups notebook and by the copy_items script to assign ownership to items copied. 

```python
#Export Group Mapping to XLS sheet
df = pd.DataFrame.from_dict(groupMapping)
with pd.ExcelWriter(groupmapXLS, engine='openpyxl') as writer:
    df.to_excel(writer)
```
