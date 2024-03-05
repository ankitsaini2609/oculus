import os
from github import *
import string
import subprocess
import datetime
import random
import pandas
import json
import argparse
import shutil
import hashlib
import time
from pathlib import Path
from configobj import ConfigObj
from helper.dbConnector import *
from helper.logger import get_logger

logger = get_logger(__name__)

class oculusAuditor():
    def __init__(self, isDebug, inputFile, isDatabaseStorage):
        """
        This function is used to initialise the class.
        isDebug: This flag will tell whether application will be running in debug mode or in production mode.
        inputFile: This is the path to the input file if debug flag is passed it will look into the file for the repo link.
        """
        try:
            logger.info("Initialising the Auditor")
            self.GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
            self.GITHUB_USERNAME = os.getenv('GITHUB_USERNAME')
            self.gh = Github(self.GITHUB_TOKEN)
            self.configObj = ConfigObj("config.cfg")
            self.ORGANIZATION_NAME = self.configObj.get('generalConfig').get('ORGANIZATION_NAME')
            self.GITLEAKS_FALSE_POSITIVE_REPO_PATH = self.configObj.get('generalConfig').get('GITLEAKS_FALSE_POSITIVE_REPO_PATH')
            self.REMOTE_GITLEAKS_FALSE_POSITIVE_REPO_PATH = self.configObj.get('generalConfig').get('REMOTE_GITLEAKS_FALSE_POSITIVE_REPO_PATH')
            self.BASEURL = self.configObj.get('generalConfig').get('BASEURL')
            self.isDebug = str(isDebug).lower()
            self.inputFile = str(inputFile)
            self.resultsDirectory = self.configObj.get('generalConfig').get('resultsDirectory')
            self.excelResultsDir = self.configObj.get('generalConfig').get('excelResultsDir')
            self.isDatabaseStorage = str(isDatabaseStorage).lower()
            if self.isDatabaseStorage == 'true':
                self.db = initialiseDB(os.getenv('databaseName'), os.getenv('connectionString'))
                self.collectionName = os.getenv('GITHUB_COLLECTION_NAME')
                self.maskedCollectionName = os.getenv('GITHUB_MASKED_COLLECTION_NAME')
            Path(self.excelResultsDir).mkdir(parents=True, exist_ok=True)
            Path(self.resultsDirectory).mkdir(parents=True, exist_ok=True)
            logger.info("Auditor Initialised")
        except Exception as e:
            logger.error("Unable to initialise auditor")


    def getRepos(self):
        """
        This function is used to fetch all the repos for an org.
        """
        try:
            logger.info("Getting repository for the organization.")
            repos = list()
            org = self.gh.get_organization(self.ORGANIZATION_NAME)
            repositories = org.get_repos()
            for repo in repositories:
                repos.append(repo.html_url)
        except Exception as e:
            logger.error("Cannot get the repository for the organzation, Please check the token or the internet connection")
        return repos        


    def generateRandomString(self, length):
        """
        This will generate the random string.
        length: the length of the string 
        """
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for i in range(length))

    
    def mask(self, str_to_mask):
        masked = str_to_mask[0:round(len(str_to_mask)/4)] + "*" * (len(str_to_mask) - round(len(str_to_mask)/4))
        return masked
    

    def pushToGithubMaskedDb(self, data):
        databaseObject = self.db.dbObject.get_database(self.db.databaseName).get_collection(self.maskedCollectionName)
        for leaks in data:
            leak = dict()
            try:
                leak['maskedOffender'] = self.mask(leaks.get('offender'))
                leak['lineNumber'] = leaks.get('lineNumber')
                leak['repoURL'] = leaks.get('repoURL')
                leak['commit'] = leaks.get('commit')
                leak['branchName'] = leaks.get('branchName')
                leak['uniqueHash'] = hashlib.sha256((leaks.get('offender') + leaks.get('commit') + leaks.get('file')).encode()).hexdigest()
                leak['leakURL'] = leaks.get('leakURL')
                databaseObject.insert_one(leak)
            except Exception as e:
                if e.code == 11000:
                    pass
                else:
                    logger.error("Unable to push leak having error: {0}".format(e))


    def pushToDatabase(self, reportName):
        try:
            with open(reportName) as jsonFile:            
                data = json.load(jsonFile)
        except Exception as e:
            logger.error('cannot read {0} json result file: {1}'.format(reportName, e))
            return
        if (data is None) or (data is not None and len(data) == 0):
            return
        for leak in data:
            try:
                leak['prNumber'] = 0
                leak['uniqueHash'] = hashlib.sha256((leak.get('offender') + leak.get('commit') + leak.get('file')).encode()).hexdigest()
                leak['fixedOn'] = ""
                leak['dateOfinsertion'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                databaseObject = self.db.dbObject.get_database(self.db.databaseName).get_collection(self.collectionName)
                databaseObject.insert_one(leak)    
                self.pushToGithubMaskedDb(data)
            except Exception as e:
                if e.code == 11000: # ignore the exception raised by duplicate entries.
                    pass
                else:
                    logger.error("Unable to push leak having error: {0}".format(e))


    def createResultsExcel(self, jsonResultsFile):
            """
            This function will take a json file as an input and will convert it in excel file.
            """
            try:
                with open(self.resultsDirectory + '/' + jsonResultsFile) as jsonFile:            
                    data = json.load(jsonFile)
                if data is None:
                    logger.error('{0} json result file is empty'.format(jsonResultsFile))
                    return
                df = pandas.read_json(self.resultsDirectory + '/' + jsonResultsFile.split('/')[-1])
                df['date'] = pandas.to_datetime(df['date'], utc=True)        
                df['date'] = df['date'].dt.tz_localize(None)
                logger.info("writing to {0}".format(jsonResultsFile.split('/')[-1].split('.')[0] + '.xlsx'))
                df.to_excel(self.excelResultsDir + '/' + jsonResultsFile.split('/')[-1].split('.')[0] + '.xlsx')     
            except Exception as e:
                logger.error("some error creating the excel file: {0}".format(e))
                return


    def cloneWhitelistrepo(self):
        """
            This function will clone the gitleaks false positive repo.
        """
        if os.path.exists('/tmp/gitleaks_false_positives'):
            shutil.rmtree('/tmp/gitleaks_false_positives')
        gitURL = 'https://' + self.GITHUB_USERNAME + ':' + self.GITHUB_TOKEN + self.REMOTE_GITLEAKS_FALSE_POSITIVE_REPO_PATH
        out = subprocess.run(['git', 'clone', gitURL, '/tmp/gitleaks_false_positives'], capture_output=True, text=True)
        if len(out.stdout) > 0:
            logger.error("An error occured while cloning the gitleaks false positive repo")
            return False
        return True


    def combineExcelsIntoOne(self):
        """
        This function will combine all the excel files into one.
        """
        logger.info("\ncombinig all excel files")
        try:
            cwd = os.path.abspath(self.excelResultsDir) 
            files = os.listdir(cwd)       
            df = pandas.DataFrame()
            for file in files:
                if file.endswith('.xlsx'):
                    df = pandas.concat([df, pandas.read_excel(cwd + '/' + file)])     
            filename = 'combinedReport' + datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.xlsx'
            col = ['line', 'lineNumber', 'offender', 'commit', 'repoURL', 'author', 'email', 'file', 'branchName', 'leakURL', 'date', 'tags']
            if len(df) > 0:
                df.to_excel(filename, columns=col)
                logger.info("All excel files combined successfully into {0}".format(filename))
        except Exception as e:
            logger.error("some error joining excel files: {0}".format(e))
        return filename


    def repoWise(self, url):
        """
        This function will run scans on the repo one by one.
        """
        try:
            url = url.split('.git')[0]
            jsonResultsFile = self.generateRandomString(12)+'.json'
            clonePath = self.generateRandomString(14)
            logger.info('Initialising scan for {0} repo, results will be saved in {1} file'.format(url.split('/')[-1], jsonResultsFile))
            if os.path.exists('/tmp/' + clonePath):
                shutil.rmtree('/tmp/' + clonePath)
            out = subprocess.run(['gitleaks', '--repo-url', url , '--username', self.GITHUB_USERNAME, '--password', self.GITHUB_TOKEN, '--clone-path', '/tmp/' + clonePath, '--quiet', '--report', self.resultsDirectory+ '/' + jsonResultsFile, '--additional-config', self.GITLEAKS_FALSE_POSITIVE_REPO_PATH], capture_output=True, text=True)
            if os.path.exists('/tmp/' + clonePath):
                shutil.rmtree('/tmp/' + clonePath)
            if len(out.stderr) > 0:
                logger.error('Cannot scan {0} repo.'.format(url))
            else:
                if self.isDatabaseStorage == 'true':
                    self.pushToDatabase(self.resultsDirectory + '/' + jsonResultsFile)
                else:
                    self.createResultsExcel(jsonResultsFile)   

                try:
                    #removing file from temp
                    logger.info("removing file {0}".format(jsonResultsFile))
                    os.remove(self.resultsDirectory + '/' + jsonResultsFile)
                except Exception as e:
                    logger.error("Unable to delete file: {0}".format(e))        
        except Exception as e:
            logger.error("An error occured, cannot scan the repo: {0}".format(e))


    def runGitleaks(self):
        """
        This function will run the trigger the flow.
        """
        logger.info('Triggering the flow')
        repos = list()
        if self.isDebug == 'true':
            try:
                with open(self.inputFile) as inf:
                    repos = [url for url in inf.read().split('\n') if len(url.strip('')) > 0]
            except Exception as e:
                logger.error("Cannot open the file getting error: {0}".format(e))
        else:
            repos = self.getRepos()

        if self.cloneWhitelistrepo() == False:
            logger.error("Unable to clone the gitleaks false positives repo. Please clone it manually.")
            return

        if len(repos) > 0:
            for repo in repos:
                self.repoWise(repo)
            
            if self.isDatabaseStorage == 'false':
                filename = self.combineExcelsIntoOne()
                if len(filename) > 0:
                    newfilename = filename.split('.')[0] + '_verified.xlsx'
                    out = subprocess.run(['python3', 'excelUpdater.py', '-p', filename, '-o', newfilename], capture_output=True, text=True)
        if os.path.exists(self.excelResultsDir):
            shutil.rmtree(self.excelResultsDir)
        if os.path.exists(self.resultsDirectory):
            shutil.rmtree(self.resultsDirectory)
        logger.info('Finished')


if __name__ == "__main__":
    # argument parsing
    parser = argparse.ArgumentParser(usage='%(prog)s -d true/false [-p file_path] [-db true/false]')
    parser.add_argument('-d', '--debug', default='false', help='It will accept boolean value')
    parser.add_argument('-p', '--file_path', default='input.txt', help='Path of the file which contains the list of the repositories to scan, each line will contain a repo link')
    parser.add_argument('-db', '--database', default='false', help='Whether you want to store data in the db or not. It will take boolean value')
    args = parser.parse_args()
    isDebug = args.debug
    inputFile = args.file_path
    isDatabaseStorage = args.database
    auditor = oculusAuditor(isDebug, inputFile, isDatabaseStorage)
    auditor.runGitleaks()