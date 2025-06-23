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
#If run in Online notebook, set base path to:  "/arcgis/home/CopyItems_log.txt"
logging.basicConfig(filename = os.path.join(basePath,"CopyItems_log.txt"), level=logging.INFO)
now = datetime.now()
logging.info("{}  Begin item migration".format(str(now)))

itemsXLS = os.path.join(basePath,  "Item_Prepxlsx")
itemMapXLS = os.path.join(basePath,  "Item_Mapping.xlsx")

source = GIS(source_portal_url, source_admin_username, source_password, expiration = 9999)  #, verify_cert = False
logging.info("Connected to source portal "+source_portal_url+" as "+source_admin_username)

target = GIS(target_portal_url, target_admin_username, target_password, expiration = 9999)
logging.info("Connected to target portal "+target_portal_url+" as "+target_admin_username)

#Get Item Prep document
itemsDF = pd.read_excel(itemsXLS,  engine='openpyxl')

def copy_item(target, source_item, copydata=True):

    try:
        #Get actual item
        item = source.content.get(source_item["itemID"])
        
        # CLONE THE ITEM to the target portal, assign owner and folder
        cloned_items = target.content.clone_items(items=[item], copy_data=copydata, preserve_item_id=True)  #retain ID not valid for ArcGIS Online
        if not cloned_items or len(cloned_items) < 1:
            print ("Item {} did not clone!!!".format(item.title))
            return None
        cloned_item = cloned_items[0]
    except Exception as copy_ex:
        print("\tError in copying " + source_item['title'])
        print("\t" + str(copy_ex))
        print (str(sys.exc_info()) + "\n")
        print(traceback.format_tb(sys.exc_info()[2])[0] + "\n")
        logging.error(copy_ex)
        return str(copy_ex)
    
    return cloned_item

#MAIN LOOP
source_target_itemId_map = []  #Title, SourceID, Type, TargetID
for index, source_item in itemsDF.iterrows():
#for source_item in source_items_by_id:

    # if  not source_item["title"] == "Comp_Plan_Edit":
    #     continue
    source_target_dict = {}
    source_target_dict["Title"] = source_item["title"]
    source_target_dict["SourceID"] = source_item["itemID"]
    source_target_dict["Type"] = source_item["type"]
    source_target_dict["Owner"] = source_item["owner"]
    source_target_dict["TargetID"] = ""
    
    #check if already there by typeKeyword
    exists = False
    for x in target.content.search(source_item["title"]):
        sourcekey = [s for s in x.typeKeywords if 'source-' in s]
        if not sourcekey:
            continue
        if source_item["itemID"] == sourcekey[0].partition("-")[2]:
            print ("{}: {} is already in target".format(source_item["title"], source_item["type"]))
            logging.info("{}: {} is already in target".format(source_item["title"], source_item["type"]))
            source_target_dict["TargetID"] = x.id
            exists = True
    if not exists and not source_item["type"] in ['Operation View', 'Application', 'Notebook', 'Web Experience']:
        print("Copying {}: Type: {}  for {}".format(source_item["title"], source_item["type"], source_item["owner"]))
        logging.info("Copying {}: Type: {}  for {}".format(source_item["title"], source_item["type"], source_item["owner"]))
        target_item = copy_item(target, source_item)  #CALL TO COPY FUNCTION
        try:
            if target_item:
                if type(target_item) == str:
                    source_target_dict["TargetID"] = target_item
                else:
                    source_target_dict["TargetID"] = target_item.id
        except Exception as copy_ex:
            source_target_dict["TargetID"] = "Failed To Copy"
            print("\t" + str(copy_ex))
            print (str(sys.exc_info()) + "\n")
            logging.error(copy_ex)
        
    source_target_itemId_map.append(source_target_dict)
    logging.info(source_target_dict)

df = pd.DataFrame.from_dict(source_target_itemId_map)
with pd.ExcelWriter(itemMapXLS, engine='openpyxl') as writer:
    df.to_excel(writer)

logging.info("Mapping file: {}".format(itemsXLS))

