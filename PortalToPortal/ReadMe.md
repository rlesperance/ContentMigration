General repository of scripts related to migrating content from Portal to Portal.  Could be ArcGIS Enterprise or ArcGIS Online.
One caveat to doing this with Enterprise is that the CLONE_ITEMS() method on content managers does not carry referenced services to a new Portal.  So if you have a map image service (with or without a feature layer) it reconstitutes each separately.  

Follow the steps below to use the notebooks.  It's suggested that the scripts be used as notebooks run in Jupyter Notebook on a computer with the arcgis libraries (Pro or Server).   
You can use it in ArcGIS Online or Pro, but the use of XLSX documents to guide the process makes using Online difficult.  

<b>1. COPYROLES</b>

Looks for and copies any non-stock roles the admins have created in the source org.  This should be done first so the roles can be applied when migrating users. 

<b>2. COPYUSERS</b>

Copies all users from source org to target org.  The users can be either built-in ArcGIS user store or SSO using SAML.   The usernames can be the same as in the source Portal, but keep in mind that SSO users must adhere to the return username from the IDP.  
NOTE:   Keep in mind that if you are using this code to move users to an ArcGIS Online organization, users in that SAAS environment cannot be duplicated, so ArcGIS Online org to org migrations will not allow same usernames.
Input for this script is an XLS sheet that maps the old username to the new username.  Use the template included with these scripts to fill in the details, and note which users are SSO and which are built in ArcGIS for the target.
The XLSX will also be used in subsequent scripts for assigning content and group ownership and membership. 

     INPUT: User_Mapping.XLSX

<b>3. COPYGROUPS</b>

Copies all non-stock groups from source organization to target organization and assigns ownership to mapped user and adds mapped user members.  Code takes into account if the group is shared edit, but does not by default bring over distributed collaboration groups.  This code does not re-create those collaborations, and so users should consider re-building that environment manually. 
     
     INPUT:  User_Mapping.XLSX
     OUTPUT: Groups_Mapping.XLSX

<b>4. GENERATEPREP</b>

Optional.  Generates a list of content from the source site and what groups each items is shared to.  The output is an XLS document listing the source item's ID, ownership and type.  
This can be input into subsequent scripts in total or as a subset.  Save this output as a copy and then remove lines you don't want as input in the following scripts. 
The prep spreadsheet can also be built manually from an inventory taken and filtered for priority datasets, so this step is optional.
     
     OUTPUT: Item_Prep.XLSX

<b>5. COPYITEMS</b>

Main cloning component.  Loops through the Item_Prep.XLSX document and uses the ArcGIS Python API clone_items() method to copy.  Hosted feature layers will be copied over entirely.  Maps and apps will search the target for layers/maps already cloned, but copy the dependencies if not already cloned.  
Output mapping document has the source and target IDs
     
     INTPUT:  Item_Prep.XLSX
     OUTPUT:  Item_Mapping.XLSX

It is suggested that this step be done in separate batches depending on the item types being migrated.  Do the hosted feature layers first, and make sure your referenced services are rebuilt and run through the post processing first (to update the source keywords), then do the maps and applications.

<b>6. POSTPROCESSLAYERS</b>

This script loops through the final mapping document setting ownership, owner folder, sharing, categories, and typeKeyword if necessary.   This can be run on any item even if it was created manually and you've added the new ID to a mapping XLSX.  

INTPUT:  User_Mapping.XLSX, Group_Mapping.XLSX, Item_Mapping.XLSX

If the user created the content manually, setting the keyword allows subsequent clones to see that as a cloned object.  For instance if you manually create a feature layer on the target that existed on the source and was used in a web map, get the original source ID and the new target ID of the layer, build an item mapping XLS in the sample format and manually enter the ids.  Run that through this process and it will update the ownership and keyword of the new item.  Then when the web map is cloned, it will see the type keyword indicating this is the same layer it was using on the source side and point to the new target layer instead. 
