#!/usr/bin/python

import os
import requests
import json
from bs4 import BeautifulSoup
from time import sleep
import re
import hashlib
import argparse
import pandas
import datetime
import subprocess
from helper.logger import get_logger
from helper.confluenceConnector import *
from configobj import ConfigObj

logger = get_logger(__name__)


class confluenceScanner():
    def __init__(self, isDatabaseStorage):
        logger.info('initialising the database')
        self.configObj = ConfigObj("config.cfg")
        self.domain = self.configObj.get('confluenceConfig').get('domain')
        self.isDatabaseStorage = isDatabaseStorage
        if isDatabaseStorage == 'true':
            self.db = initialiseDB(os.getenv('databaseName'), os.getenv('connectionString'))
            self.confluenceCollection = os.getenv('CONFLUENCE_COLLECTION')
        self.confluenceToken = os.getenv('CONFLUENCE_TOKEN')
        logger.info('Database intialised.')
        

    def getAllSpace(self):
        url = 'https://{0}.atlassian.net/wiki/rest/api/space'.format(self.domain)
        headers = {
            "Accept": "application/json",
            "Authorization": "Basic {0}".format(self.confluenceToken)
        }
        spaces = list()
        try:
            while True:
                res = requests.get(url, headers=headers, timeout=2)
                for result in res.json().get('results'):
                    spaces.append(result.get('key'))
                if res.json().get('_links') is not None and res.json().get('_links').get('next') is not None:
                    url = res.json().get('_links').get('base') + res.json().get('_links').get('next')
                else:
                    break
        except Exception as e:
            logger.error("Exception occured while getting all spaces")

        return spaces


    def getAllPages(self, space):
        url = 'https://{0}.atlassian.net/wiki/rest/api/space/{1}/content?start=0&limit=999&type=page'.format(self.domain, space)
        headers = {
            "Accept": "application/json",
            "Authorization": "Basic {0}".format(self.confluenceToken)
        }
        pages = list()
        try:
            while True:
                res = requests.get(url, headers=headers, timeout=2)
                if res.json().get('_links') is not None and res.json().get('page') is not None:
                    if res.json().get('page').get('results') is not None:
                        for result in res.json().get('page').get('results'):
                            pages.append(result.get('id'))
                    if res.json().get('page').get('_links') is not None and res.json().get('page').get('_links').get('next') is not None:
                        url = res.json().get('_links').get('base') + res.json().get('page').get('_links').get('next')
                    else:
                        break
                else:
                    break
        except Exception as e:
            logger.error("Exception occured while getting all pages of space: {0}".format(space))
        return pages


    def findFrequentlyUpdatedBy(self, page, number):
        userCount = dict()
        while number > 0:
                url = 'https://{0}.atlassian.net/wiki/rest/api/content/{1}/version/{2}'.format(self.domain, page, number)
                headers = {
                    "Accept": "application/json",
                    "Authorization": "Basic {0}".format(self.confluenceToken)
                }
                try: 
                    res = requests.get(url, headers=headers, timeout=2)
                    if res.json() is not None and res.json().get('by') is not None and res.json().get('by').get('email') is not None:
                        email = res.json().get('by').get('email')
                        if email in userCount.keys():
                            userCount[email] += 1
                        else:
                            userCount[email] = 1
                except Exception as e:
                    logger.error("Exception occured while getting Frequently Updated user details for {0}".format(page))
                number -= 1
        return max(userCount, key=userCount.get)


    def getOwnerDetails(self, page):
        url = 'https://{0}.atlassian.net/wiki/rest/api/content/{1}/history'.format(self.domain, page)
        headers = {
            "Accept": "application/json",
            "Authorization": "Basic {0}".format(self.confluenceToken)
        }
        createdBy = lastUpdatedBy = frequentlyUpdatedBy = ''
        try:
            res = requests.get(url, headers=headers, timeout=2)
            if res.json() is not None and res.json().get('createdBy') is not None and res.json().get('createdBy').get('email') is not None:
                createdBy = res.json().get('createdBy').get('email')
            if res.json() is not None and res.json().get('lastUpdated') is not None:
                if res.json().get('lastUpdated').get('by') is not None and res.json().get('lastUpdated').get('by').get('email') is not None:
                    lastUpdatedBy = res.json().get('lastUpdated').get('by').get('email')
                if res.json().get('lastUpdated').get('number') is not None:
                    frequentlyUpdatedBy = self.findFrequentlyUpdatedBy(page, res.json().get('lastUpdated').get('number'))
            else:
                frequentlyUpdatedBy = createdBy = lastUpdatedBy
        except Exception as e:
            logger.error("Exception occured while getting owner details for {0}".format(page))
        return createdBy, lastUpdatedBy, frequentlyUpdatedBy


    def pushToDatabase(self, data):
        databaseObject = self.db.dbObject.get_database(self.db.databaseName).get_collection(self.confluenceCollection)
        try:
            databaseObject.insert_one(data)     
        except Exception as e:
            if e.code == 11000: # ignore the exception raised by duplicate entries.
                pass
            else:
                logger.error(e)


    def runSecretCodeScanning(self, text, space, page, version, findings):
        regexDict = {
            "SLACK_WEBHOOKS":"""https://hooks.slack.com/services/T[a-zA-Z0-9_]{8}/B[a-zA-Z0-9_]{8}/[a-zA-Z0-9_]{24}""",
            "TWILIO": """(?i)twilio(.{0,20})?SK[0-9a-f]{32}""",
            "STRIPE" : """(?i)stripe(.{0,20})?[sr]k_live_[0-9a-zA-Z]{24}""",
            "SLACK_API_TOKENS" : """xox[baprs]([0-9a-zA-Z-]{10,72})""",
            "MAILGUN" : """key-[0-9a-zA-Z]{32}""",
            "MAILCHIMP" : """[0-9a-f]{32}-us[0-9]{1,2}""",
            "GOOGLE" : """AIza[0-9A-Za-z\\-_]{35}|[0-9]+-[0-9A-Za-z_]{32}""",
            "GITHUB" : """(ghu|ghs|gho|ghp|ghr)_[0-9a-zA-Z]{36}""",
            "GITLAB": """gl(pat|rat|gat)-[0-9a-zA-Z\-\_]{20}""",
            "AWS" : """\\b(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}\\b""",
            "PASSWORD": """(?i)(password|pass|passwd)=[0-9a-zA-Z-_.{}]{4,120}""",
            "PYPI": """pypi-AgEIcHlwaS5vcmc[A-Za-z0-9-_]{50,1000}""",
            "SENDGRID": """SG\.[\w_]{16,32}\.[\w_]{16,64}""",
            "PAYPAL": """access_token\$production\$[0-9a-z]{16}\$[0-9a-f]{32}""",
            "JWT": """\\b(ey[a-zA-Z0-9]{17,}\\.ey[a-zA-Z0-9\\/\\\\_-]{17,}\\.(?:[a-zA-Z0-9\\/\\\\_-]{10,}={0,2})?)\\b""",
            "NPM": """(?i)\\b(npm_[a-z0-9]{36})\\b"""
        }

        for regex in regexDict.keys():
            if regex == "PASSWORD":
                x = re.findall(re.compile(regexDict[regex], re.IGNORECASE), text)
            else:
                x = re.findall(re.compile(regexDict[regex]), text)
            if len(x) > 0:
                logger.info("Leak detected: {0}".format(regex))
                createdBy, lastUpdatedBy, frequentlyUpdatedBy = self.getOwnerDetails(page)
                for finding in x:
                    data = {
                        "space": str(space),
                        "page": str(page), 
                        "tags": str(regex), 
                        "offender": str(finding), 
                        "uniqueHash": hashlib.sha256((str(space) + str(page) + str(regex) + str(finding)).encode()).hexdigest(), 
                        "leakURL": "https://{0}.atlassian.net/wiki/pages/viewpage.action?pageId={1}&pageVersion={2}".format(self.domain, str(page), str(version)),
                        "createdBy": createdBy,
                        "lastUpdatedBy": lastUpdatedBy,
                        "frequentlyUpdatedBy": frequentlyUpdatedBy,
                        "version": str(version),
                        "fixedOn":"",
                        "line": str(finding)
                    }
                    if self.isDatabaseStorage == 'true':
                        self.pushToDatabase(data)
                    else:
                        findings.append(data)
        return findings


    def scanPage(self, page, space):
        findings = list()
        url = 'https://{0}.atlassian.net/wiki/rest/api/content/{1}/history'.format(self.domain, page)
        headers = {
            "Accept": "application/json",
            "Authorization": "Basic {0}".format(self.confluenceToken)
        }
        res = requests.get(url, headers=headers, timeout=2)
        number = 0
        if res.json() is not None and res.json().get('lastUpdated') is not None and res.json().get('lastUpdated').get('number') is not None:
            number = res.json().get('lastUpdated').get('number')
        for num in range(1, number+1):
            url = 'https://{0}.atlassian.net/wiki/rest/api/content/{1}?expand=body.storage,&version={2}'.format(self.domain, page, num)
            logger.info("Looking in v{0}".format(num))
            try:
                res = requests.get(url, headers=headers, timeout=2)
                if res.json().get('body') is not None and res.json().get('body').get('storage') is not None and res.json().get('body').get('storage').get('value') is not None:
                    htmlContent = res.json().get('body').get('storage').get('value')
                    soup = BeautifulSoup(htmlContent, 'html.parser')
                    formattedContent = soup.get_text(separator=' ')
                    findings += self.runSecretCodeScanning(formattedContent, space, page, num, findings)
                    sleep(2)
            except Exception as e:
                logger.error("Exception occured while getting content for {0}".format(page))
        return findings


    def createExcel(self, filename, findings):
        if os.path.exists(filename):
            df = pandas.read_excel(filename)
        else:
            df = pandas.DataFrame()

        try:
            df = df.append(findings, ignore_index=True)
            df.to_excel(filename, index=False)
        except Exception as e:
            logger.error('Unable to save confluence results in the excel file, getting error: {0}'.format(e))


    def main(self):
        spaces = self.getAllSpace()
        noOfSpaces = len(spaces)
        filename = 'confluenceReport' + datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.xlsx'
        for space in spaces:
            pages = self.getAllPages(space)
            noOfPages = len(pages)
            for page in pages:
                logger.info('{0}:{1}'.format(space, page))
                findings = self.scanPage(page, space)
                if len(findings) > 0:
                    self.createExcel(filename, findings)
                noOfPages -= 1
                logger.info('remaining pages: {0}'.format(noOfPages))
                sleep(2)
            noOfSpaces -= 1
            logger.info('remaining spaces: {0}'.format(noOfSpaces))

        if self.isDatabaseStorage == 'false':
            try:
                newfilename = filename.split('.')[0] + '_verified.xlsx'
                out = subprocess.run(['python3', 'excelUpdater.py', '-p', filename, '-o', newfilename], capture_output=True, text=True)
            except Exception as e:
                logger.error("An error occurred while running veritas: {0}".format(e))
        logger.info("completed")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(usage='%(prog)s [-db true/false]')
    parser.add_argument('-db', '--database', default='false', help='Please mark it as true, if you want to use database.')
    args = parser.parse_args()
    isDatabaseStorage = str(args.database).lower()
    cs = confluenceScanner(isDatabaseStorage)
    cs.main()
