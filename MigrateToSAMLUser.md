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


admin_username = 'adminuser'
portal_url = 'https://something.else.com/portal'
password = 'password
gis = GIS(portal_url, admin_username, password)#, verify_cert = False, expiration = 9999)

basePath = r""
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
                            user_type = "creatorUT",
                            role = user.role,
                            provider = 'enterprise',
                            idp_username=idpUsername)
    return target_user


def transferGroups(user, target_user):
    targetUserId = target_user.id
    orig_userid = user.id
    
    usergroups = user['groups']
    #print (usergroups)

    for group in usergroups:
        grp = gis.groups.get(group['id'])
        if (grp.owner == user.username):
            result = grp.reassign_to(target_user)
            print ("Reassigned group result:  {}: {}".format(grp.title, result))
        else:
            result = grp.add_users(target_user, admin=target_user) 
            print ("Added group result:  {}: {}".format(grp.title, result))
            #grp.remove_users(orig_userid) 


def transferContent(user, target_user):
    
    targetUserId = target_user.id
    usercontent = user.items()
    
    for item in usercontent:
        item.reassign_to(target_user.username)
        print ("Reassigned item:  {}, {}".format(item.title, item.type))
            
    folders = user.folders
    for folder in folders:
        gis.content.create_folder(folder['title'], target_user)  #assuming folder doesn't exist
        print ("Creating Folder {}".format(folder['title']))
        folderitems = olduser.items(folder=folder['title'])
        for item in folderitems:
            item.reassign_to(target_user.username, target_folder=folder['title'])
            print ("Reassigned item:  {}, {}".format(item.title, item.type))


#Get current user
for index, source_user in userDF.iterrows():
    user = gis.users.get(source_user["Username"])
    
    target_user = createUser(user, source_user)
    
    transferGroups(user, target_user)
    
    transferContent(user, target_user)

```

