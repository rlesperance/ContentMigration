## Notebook Code

This code copies users from one ArcGIS Online org to another one. 
It takes the user and uses the properties to run the portal.users.create() function to create the user on the target. 
  Because ArcGIS Online only allows a unique username across all organizations, the new user's name needs to be different.  There is an "org" variable in the setup code that gets appended to the username to be added to the target.  


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

org = 'newOrg'   #This is going to be tagged to the end of each username

# Log file location - specify the location of the log file to be created
logging.basicConfig(filename = r".\CopyUsers_log.txt", level=logging.INFO)
now = datetime.datetime.now()
logging.info("{}  Begin user migration".format(str(now)))

basePath = r"."
usermapXLS = os.path.join(basePath, "User_Mapping.xlsx")
```

## Connect to source and target portals

```python
# Instantiate Portal connections - use verify_cert = False to use self signed SSL
source = GIS(source_portal_url, source_admin_username, source_password, verify_cert = False, expiration = 9999)
logging.info("Connected to source portal "+source_portal_url+" as "+source_admin_username)
target = GIS(target_portal_url, target_admin_username, target_password, verify_cert = False)
logging.info("Connected to target portal "+target_portal_url+" as "+target_admin_username)
```

## Get source users to be transferred

```python
# Get source users source_users = source.users.search('!esri_ & !admin',max_users=99999)
source_users = source.users.search('!esri_ & !esri_livingatlas',max_users=99999)

print (source_users)
logging.info("Total users to migrate: {}".foramt(len(source_users)))
```

## Functions

```python
def GetUserTypeName(userType):
    userTypes = [{"Type": "creatorUT","Descr": "Creator"}, {"Type": "viewerUT","Descr": "Viewer"}]
    typeDescr = next(item for item in userTypes if item["Type"]==userType)
    return typeDescr["Descr"]

def copy_user(target_portal, source_user, password, org):
    # split the fullName
    full_name = source_user.fullName
    first_name = full_name.split()[0]
    try:
        last_name = full_name.split(maxsplit = 1)[1]
    except:
        last_name = 'NoLastName'
    
    newusername = source_user.username
    if re.search(org, newusername, re.IGNORECASE):
        newusername = "{}_{}".format(newusername, "1")
    else:
        newusername = "{}_{}".format(newusername, org)
        
    userRole = source_user.role
    if userRole == "org_admin":
        userRole = "org_user"

    try: 
        target_user = target_portal.users.create(username = newusername,
                                                 password = password, 
                                                 firstname = first_name, 
                                                 lastname = last_name, 
                                                 email = source_user.email, 
                                                 description = source_user.description, 
                                                 role = userRole,
                                                 user_type = "Creator")

        if source_user.role == "org_admin":
            target_user.update_role("org_admin")
        
        # update user properties
        target_user.update(access = source_user.access, 
                           description = source_user.description, 
                           tags = source_user.tags)

        return target_user
    
    except Exception as Ex:
        print(str(Ex))
        print("Unable to create user "+ newusername)
        print (str(sys.exc_info()) + "\n")
        print(traceback.format_tb(sys.exc_info()[2])[0] + "\n")
        return None
```

## Actual loop through users to copy

```python
#  Cycle through source users and run copy routine
userMapping = []
for u in source_users:
    print(u.username)
    userMap = {}
    userMap["sourcename"] = u.username
    userMap["fullname"] = u.fullName
    
    targetUserCheck = target.users.get("{}_{}".format(u.username, org))
    if targetUserCheck:
        print ("Username {} already in target site".format(u.username))
        userMap["targetname"] = "Already in Target"
        continue

    new_user = copy_user(target, u, "ChangeMe12345", org)
    if new_user:
        userMap["targetname"] = new_user.username
    else:
        userMap["targetname"] = "Failed to Copy"
    
    logging.info(userMap)
    userMapping.append(userMap)
```

## Output to XLS file
Take note of the format of the output.  This file will be used to add users to groups in the copy_groups notebook and by the copy_items script to assign ownership to items copied. 

```python
#Export User Mapping to XLS sheet
df = pd.DataFrame.from_dict(userMapping)
with pd.ExcelWriter(usermapXLS, engine='openpyxl') as writer:
    df.to_excel(writer, sheet_name='Sheet1', index=None)
    
logging.info ("")
```

## Copy manually
Alternatively you can send a list to the copy function

```python
users = ["e000050"]
for user in users:
    u = source.users.get(user)
    new_user = copy_user(target, u, "ChangeMe12345", org)
    print (new_user.username)
```
