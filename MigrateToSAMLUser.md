If you need to migrate your users that own content to new users under a SAML authentication method you need to cover a few things with each user. 
    1. Create the new user
    2. Add the new user to the same groups the existing user is in
    3. Change the ownership of all the items for each user to their respective new user
    4. optionally delete the old user

This code is a simple way of doing this.  Can't guarangee it'll work in all cases.  There are some consideration for groups with shared edit set and item dependency that could probably be integrated into this code.

## Excel data

The script uses an XLSX file to drive the loop.  The Excel contains 6 fields detailed below providing information on the source user and the new users's information. 

Fields: 
Username:  source user
New_Username:  target username
IDP_Username:  If this is an enterprise user, this needs to be filled out
FirstName:  Fill this and the next two out like you orndarily would. 
LastName:
Email:  

In the code below I have it hardwired to add SAML users  (provider = 'enterprise').  You could recode this to go the other direction, but you'd leave out the IDP username variable. 

## Code

```python

from arcgis.gis import GIS
import pandas as pd
import sys, os
import traceback
from datetime import datetime
import logging
import openpyxl

admin_username = 'adminuser'
portal_url = 'https://something.else.com/portal'
password = 'password
gis = GIS(portal_url, admin_username, password)#, verify_cert = False, expiration = 9999)

basePath = r""
logging.basicConfig(filename = os.path.join(basePath,"UserLog_{}.txt".format(now.strftime("%Y%m%d%H%M%S"))), level=logging.INFO)
logging.info("{}  Begin user migration".format(str(now)))

usermapXLS = os.path.join(basePath, "UserMapping.xlsx")
userDF = pd.read_excel(usermapXLS, engine='openpyxl')

def createUser(user, source_user):
    
    newUsername = source_user["New_Username"]
    idpUsername=source_user["IDP_Username"]
    firstName = source_user["FirstName"]
    lastName = source_user["LastName"]
    email = source_user["Email"]

    target_user = gis.users.create(username = newUsername,
                            password = "pwdNotUsed",
                            firstname = firstName,
                            lastname = lastName,
                            email = email,
                            description = user.description,
                            user_type = user.userLicenseTypeId,
                            role = user.roleId,
                            provider = 'enterprise',
                            idp_username=idpUsername)
    return target_user

def updateAddOns(sourceUser, target_user):
    licenses = gis.admin.license.all()
    for lic in licenses:
        try:
            licType = lic.properties['listing']['title']
            ents = lic.user_entitlement(sourceUser.username)

            license = gis.admin.license.get(licType)

            if ents:
                print (ents['entitlements'])
                license.assign(username=target_user.username, entitlements=ents['entitlements'])
        except Exception as ex:
            print (str(sys.exc_info()) + "\n")
            logging.error(ex)
    

def transferGroups(user, target_user):
    targetUserId = target_user.id
    orig_userid = user.id
    
    usergroups = user['groups']
    #print (usergroups)

    for group in usergroups:
        groupname = group['title']
        try:
            logging.info("Adding new user to group: {}".format(groupname))
            grp = gis.groups.get(group['id'])
            members = grp.get_members()
            if (grp.owner == user.username):
                result = grp.reassign_to(target_user)
                print ("Reassigned group result:  {}: {}".format(grp.title, result))
                logging.info ("Reassigned group result:  {}: {}".format(grp.title, result))
            else:
                result = grp.add_users(usernames=target_user.username)
                print ("Added group result:  {}: {}".format(grp.title, result))
                if user.username in members['admins']:
                    grp.update_users_roles(managers = [target_user])
                #grp.remove_users(orig_userid)
        except Exception as ex:
            print (ex)
            logging.error("Error assigning user to group")
            logging.error(ex) 


def transferContent(user, target_user):
    
    targetUserId = target_user.id
    usercontent = user.items()
    
    for item in usercontent:
        errorItem = {}
        try:
            logging.info("Reassigning item: {}  -  {}".format(item.title, item.type))
            itemsharing = item.shared_with
            item.unshare(groups=itemsharing['groups'])  #Unshare
            item.reassign_to(target_user.username)
            item.share(everyone=itemsharing['everyone'], org=itemsharing['org'], groups=itemsharing['groups'], 
                       allow_members_to_edit=True)   #reshare
            
            print ("Reassigned item:  {}, {}".format(item.title, item.type))
        except Exception as ex:
            print (ex)
            logging.error("Error reassigning item: {}".format(item.title))
            logging.error(ex)
            errorItem["title"] = item.title
            errorList.append(errorItem)
            
    folders = user.folders
    for folder in folders:
        folder_list = [i['title'] for i in folders]
        if folder['title'] not in folder_list:
            print ("Creating Folder {}".format(folder['title']))
            gis.content.create_folder(folder['title'], target_user)  #folder doesn't exist
            
        folderitems = user.items(folder=folder['title'])
        for item in folderitems:
            errorItem = {}
            try:
                logging.info("Reassigning item: {}  -  {}".format(item.title, item.type))
                itemsharing = item.shared_with
                item.unshare(groups=itemsharing['groups'])  #Unshare
                item.reassign_to(target_user.username, target_folder=folder['title'])
                item.share(everyone=itemsharing['everyone'], org=itemsharing['org'], groups=itemsharing['groups'], 
                           allow_members_to_edit=True)   #reshare
                print ("Reassigned item:  {}, {}".format(item.title, item.type))
            except Exception as ex:
                print (ex)
                logging.error("Error reassigning item: {}".format(item.title))
                logging.error(ex)
                errorItem["title"] = item.title
                errorList.append(errorItem)


#Get current user
errorList = []

for index, source_user in userDF.iterrows():
    if source_user["Username"] != "ksullivan@HAWAIICOUNTY":
        continue
    logging.info("Attempting to migrate user: {}".format(source_user["Username"]))
    user = gis.users.get(source_user["Username"])
    newUsername = source_user["New_Username"]
    
    if len(gis.users.search(query=newUsername)) == 0:
        print ("Creating user {}".format(newUsername))
        target_user = createUser(user, source_user)
    else:
        print ("user exists: {}".format(newUsername))
        target_user = gis.users.get(source_user["New_Username"])
        #print ("Updating user")
        #updateUser(target_user, user)
        
    if target_user == None or not target_user:
        print ("target user not created or does not exist")
        continue
        
    print ("  Update AddOn Licenses")
    #updateAddOns(user, target_user)
    
    print ("  updating groups")
    #transferGroups(user, target_user)
    
    print ("  transferring content")
    transferContent(user, target_user)
    
    logging.info("Successfully transferred user: {}".format(target_user.username))

#ExportErrorList
now = datetime.now()
errlistname = "Error_List_{}.txt".format(now.strftime("%Y%m%d%H%M%S"))
errorListXLS = os.path.join(basePath,  errlistname)

df = pd.DataFrame.from_dict(errorList)

with pd.ExcelWriter(errorListXLS, engine='openpyxl') as writer:
    df.to_excel(writer)

# DISABLE ALL USERS IN LIST
for index, source_user in userDF.iterrows():
    user = gis.users.get(source_user["Username"])
    print (user.username, user.level, user.role, user.roleId)
    user.disable()
```

## Code
Optional code for using the same spreadsheet input to delete the users. 
Must remove their add-on extension licensing before removing them
   - (also assumes they don't now own any content)

```python
def deleteUser(user):

    try:
        licenses = gis.admin.license.all()
        for lic in licenses:

            licType = lic.properties['listing']['title']
            ents = lic.user_entitlement(user.username)

            license = gis.admin.license.get(licType)

            if ents:
                license.revoke(username=user.username, entitlements='*')
                print ("...revoked license  {}".format(ents['entitlements']))
        
        user.delete()
        print ("...user deleted")
    except Exception as ex:
        print (str(sys.exc_info()) + "\n")
        logging.error(ex)

for index, source_user in userDF.iterrows():
    print ("Attempting to delete user: {}".format(source_user["Username"]))
    logging.info("Attempting to delete user: {}".format(source_user["Username"]))
    user = gis.users.get(source_user["Username"])
    
    deleteUser(user)
    
```
