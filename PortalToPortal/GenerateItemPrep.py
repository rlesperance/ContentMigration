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

basePath = r"C:\workspace"
logging.basicConfig(filename = os.path.join(basePath, "GeneratePrep_log.txt"), level=logging.INFO)
now = datetime.now()
logging.info("{}  Begin item prep".format(str(now)))

itemsXLS = os.path.join(basePath,  "Item_Prep.xlsx")

# Instantiate Portal connections - use verify_cert = False to use self signed SSL
source = GIS(source_portal_url, source_admin_username, source_password, verify_cert = False, expiration = 9999)
logging.info("Connected to source portal "+source_portal_url+" as "+source_admin_username)

source_users = source.users.search('!esri_ & !esri_livingatlas',max_users=99999)


source_items_by_id = []
for user in source_users:
    #if not user.username == "NameYouWantToTest":
        #continue
    num_items = 0
    num_folders = 0
    print("Collecting item ids for {}".format(user.username), end="\t\t")
    user_content = source.content.search(query="owner:{}".format(user.username), max_items=1000)
    
    # Get item ids from root folder first
    for item in user_content:
        num_items += 1
        source_item = {}
        source_item["itemID"] = item.id
        source_item["title"] = item.title 
        source_item["type"] = item.type 
        source_item["owner"] = item.owner
        source_items_by_id.append(source_item)
    
    print("Number of folders {} # Number of items {}".format(str(num_folders), str(num_items)))
    logging.info("Number of folders {} # Number of items {}".format(str(num_folders), str(num_items)))


sourceDF = pd.DataFrame.from_dict(source_items_by_id)

with pd.ExcelWriter(itemsXLS, engine='openpyxl') as writer:
    sourceDF.to_excel(writer)
    
logging.info("Prep file created:  {}".format(itemsXLS))



