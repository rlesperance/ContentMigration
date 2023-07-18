## General workflow 
For migrating users/groups/roles/content from one ArcGIS Online organization to another

This is the order these scripts should be run, and generally what they do.  See the individual items for more detail. 
Examples of the input/output XLS documents are included in this repository.  Any of these can be created on the fly if the routines creating them don't need to be run (for instance if you've already created the users on the target). 

1. COPYROLES

Looks for and copies any non-stock roles the admins have created in the source org.  This should be done first so the roles can be applied when migrating users. 

2. COPYUSERS

Copies all users from source org to target org.  This is a true clone, so in ArcGIS Online there cannot be users in two different organizations with the same usersname.  
Output from this script is an XLS sheet that maps the old username to the new username to be used in subsequent scripts for assigning content and group ownership and membership. 
     
     OUTPUT: User_Mapping.XLSX

3. COPYGROUPS

Copies all non-stock groups from source organization to target organization and assigns ownership to mapped user and adds mapped user members.
     
     INPUT:  User_Mapping.XLSX
     OUTPUT: Groups_Mapping.XLSX

4. GENERATEPREP

Generates a list of content from the source site and what groups each items is shared to.  The output is an XLS document listing the source item's ID, ownership and groups.  
This can be input into subsequent scripts in total or as a subset.  Save this output as a copy and then remove lines you don't want as input in the following scripts. 
     
     OUTPUT: Item_Prep.XLSX

5. COPYITEMS

Main cloning component.  Loops through the Item_Prep.XLSX document and uses the ArcGIS Python API clone_items() method to copy.  Hosted feature layers will be copied over entirely.  Referenced map services will be created as items referencing the original data source.  Maps and apps will search the target for layers/maps already cloned, but copy the dependencies if not already cloned.  
Output mapping document has the source and target IDs
     
     INTPUT:  User_Mapping.XLSX, Group_Mapping.XLSX, Item_Prep.XLSX
     OUTPUT:  Item_Mapping.XLSX

6. POSTPROCESSLAYERS

This script accepts all the previous documents typs as input and loops through the final mapping document setting ownership, sharing, categories, and typeKeyword if necessary.   This can be run on any item even if it was created manually.  
If it went through the entire process, it may not need the ownership or keyword sections of the code, however there's no harm in them processing again.  
If the user created the content manually, setting the keyword allows subsequent clones to see that as a cloned object.  For instance if you manually create a feature layer on the target that existed on the source and was used in a web map, get the original source ID and the new target ID of the layer, build an item mapping XLS in the sample format and manually enter the ids.  Run that through this process and it will update the ownership and keyword of the new item (since you need the original prep document, that item should be in there and the group sharing and categories will update as well).  Then when the web map is cloned, it will see the type keyword indicating this is the same layer it was using on the source side and point to the new target layer instead. 
