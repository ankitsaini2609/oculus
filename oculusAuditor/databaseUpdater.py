import subprocess
import json
from datetime import datetime
import argparse
import os
import pandas as pd
import re
import boto3
import requests
from helper.logger import get_logger
import helper.confluenceConnector as cc
import helper.dbConnector as gh

logger = get_logger(__name__)


class databaseUpdater():
    def __init__(self, githubFlag, confluenceFlag, uploadToS3):
        logger.info('Initialising databaseUpdater')
        self.githubFlag = str(githubFlag).lower()
        self.confluenceFlag = str(confluenceFlag).lower()
        self.uploadToS3 = str(uploadToS3).lower()
        if self.githubFlag == 'true':
            self.ghdb = gh.initialiseDB(os.getenv('databaseName'), os.getenv('connectionString'))
            self.githubCollectionName = os.getenv('GITHUB_COLLECTION_NAME')
            self.githubMaskedCollectionName = os.getenv('GITHUB_MASKED_COLLECTION_NAME')
        if self.confluenceFlag == 'true':
            self.ccdb = cc.initialiseDB(os.getenv('databaseName'), os.getenv('connectionString'))
            self.confluenceCollection = os.getenv('CONFLUENCE_COLLECTION')
        if self.uploadToS3 == 'true':
            self.BUCKET_NAME = os.getenv('BUCKET_NAME')
        logger.info('databaseUpdater intialised.')


    def upload_s3(self, filename, destFilename):
        try:
            s3 = boto3.client('s3')
            with open(filename, 'rb') as data:
                s3.upload_fileobj(data, self.BUCKET_NAME, destFilename)
            logger.info('successfully uploaded to bucket')
            if os.path.exists(filename):
                os.remove(filename)
        except Exception as e:
            logger.error('unable to put data in bucket: {0}'.format(e))
    

    def create_excel_and_upload(self, MongoDocuments, bucketPath, platformIdentifier):
        try:
            df  = pd.DataFrame()
            df = pd.DataFrame.from_dict(MongoDocuments)
            filename = 'combinedReport' + datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.xlsx'
            if platformIdentifier == 'github':
                col = ['line', 'lineNumber', 'offender', 'commit', 'repoURL', 'author', 'file', 'branchName', 'leakURL', 'dateOfinsertion', 'tags']
            elif platformIdentifier == 'confluence':
                col = ['space', 'page', 'tags', 'offender', 'createdBy', 'lastUpdatedBy', 'frequentlyUpdatedBy', 'leakURL']
            else:
                logger.error('File Cannot be uploaded to the bucket. {0} not supported.'.format(platformIdentifier))
                return
            df.to_excel(filename, header=True, engine='xlsxwriter', columns=col)
        except Exception as e:
            logger.error('Unable to create excel getting error: {0}'.format(e))
        destFilename = bucketPath+filename
        self.upload_s3(filename, destFilename)
    

    def update_db(self, document, platformIdentifier):
        try:
            now = datetime.now()
            dateString = now.strftime("%d/%m/%Y %H:%M:%S")
            if platformIdentifier == 'github':
                gh.scanResults.objects(uniqueHash=document.get('uniqueHash')).update(set__fixedOn=dateString)
            elif platformIdentifier == 'confluence':
                cc.confluenceResults.objects(uniqueHash=document.get('uniqueHash')).update(set__fixedOn=dateString)
            else:
                logger.info('Unable to update documents having {0} uniqueHash of {1} collection'.format(document.get('uniqueHash'), platformIdentifier))
        except Exception as e:
            logger.info('Unable to update documents having {0} uniqueHash of {1} collection. Getting exception: {2}'.format(document.get('uniqueHash'), platformIdentifier, e))


    def updateDatabase(self, MongoDocuments, platformIdentifier):
        try:
            VERITAS_URL = os.getenv('VERITAS_URL')
            for document in MongoDocuments:
                if 'jwt' in str(document.get('tags')).lower():
                    jwtRegex = """\\b(ey[a-zA-Z0-9]{17,}\\.ey[a-zA-Z0-9\\/\\\\_-]{17,}\\.(?:[a-zA-Z0-9\\/\\\\_-]{10,}={0,2})?)\\b"""
                    text = document.get('offender')
                    x = re.search(re.compile(jwtRegex), text)
                    if x is not None:
                        tag = 'jwt'
                        data = {"tag": tag, "key": x.group()}
                        try:
                            res = requests.post(VERITAS_URL, json=data)
                            if res.json()['status'] == 'False':
                                self.update_db(document, platformIdentifier)
                        except Exception as e:
                            logger.error(e)
                    else:
                        self.update_db(document, platformIdentifier)
                elif 'npm' in str(document.get('tags')).lower():
                    npmRegex = """(?i)\\b(npm_[a-z0-9]{36})\\b"""
                    text = document.get('offender')
                    x = re.search(re.compile(npmRegex), text)
                    if x is not None:
                        tag = 'npm'
                        data = {"tag": tag, "key": x.group()}
                        try:
                            res = requests.post(VERITAS_URL, json=data)
                            if res.json()['status'] == 'False':
                                self.update_db(document, platformIdentifier)
                        except Exception as e:
                            logger.error(e)
                    else:
                        self.update_db(document, platformIdentifier)
                elif 'google' in str(document.get('tags')).lower():
                    text = document.get('offender')
                    tag = 'google'
                    data = {"tag": tag, "key": text}
                    try:
                        res = requests.post(VERITAS_URL, json=data)
                        if res.json()['status'] == 'False':
                            self.update_db(document, platformIdentifier)
                    except Exception as e:
                        logger.error(e)
                elif 'github' in str(document.get('tags')).lower():
                    text = document.get('offender')
                    tag = 'github'
                    data = {"tag": tag, "key": text}
                    try:
                        res = requests.post(VERITAS_URL, json=data)
                        if res.json()['status'] == 'False':
                            self.update_db(document, platformIdentifier)
                    except Exception as e:
                        logger.error(e)
                elif 'slack' in str(document.get('tags')).lower():
                    flag = False
                    regexDict = {
                        "SLACK_WEBHOOKS": """(https?://)?hooks.slack.com/(services|workflows)/[A-Za-z0-9+/]{43,46}""",
                        "SLACK_BOT_TOKEN" : """(xoxb-[0-9]{10,13}\\-[0-9]{10,13}[a-zA-Z0-9-]*)""",
                        "SLACK_APP_TOKEN" : """(?i)(xapp-\\d-[A-Z0-9]+-\\d+-[a-z0-9]+)""",
                        "SLACK_CONFIG_ACCESS_TOKEN" : """(?i)(xoxe.xox[bp]-\\d-[A-Z0-9]{163,166})""",
                        "SLACK_CONFIG_REFRESH_TOKEN": """(?i)(xoxe-\\d-[A-Z0-9]{146})""",
                        "SLACK_LEGACY_BOT_TOKEN": """(xoxb-[0-9]{8,14}\\-[a-zA-Z0-9]{18,26})""",
                        "SLACK_LEGACY_TOKEN": """(xox[os]-\\d+-\\d+-\\d+-[a-fA-F\\d]+)""",
                        "SLACK_LEGACY_WORKSPACE_TOKEN": """(xox[ar]-(?:\\d-)?[0-9a-zA-Z]{8,48})""",
                        "SLACK_USER_TOKEN": """(xox[pe](?:-[0-9]{10,13}){3}-[a-zA-Z0-9-]{28,34})"""
                    }
                    text = document.get('offender')
                    for regex in regexDict.keys():
                        x = re.search(re.compile(regexDict[regex]), text)
                        if x is not None:
                            flag = True
                            try:
                                if regex == 'SLACK_BOT_TOKEN' or regex == 'SLACK_USER_TOKEN' or regex == 'SLACK_LEGACY_BOT_TOKEN':
                                    tag = 'slack_token'
                                elif regex == 'SLACK_WEBHOOKS':
                                    tag = 'slack_webhook'
                                else:
                                    tag = 'unknown'
                                data = {"tag": tag, "key": x.group()}
                                res = requests.post(VERITAS_URL, json=data)
                                if res.json()['status'] == 'False':
                                    self.update_db(document, platformIdentifier)
                            except Exception as e:
                                logger.error(e)
                    if flag == False:
                        self.update_db(document, platformIdentifier)
                else:
                    continue
        except Exception as e:
            logger.error('Not able to update {0} collection'.format(platformIdentifier))


    def main(self):
        if self.githubFlag == 'true':
            githubMongoDocuments = list() # contains entries which are not fixed
            githubMaskedMongoDocuments = list() # contains entries which are the part of masked db and not fixed
            count_audit = 0
            count_scan = 0
            for document in self.ghdb.dbObject.get_database(self.ghdb.databaseName).get_collection(self.githubCollectionName).find():
                fixedOn = document.get('fixedOn')
                if len(fixedOn) == 0:
                    githubMongoDocuments.append(document)
                    if int(document.get('prNumber')) == 0:
                        count_audit += 1
                    else:
                        count_scan += 1
            self.updateDatabase(githubMongoDocuments, 'github')

            for document in self.ghdb.dbObject.get_database(self.ghdb.databaseName).get_collection(self.githubMaskedCollectionName).find():
                githubMaskedMongoDocuments.append(document)
    
            for document in githubMaskedMongoDocuments:
                new_document = self.ghdb.dbObject.get_database(self.ghdb.databaseName).get_collection(self.githubCollectionName).find_one({'uniqueHash': document.get('uniqueHash')})
                if new_document is None:
                    fixedOn = 'None'
                else:
                    fixedOn = new_document.get('fixedOn')
                if len(fixedOn) > 0:
                    try:
                        self.ghdb.dbObject.get_database(self.ghdb.databaseName).get_collection(self.githubMaskedCollectionName).delete_one({'uniqueHash': document.get('uniqueHash')})
                    except Exception as e:
                        print("Unable to delete data from masked db {0}".format(e))
            
            if self.uploadToS3 == 'true':
                self.create_excel_and_upload(githubMongoDocuments, "github/", 'github')
            logger.info('Current Count for Github Auditor: {0}'.format(count_audit))
            logger.info('Current Count for Github Scans: {0}'.format(count_scan))
            
        if self.confluenceFlag == 'true':
            confluenceMongoDocuments = list()
            count_confluence = 0
            for document in self.ccdb.dbObject.get_database(self.ccdb.databaseName).get_collection(self.confluenceCollection).find():
                fixedOn = document.get('fixedOn')
                if len(fixedOn) == 0:
                    confluenceMongoDocuments.append(document)
                    count_confluence += 1
            self.updateDatabase(confluenceMongoDocuments, 'confluence')
            if self.uploadToS3 == 'true':
                self.create_excel_and_upload(confluenceMongoDocuments, "confluence/", 'confluence')
            logger.info('Current Count for Confluence Audit: {0}'.format(count_confluence))

    
if __name__ == "__main__":
    # argument parsing
    parser = argparse.ArgumentParser(usage='%(prog)s -gh true/false [-c true/false] [-us3 true/false]')
    parser.add_argument('-c', '--confluence', default='false', help='whether you want to update the confluence db or not.')
    parser.add_argument('-gh', '--github', default='false', help='whether you want to update the github db or not.')
    parser.add_argument('-us3', '--uploadToS3', default='false', help='whether you want to upload the results to the s3 bucket or not.')
    args = parser.parse_args()
    githubFlag = args.github
    confluenceFlag = args.confluence
    uploadToS3 = args.uploadToS3
    dbu = databaseUpdater(githubFlag, confluenceFlag, uploadToS3)
    dbu.main()