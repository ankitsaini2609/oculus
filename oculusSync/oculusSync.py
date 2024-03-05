import argparse
import os
import pandas as pd
import json
import sys
from helper.logger import get_logger
from helper.dbConnector import initialiseDB
import hashlib

logger = get_logger(__name__)

# field required for confluence: space,page,tags,offender,line,uniqueHash,leakURL,fixedOn,createdBy,lastUpdatedBy,frequentlyUpdatedBy,version
# field required for github: line,lineNumber,offender,offenderEntropy,commit,repo,repoURL,leakURL,rule,commitMessage,author,email,file,date,dateOfinsertion,tags,branchName,prNumber,uniqueHash,fixedOn

class oculusSync:
    def __init__(self, sourceType, sourceConnectionString, destinationType, destinationConnectionString, platformIdentifier):
        self.sourceType = sourceType.strip()
        if self.sourceType != 'mongodb':
            self.destinationConnectionString = destinationConnectionString.strip()
        self.sourceConnectionString = sourceConnectionString.strip()
        self.destinationType = destinationType.strip()
        if self.destinationType != 'mongodb':
            self.destinationConnectionString = destinationConnectionString.strip()
        self.platformIdentifier = platformIdentifier.strip()

        if not (self.sourceType == 'mongodb' or self.destinationType == 'mongodb'):
            sys.exit('The combination of sourceType and destinationType is not supported.')
        
        if self.sourceType == 'mongodb':
            self.sourceDatabaseName = os.getenv('sourceDatabaseName')
            self.sourceConnectionString = os.getenv('sourceConnectionString')
            self.SOURCE_COLLECTION = os.getenv('SOURCE_COLLECTION')
            self.sourcedb = initialiseDB(self.sourceDatabaseName, self.sourceConnectionString)
        
        if self.destinationType == 'mongodb':
            self.destinationDatabaseName = os.getenv('destinationDatabaseName')
            self.destinationConnectionString = os.getenv('destinationConnectionString')
            self.DESTINATION_COLLECTION = os.getenv('DESTINATION_COLLECTION')
            self.destinationdb = initialiseDB(self.destinationDatabaseName, self.destinationConnectionString)
            with open('fieldMapping.json', 'r') as file:
                self.fieldMapping = json.load(file)

        if self.sourceConnectionString == self.destinationConnectionString:
            if self.SOURCE_COLLECTION == self.DESTINATION_COLLECTION:
                sys.exit("Can't read and write in the same collection")
                
    
    def transformDocument(self, document):
        leak = dict()
        if self.platformIdentifier == 'confluence':
            leak = {
                "space": str(document[self.fieldMapping['space']]),
                "page": str(document[self.fieldMapping['page']]), 
                "tags": str(document[self.fieldMapping['tags']]), 
                "offender": str(document[self.fieldMapping['offender']]), 
                "uniqueHash": hashlib.sha256((str(document[self.fieldMapping['space']]) + str(document[self.fieldMapping['page']]) + str(document[self.fieldMapping['tags']]) + str(document[self.fieldMapping['offender']])).encode()).hexdigest(), 
                "leakURL": str(document[self.fieldMapping['leakURL']]),
                "createdBy": str(document[self.fieldMapping['createdBy']]),
                "lastUpdatedBy": str(document[self.fieldMapping['lastUpdatedBy']]),
                "frequentlyUpdatedBy": str(document[self.fieldMapping['frequentlyUpdatedBy']]),
                "version": str(document[self.fieldMapping['version']]),
                "fixedOn": str(document[self.fieldMapping['fixedOn']]),
                "line": str(document[self.fieldMapping['line']])
            }
        elif self.platformIdentifier == 'github':
            leak = {
                "line": str(document[self.fieldMapping['line']]),
                "lineNumber": int(document[self.fieldMapping['lineNumber']]),
                "offender": str(document[self.fieldMapping['offender']]),
                "offenderEntropy": int(document[self.fieldMapping['offenderEntropy']]),
                "commit": str(document[self.fieldMapping['commit']]),
                "repo": str(document[self.fieldMapping['repo']]),
                "repoURL": document[self.fieldMapping['repoURL']],
                "leakURL": document[self.fieldMapping['leakURL']],
                "rule": str(document[self.fieldMapping['rule']]),
                "commitMessage": str(document[self.fieldMapping['commitMessage']]),
                "author": str(document[self.fieldMapping['author']]),
                "email": document[self.fieldMapping['email']],
                "file": str(document[self.fieldMapping['file']]),
                "date": str(document[self.fieldMapping['date']]),
                "dateOfinsertion": str(document[self.fieldMapping['dateOfinsertion']]),
                "tags": str(document[self.fieldMapping['tags']]),
                "branchName": str(document[self.fieldMapping['branchName']]),
                "prNumber": int(document[self.fieldMapping['prNumber']]),
                "uniqueHash": hashlib.sha256((str(document[self.fieldMapping['offender']]) + str(document[self.fieldMapping['commit']]) + str(document[self.fieldMapping['file']])).encode()).hexdigest(),
                "fixedOn": str(document[self.fieldMapping['fixedOn']])
            }
        else:
            sys.exit('platform type not supported')
        return leak


    def writeDB(self, sourceMongoDocuments):
        try:
            databaseObject = self.destinationdb.dbObject.get_database(self.destinationdb.databaseName).get_collection(self.DESTINATION_COLLECTION)
            for document in sourceMongoDocuments:
                transformedDocument = self.transformDocument(document)
                databaseObject.insert_one(transformedDocument)
        except Exception as e:
            logger.error('Cannot write into db getting error: {0}'.format(e))

    
    def readDB(self):
        sourceMongoDocuments = list()
        try:
            for document in self.sourcedb.dbObject.get_database(self.sourcedb.databaseName).get_collection(self.SOURCE_COLLECTION).find({}, {"_id": 0}):
                    sourceMongoDocuments.append(document)
        except Exception as e:
            logger.error('Cannot read the source collection getting error: {0}'.format(e))
        return sourceMongoDocuments

    
    def readJson(self, jsonInputFilePath):
        jsondata = []
        try:
            with open(jsonInputFilePath, 'r') as file:
                data = json.load(file)
            logger.info('The JSON file has been read.')
        except Exception as e:
            logger.error('Unable to read {0} getting error: {1}'.format(jsonInputFilePath, e))
        if type(data) == dict:
            jsondata.append(data)
        else:
            jsondata = data
        
        return jsondata
    

    def writeJson(self, jsonOutputFilePath, jsondata):
        try:
            with open(jsonOutputFilePath, 'w') as file:
                json.dump(jsondata, file)
            logger.info('The JSON data has been written')
        except Exception as e:
            logger.error('Unable to write on {0} getting error: {1}'.format(jsonOutputFilePath, e))

    
    def readExcel(self, excelInputFilePath):
        exceldata = []
        try:
            df = pd.read_excel(excelInputFilePath)
            exceldata = df.to_dict(orient='records')
            logger.info('The Excel file has been read.')
        except Exception as e:
            logger.error('Unable to read {0} getting error: {1}'.format(excelInputFilePath, e))
        
        return exceldata


    def writeExcel(self, excelOutputFilePath, exceldata):
        try:
            df = pd.DataFrame(exceldata)
            df.to_excel(excelOutputFilePath, index=False)
            logger.info('The Excel data has been written')
        except Exception as e:
            logger.error('Unable to read {0} getting error: {1}'.format(excelOutputFilePath, e))
    

    def startSync(self):
        sourceData = list()
        if self.sourceType == 'json' and self.destinationType == 'mongodb':
            sourceData = self.readJson(self.sourceConnectionString)
            self.writeDB(sourceData)
        elif self.sourceType == 'xlsx' and self.destinationType == 'mongodb':
            sourceData = self.readExcel(self.sourceConnectionString)
            self.writeDB(sourceData)
        elif self.sourceType == 'mongodb' and self.destinationType == 'mongodb':
            sourceData = self.readDB()
            self.writeDB(sourceData)
        elif self.sourceType == 'mongodb' and self.destinationType == 'json':
            sourceData = self.readDB()
            self.writeJson(self.destinationConnectionString, sourceData)
        elif self.sourceType == 'mongodb' and self.destinationType == 'xlsx':
            sourceData = self.readDB()
            self.writeExcel(self.destinationConnectionString, sourceData)
        else:
            logger.error("Sync between sourceType and destinationType not supported")


