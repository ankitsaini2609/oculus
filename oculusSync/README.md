# oculusSync
It will be helpful during the migration between different credential management tool. It serves the following purpose.
- If your existing credentials management system exports the findings in the json/excel, you can easily feed both the file type to the oculusSync along with mongoDB details it will update the database accordingly.
- You can export the findings of your mongoDB to excel/json.
- You can sync between two mongoDB database as well.

**Note** Make sure database schema is same. currently oculusSync is only doing extraction and loading of the data without any transformation.

## How to run
```
➜ python3 oculusSync.py -h
usage: oculusSync.py -st json/xlsx/mongodb -scstr in_path -dt json/xlsx/mongodb -dcstr out_path -pid github/confluence

options:
  -h, --help            show this help message and exit
  -st SOURCETYPE, --sourceType SOURCETYPE
                        sourceType file/db.
  -scstr SOURCECONNECTIONSTRING, --sourceConnectionString SOURCECONNECTIONSTRING
                        pass list of json or excel file. use env variables in case of db
  -dt DESTINATIONTYPE, --destinationType DESTINATIONTYPE
                        format of exported findings.
  -dcstr DESTINATIONCONNECTIONSTRING, --destinationConnectionString DESTINATIONCONNECTIONSTRING
                        path of the file where you want to export findings to. use env variables in case of db
  -pid PLATFORMIDENTIFIER, --platformIdentifier PLATFORMIDENTIFIER
                        for which platform you are doing github/confluence
```
**Note**:
- Supported sourceType and destinationType are json/xlsx/mongodb.
- In case you are choosing sourceType or destinationType as mongodb you can ignore -scstr and -dcstr flag.
- Always set the destination location where you want to write your data, meaning It will always read from source parameter and will write in the destination parameter.
- In case you are using destination as mongodb, set the following environment variable:
    - destinationDatabaseName = 'databaseName'
    - destinationConnectionString = 'mongodbConnectionString'
    - DESTINATION_COLLECTION='mongodbCollectionName'
- In case you are using source as mongodb, set the following environment variable:
    - sourceDatabaseName='databaseName'
    - sourceConnectionString='mongodbConnectionString'
    - SOURCE_COLLECTION='mongodbCollectionName' 
- fieldMapping.json file is used to map the fields (source -> destination). Source will always be fixed change the values on right side as per the fields present in your current credentials detection systems.
- platformIdentifier supports confluence/github for now.

## Future Scope
- Can be extended to other databases and file types.
- Can be extended to do real time database sync.

