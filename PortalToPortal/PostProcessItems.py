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
logging.basicConfig(filename = os.path.join(basePath, "UpdateItems_log.txt"), level=logging.INFO)
now = datetime.now()
logging.info("{}  Begin updating item properties".format(str(now)))

userXLS = os.path.join(basePath,  "User_Mapping.xlsx")
itemMapXLS = os.path.join(basePath,  "Item_Mapping.xlsx")

# Instantiate Portal connections - use verify_cert = False to use self signed SSL
source = GIS(source_portal_url, source_admin_username, source_password, verify_cert = False, expiration = 9999)
logging.info("Connected to source portal "+source_portal_url+" as "+source_admin_username)

target = GIS(target_portal_url, target_admin_username, target_password, verify_cert = False, expiration = 9999)
logging.info("Connected to target portal "+target_portal_url+" as "+target_admin_username)

userDF = pd.read_excel(userXLS, engine='openpyxl')  # User mapping XLS
newitemsDF = pd.read_excel(itemMapXLS,  engine='openpyxl')  #Item Mapping XLS

def getNewUsername(username):
    newusers = userDF.loc[userDF.sourcename == username]
    if newusers.empty or len(newusers) < 1:
        return None

    newuser = newusers.values[0]
    return newuser[2]

def updateOwner(orig_item, target_item):
    try:
        #Update Item Owner
        newOwner = getNewUsername(orig_item.owner)
        if newOwner == None:
            print ("Target User not Found")
            newOwner = target_admin_username
        print ("  Updating owner to {}".format(newOwner))
        logging.info("  Updating owner to {}".format(newOwner))
        target_item.reassign_to(newOwner)
    except Exception as copy_ex:
        print("\tError in update owner: " + target_item.title)
        print("\t" + str(copy_ex))
        print (str(sys.exc_info()) + "\n")
        print(traceback.format_tb(sys.exc_info()[2])[0] + "\n")
        logging.error(copy_ex)
        return None

def updateFolder2(orig_item, target_item):
    try:
        sourceOwner = source.users.get(orig_item.owner)
        targetOwner = target.users.get(target_item.owner)
        
        if orig_item.ownerFolder==None:
            print ("Item is in the Root")
        else:
            fld = source.content.folders.get(folder=orig_item.ownerFolder, owner=orig_item.owner)
            print ("Moving to folder {}".format(fld.name))
            newfolder = target.content.folders.create(fld.name, owner= targetOwner, exist_ok=True)

            target_item.move(newfolder)
            
    except Exception as copy_ex:
        print("\tError in update folder: " + target_item.title)
        print("\t" + str(copy_ex))
        print (str(sys.exc_info()) + "\n")
        print(traceback.format_tb(sys.exc_info()[2])[0] + "\n")
        logging.error(copy_ex)
        return None


def updateKeyword(orig_item, target_item):
    try:
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
    except Exception as copy_ex:
        print("\tError in update owner: " + target_item.title)
        print("\t" + str(copy_ex))
        print (str(sys.exc_info()) + "\n")
        print(traceback.format_tb(sys.exc_info()[2])[0] + "\n")
        logging.error(copy_ex)
        return None


def updateSharing(orig_item, target_item):
    
    try:
        #Set sharing (privacy) information
        print ("  Set sharing for item {}".format(target_item.title))
        logging.info("Set sharing for item {}".format(target_item.title))
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
                print ("  Cannot identify new group for {}".format(group))
    	
    except Exception as copy_ex:
        print("\tError in update Sharing " + target_item.title)
        print("\t" + str(copy_ex))
        print (str(sys.exc_info()) + "\n")
        print(traceback.format_tb(sys.exc_info()[2])[0] + "\n")
        logging.error(copy_ex)
        return None

def updateCategories(orig_item, target_item):
    try:
        #might need to check if categories keyword exists if org has no categories
        print ("  Set categories for item")
        categories = orig_item.categories
        itemlist = [{target_item.id:{"categories": categories}}]
        if len(categories) > 0:
            target.content.categories.assign_to_items(items=itemlist)
    except Exception as copy_ex:
        print("\tError in update Categories " + target_item.title)
        print("\t" + str(copy_ex))
        print (str(sys.exc_info()) + "\n")
        print(traceback.format_tb(sys.exc_info()[2])[0] + "\n")
        logging.error(copy_ex)
        return None

def updateProperties(orig_item, target_item):
    target_props = {
        "description": orig_item.description,
        "tags": orig_item.tags,
        "snippet": orig_item.snippet
    }
    print("   Updating properties...")
    target_item.update(target_props)

def updateThumbnail(orig_item, target_item):
    tempdir = tempfile.TemporaryDirectory()
    thumbNail = orig_item.download_thumbnail(tempdir)
    if thumbNail:
        print ("  Uploading thumbnail")
        target_item.update(thumbnail=thumbNail)
        os.remove(thumbNail)
    os.removedirs(tempdir)

#MAIN LOOP
for index, target_row in newitemsDF.iterrows():
    # if not target_row["Title"] == "Depth_Groundwater_feet":
    #     continue
        
    orig_item = source.content.get(target_row["SourceID"])
    target_item = target.content.get(target_row["TargetID"])

    if not orig_item:
        print ("Source Item {} : {} not found!!".format(target_row["Title"], target_row["SourceID"]))
        logging.error("Source Item {} : {} not found!!".format(target_row["Title"], target_row["SourceID"]))
        continue
    if not target_item:
        print ("Target Item {} not found!!".format(target_row["Title"], target_row["TargetID"]))
        logging.error("Target Item {} not found!!".format(target_row["Title"], target_row["TargetID"]))
        continue

    print("Setting properties for {}: Type: {}  for {}".format(orig_item.title, orig_item.type, orig_item.owner))
    logging.info("Setting properties for {}: Type: {}  for {}".format(orig_item.title, orig_item.type, orig_item.owner))
    
    updateOwner(orig_item, target_item)
    updateFolder(orig_item, target_item)
    updateKeyword(orig_item, target_item)
    updateSharing(orig_item, target_item)
    updateCategories(orig_item, target_item)
    updateProperties(orig_item, target_item)
    updateThumbnail(orig_item, target_item)




