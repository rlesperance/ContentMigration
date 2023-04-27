## Notebook Code

This code copies roles from one ArcGIS Online org to another one. 


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

## Get roles to be transferred
Note that there are some stock roles that we don't need to transfer.  

```python
source_roles_set = set((role.name for role in source.users.roles.all(max_roles=99999)))
target_roles_set = set((role.name for role in target.users.roles.all(max_roles=99999)))

# Finding the difference between the sets, this is what is missing and needs to be migrated
diff_roles = source_roles_set.difference(target_roles_set)
```

## Create roles in target

```python
# Create a role dictionary to store old and new role IDs
role_mapping = []

# For each role in the source
for role in source.users.roles.all(max_roles=99999):
    # If the role name is in the migration set
    role_dict = {}
    role_dict["RoleName"]= role.name
    role_dict["SourceID"] = role.role_id
    role_dict["TargetID"] = ""
    if role.name in diff_roles:
        # Create the role
        new_role = target.users.roles.create(
                name = role.name,
                description = role.description,
                privileges = role.privileges)
        # Append the information to the crosswalk
        role_dict["TargetID"]=new_role.role_id
        print ("Copied role {}".format(role.name))
        logging.info("Role "+role.name+" copied")
    else:
        print ("Role {} already exists in target".format(role.name))
        role_dict["TargetID"] = "Already Exists"
        
    role_mapping.append(role_dict)
```


## Output to XLS file
Take note of the format of the output.  This file will be used to add users to groups in the copy_groups notebook and by the copy_items script to assign ownership to items copied. 

```python
#Export User Mapping to XLS sheet
df = pd.DataFrame.from_dict(role_mapping)
with pd.ExcelWriter(rolemapXLS, engine='openpyxl') as writer:
    df.to_excel(writer, sheet_name='Sheet1', index=None)
```