# Always keep the place where you want to write as a destination and from where you want to read as a source
if __name__ == "__main__":
    parser = argparse.ArgumentParser(usage='%(prog)s -st json/xlsx/mongodb -scstr in_path -dt json/xlsx/mongodb -dcstr out_path -pid github/confluence')
    parser.add_argument('-st', '--sourceType', default='json', help='sourceType file/db.')
    parser.add_argument('-scstr', '--sourceConnectionString', default='in.json', help='pass list of json or excel file. use env variables in case of db')
    parser.add_argument('-dt', '--destinationType', default='json', help='format of exported findings.')
    parser.add_argument('-dcstr', '--destinationConnectionString', default='out.json', help='path of the file where you want to export findings to. use env variables in case of db')
    parser.add_argument('-pid', '--platformIdentifier', default='github', help='for which platform you are doing github/confluence')
    args = parser.parse_args()
    sourceType = str(args.sourceType).lower()
    sourceConnectionString = str(args.sourceConnectionString).lower()
    destinationType = str(args.destinationType).lower()
    destinationConnectionString = str(args.destinationConnectionString).lower()
    platformIdentifier = str(args.platformIdentifier).lower()
    oce = oculusSync(sourceType, sourceConnectionString, destinationType, destinationConnectionString, platformIdentifier)
    oce.startSync()