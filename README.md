# mbclient
Microblog client

## Installation from the zip file

* Unpack the zip file into a location of your choice
* Edit the db_root.py file to set the location you wish the database to be placed - the directory must already exist
* Execute the database setup script with: python db_setup.py
* Start the client with: python mb_client.py

## Database Structure

### system table

* sys_update - Timestamp of the last system-wide update
* news_update - Timestamp of the last news update
* qso_update - Timestamp of the last qso update
* blogs_update - Timestamp of the last blogs update
