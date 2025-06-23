from arcgis.gis import GIS
import pandas as pd
import logging
from datetime import datetime
import sys, os
import tempfile
import traceback
import openpyxl

# Source Portal information
source_admin_username = 'admin'
source_portal_url = 'https://gis.domain.org/portal'
source_password = 'password'

# Target Portal information
target_admin_username = 'rlesperance'
target_portal_url = 'https://maps.domain.org/portal'
target_password = 'password'

basePath = r"C:\workspace"
logging.basicConfig(filename = os.path.join(basePath, "UpdateGroups_log.txt"), level=logging.INFO)
now = datetime.now()
logging.info("{}  Begin group migration".format(str(now)))

userXLS = os.path.join(basePath, "User_Mapping.xlsx")
groupmapXLS = os.path.join(basePath, "Group_Mapping.xlsx")

# Instantiate Portal connections - use verify_cert = False to use self signed SSL
source = GIS(source_portal_url, source_admin_username, source_password, verify_cert = False, expiration = 9999)
logging.info("Connected to source portal "+source_portal_url+" as "+source_admin_username)

target = GIS(target_portal_url, target_admin_username, target_password, verify_cert = False, expiration = 9999)
logging.info("Connected to target portal "+target_portal_url+" as "+target_admin_username)

userDF = pd.read_excel(userXLS, engine='openpyxl')

def getNewUsername(username):
    try:
        newuser = userDF.loc[userDF.sourcename == username].values[0]
        return newuser[2]
    except Exception as Ex:
        print("User: {} :: {}".format(username, str(Ex)))
        return None

def copy_group2(target, source, source_group):
    try:
        temp_dir = tempfile.TemporaryDirectory()
        
        thumbnail_file = None
        if 'thumbnail' in source_group:
            thumbnail_file = source_group.download_thumbnail(temp_dir)

        dispset = None
        if group.displaySettings['itemTypes']:
            dispset = source_group.displaySettings


        shared_edit = None
        for capability in group.capabilities:
            if capability == 'updateitemcontrol':
                print ("   Group is Shared Edit")
                shared_edit=True
            #If the group is part of a distributed collaboration, may want to re-create manually
            if capability == 'distributed':
                print ("   Group is distributed!")
                return
        
        new_group = target.groups.create(
            title = source_group.title,
            tags = source_group.tags,
            description = source_group.description,
            snippet = source_group.snippet,
            access = source_group.access,
            thumbnail = thumbnail_file,
            is_invitation_only = source_group.isInvitationOnly,
            sort_field = source_group.sortField,
            sort_order = source_group.sortOrder,
            is_view_only = source_group.isViewOnly,
            auto_join = source_group.autoJoin,
            provider_group_name = source_group.providerGroupName,
            users_update_items = shared_edit
            )
        return new_group
    except Exception as Ex:
        print(str(Ex))
        print("Unable to create group "+ source_group.title)
        print (str(sys.exc_info()) + "\n")
        print(traceback.format_tb(sys.exc_info()[2])[0] + "\n")
        return None

def addMembers(source_group, new_group):
    try:
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
    except Exception as Ex:
        print(str(Ex))
        print("Unable to add memebers "+ source_group.title)
        print (str(sys.exc_info()) + "\n")
        print(traceback.format_tb(sys.exc_info()[2])[0] + "\n")
        logging.error(Ex)


## MAIN LOOP
groupMapping = []
source_groups = source.groups.search(max_groups=9999)
for group in source_groups:

    # if group.title != "Ammon Public Works":
    #     continue
    groupMap = {}
    groupMap["groupname"] = group.title
    groupMap["sourceID"] = group.id
    groupMap["targetID"] = ""

    print ("Copying group:  {}".format(groupMap["groupname"]))
    
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
        
        #addMembers(group, target_group)
    else:
        
        target_group = copy_group2(target, source, group)
        if not target_group:
            continue
        print ("  Target group {} created".format(target_group.title))
        if target_group:
            addMembers(group, target_group)
            groupMap["targetID"] = target_group.id
            print ("  Group membership set")
            
    groupMapping.append(groupMap)

#Export Group Mapping to XLS sheet
df = pd.DataFrame.from_dict(groupMapping)
with pd.ExcelWriter(groupmapXLS, engine='openpyxl') as writer:
    df.to_excel(writer)