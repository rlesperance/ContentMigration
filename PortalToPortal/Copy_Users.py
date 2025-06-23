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


# Log file location - specify the location of the log file to be created
basePath = r"C:\workspace"
logging.basicConfig(filename = os.path.join(basePath,"Migrate_Users_log.txt"), level=logging.INFO)
now = datetime.now()
logging.info("{}  Begin user migration".format(str(now)))

usermapXLS = os.path.join(basePath, "User_Mapping.xlsx")

# Instantiate Portal connections - use verify_cert = False to use self signed SSL
source = GIS(source_portal_url, source_admin_username, source_password, verify_cert = False, expiration = 9999)
logging.info("Connected to source portal "+source_portal_url+" as "+source_admin_username)

target = GIS(target_portal_url, target_admin_username, target_password, verify_cert = False, expiration = 9999)
logging.info("Connected to target portal "+target_portal_url+" as "+target_admin_username)

userDF = pd.read_excel(usermapXLS, engine='openpyxl')

def copy_user(target_portal, source_user, sourceDict, password):
    try: 
        # split the fullName
        full_name = source_user.fullName
        print ("Full Name: {}".format(full_name))
        print ("  First Name: {}".format(source_user.firstName))
        print ("  Last Name: {}".format(source_user.lastName))
        #first_name = full_name.split()[0]
        first_name = source_user.firstName
        try:
            #last_name = full_name.split(maxsplit = 1)[1]
            last_name = source_user.lastName
        except:
            last_name = 'NoLastName'
    
        if source_user.userLicenseTypeId == "editorUT" or source_user.userLicenseTypeId == "fieldWorkerUT":
            userType  = "creatorUT"
        else:
            userType = source_user.userLicenseTypeId
    
        print ("  userType = {}".format(userType))
        print ("  role = {}".format(source_user.roleId))
        
        # if there are roles that cannot be used, set the default role  (for instance the create method can't set user as admin)
        role = source_user.roleId
        if source_user.roleId == "cEjWdBndqtbRluJW" or source_user.roleId=="org_admin":
            role = "iAAAAAAAAAAAAAAA"

        if sourceDict["Type"] == "arcgis":
            target_user = target_portal.users.create(username = source_user.username,
                                                     password = password, 
                                                     firstname = first_name, 
                                                     lastname = last_name, 
                                                     email = source_user.email, 
                                                     description = source_user.description, 
                                                     role = role,
                                                     user_type = userType)
        
        if sourceDict["Type"] == "SAML":
            target_user = target_portal.users.create(username = sourceDict["targetname"],
                                                    password = "pwdNotUsed",
                                                    firstname = first_name,
                                                    lastname = last_name,
                                                    email = sourceDict["targetname"],
                                                    description = source_user.description,
                                                    user_type = userType,
                                                    role = role,
                                                    provider = 'enterprise',
                                                    idp_username=sourceDict["targetname"])
        
        if not target_user:
            Exception("source user Type incorrect")
        
        # update user properties not in create method
        target_user.update(access = source_user.access, 
                           tags = source_user.tags)

        return target_user
    
    except Exception as Ex:
        print(str(Ex))
        print("Unable to create user")
        print (str(sys.exc_info()) + "\n")
        print(traceback.format_tb(sys.exc_info()[2])[0] + "\n")
        logging.error(Ex)
        return None

def updateAddOns(sourceUser, target_user):
    licenses = source.admin.license.all()
    for lic in licenses:
        try:
            licType = lic.properties['listing']['title']
            ents = lic.user_entitlement(sourceUser.username)

            license = target.admin.license.get(licType)

            if ents:
                print (ents['entitlements'])
                license.assign(username=target_user.username, entitlements=ents['entitlements'])
        except Exception as ex:
            print ("Unable to update AddOns")
            print (str(sys.exc_info()) + "\n")
            logging.error(ex)


##  MAIN LOOP
for index, source_user in userDF.iterrows():
    try:
        u = source.users.get(source_user["sourcename"])
    except Exception as ex:
        print ("Username {} not found in source portal".format(source_user["sourcename"]))
        continue

    if not u:
        print ("Username {} not found in source portal".format(source_user["sourcename"]))
        continue
    print(u.username)
    
    users = target.users.search(source_user["targetname"])
    if users:
        targetuser = users[0]
        print ("Username {} already in target site".format(u.username))
        logging.info("Username {} already in target site".format(u.username))
        continue

    new_user = copy_user(target, u, source_user, "ChangeMe12345")

    #updateAddOns(u, new_user)
    
    logging.info("  Copied user")

