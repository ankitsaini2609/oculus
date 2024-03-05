import os
import boto3
import requests
import re
import argparse
from slack_sdk import WebClient
from configobj import ConfigObj
from helper.logger import get_logger
from helper.realTimeNotificationConnector import *

logger = get_logger(__name__)

class realTimeNotifications:
    def __init__(self, githubFlag, confluenceFlag, emailFlag, slackFlag):
        try:
            logger.info('Initialising the realTimeNotifications service')
            self.db = initialiseDB(os.getenv('databaseName'), os.getenv('connectionString'))
            self.notificationTrackerCollection = os.getenv('NOTIFICATION_TRACKER')
            self.githubFlag = githubFlag
            self.confluenceFlag = confluenceFlag
            self.emailFlag = emailFlag
            self.slackFlag = slackFlag
            self.configObj = ConfigObj("config.cfg")
            if self.githubFlag == 'true':
                self.githubCollectionName = os.getenv('GITHUB_COLLECTION_NAME')
            if self.confluenceFlag == 'true':
                self.confluenceCollection = os.getenv('CONFLUENCE_COLLECTION')
            if self.emailFlag == 'true':
                self.fromEmail = self.configObj.get('notificationEmailConfig').get('fromEmail')
                self.ccEmail = self.configObj.get('notificationEmailConfig').get('ccEmail')
                self.regionName = self.configObj.get('notificationEmailConfig').get('regionName')
                self.ORGANIZATION_EMAIL_DOMAIN = self.configObj.get('notificationEmailConfig').get('ORGANIZATION_EMAIL_DOMAIN')
                self.emailMessageTemplate = '''
                                    <html>
                                        <head></head>
                                        <body>
                                            <p>Hi {0},</p>
                                            <p>We have found that you have hardcoded the credentials in the codebase. Harcoding credentials is a big security and compliance issue. Please refrain from doing it.</p>
                                            <p><strong>Please find the relevant details below:</strong><br>
                                            <ul>
                                                <li>URL of the issue => {2}</li>
                                                <li>Hardcoded Key => {3}</li>
                                            </ul>
                                            </p>
                                            <p><strong>Action items:</strong><br>
                                                <ol>
                                                    <li>Please get the credentials invalidated immediately.</li>
                                                    <li>If you think, it is a false positive please raise a pull request in gitleaks_false_positives repo.</li>
                                                </ol>
                                            </p>
                                            <p>Credentials should always be stored in the environment variables/vault/config service/or some secrets manager, but do not hard coded it in the code base.</p>
                                        </body>
                                    </html>
                                '''
            if self.slackFlag == 'true':
                self.channelName = self.configObj.get('notificationSlackConfig').get('channelName')
                self.SLACK_TOKEN = os.getenv('SLACK_TOKEN')
                self.slackMessageTemplate = '''
                                    Hi `{0}`,
                                    \nWe have found that you have hardcoded the credentials in the codebase. Harcoding credentials is a big security and compliance issue. Please refrain from doing it.
                                    \n*_Please find the relevant details below:_*
                                        \n  - URL of the issue => `{2}`\n
                                        \n  - Hardcoded Key => `{3}`\n

                                    \n\n*_Action items:_*
                                        \n  1. Please get the credentials invalidated immediately\n
                                        \n  2. If you think, it is a false positive please raise a pull request in gitleaks_false_positives repo.\n
                                    
                                    \n\nCredentials should always be stored in the environment variables/vault/config service/or some secrets manager, but do not hard coded it in the code base.
                                '''
            logger.info('Initialised')
        except Exception as e:
            logger.error('Cannot initalise the realTimeNotifications, getting error: {0}'.format(e))


    def mask(self, str_to_mask):
        masked = str_to_mask[0:round(len(str_to_mask)/4)] + "*" * (len(str_to_mask) - round(len(str_to_mask)/4))
        return masked
    
    
    def verify(self, document):
        try:
            VERITAS_URL = os.getenv('VERITAS_URL')
            if 'jwt' in str(document.get('tags')).lower():
                jwtRegex = """\\b(ey[a-zA-Z0-9]{17,}\\.ey[a-zA-Z0-9\\/\\\\_-]{17,}\\.(?:[a-zA-Z0-9\\/\\\\_-]{10,}={0,2})?)\\b"""
                text = document.get('offender')
                x = re.search(re.compile(jwtRegex), text)
                if x is not None:
                    tag = 'jwt'
                    data = {"tag": tag, "key": x.group()}
                    try:
                        res = requests.post(VERITAS_URL, json=data)
                        if res.json()['status'] == 'True':
                            return True
                        else:
                            return False
                    except Exception as e:
                        logger.error(e)
                        return False
                else:
                    return False
            elif 'npm' in str(document.get('tags')).lower():
                npmRegex = """(?i)\\b(npm_[a-z0-9]{36})\\b"""
                text = document.get('offender')
                x = re.search(re.compile(npmRegex), text)
                if x is not None:
                    tag = 'npm'
                    data = {"tag": tag, "key": x.group()}
                    try:
                        res = requests.post(VERITAS_URL, json=data)
                        if res.json()['status'] == 'True':
                            return True
                        else:
                            return False
                    except Exception as e:
                        logger.error(e)
                        return False
                else:
                    return False
            elif 'google' in str(document.get('tags')).lower():
                text = document.get('offender')
                tag = 'google'
                data = {"tag": tag, "key": text}
                try:
                    res = requests.post(VERITAS_URL, json=data)
                    if res.json()['status'] == 'True':
                        return True
                    else:
                        return False
                except Exception as e:
                    logger.error(e)
                    return False
            elif 'github' in str(document.get('tags')).lower():
                text = document.get('offender')
                tag = 'github'
                data = {"tag": tag, "key": text}
                try:
                    res = requests.post(VERITAS_URL, json=data)
                    if res.json()['status'] == 'True':
                        return True
                    else:
                        return False
                except Exception as e:
                    logger.error(e)
                    return False
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
                            if res.json()['status'] == 'True':
                                return True
                            else:
                                return False
                        except Exception as e:
                            logger.error(e)
                            return False
                if flag == False:
                    return False
            else:
                return False
        except Exception as e:
            logger.error('Got exception for the given document with {} unique hash'.format(document.get('uniqueHash')))


    def sendEmail(self, document):
        try:
            ses_client = boto3.client('ses', region_name=self.regionName)
            subject = 'Re: Hardcoded credentials detected by Oculus in {0}'.format(document.get('repo'))
            source = self.fromEmail
            destination = document.get('email')
            if not destination.endswith('@' + self.ORGANIZATION_EMAIL_DOMAIN):
                destination = self.fromEmail
            cc_list = self.ccEmail.split(',')
            emailTemplate = self.emailMessageTemplate.format(document.get('author'), destination, document.get('leakURL'), document.get('offender'))
            email = {
                'Source': source,
                'Destination': {
                    'ToAddresses': [destination],
                    'CcAddresses': cc_list if cc_list else []  # Include CC if provided
                },
                'Message': {
                    'Subject': {'Data': subject},
                    'Body': {'Html': {'Data': emailTemplate}}
                }
            }
            ses_client.send_email(**email)
        except Exception as e:
            print('Unable to send email, please find the attached list: {0}'.format(e))


    def sendSlackMessage(self, document):
        messsageTemplateSlack = self.slackMessageTemplate.format(document.get('author'), document.get('email'), document.get('leakURL'), document.get('offender'))
        try:
            client = WebClient(token=self.SLACK_TOKEN)
            response = client.chat_postMessage(channel=self.channelName, text=messsageTemplateSlack, parse="full")
        except Exception as e:
            logger.error('Unable to post in the slack channel, getting error: {0}'.format(e))

    
    def sendNotification(self, document):
        if self.emailFlag == 'true':
            self.sendEmail(document)
        if self.slackFlag == 'true':
            self.sendSlackMessage(document)
        

    def pushToDatabase(self, document):
        databaseObject = self.db.dbObject.get_database(self.db.databaseName).get_collection(self.notificationTrackerCollection)
        leak = dict()
        try:
            leak['offender'] = document.get('offender')
            databaseObject.insert_one(leak)
            document['offender'] = self.mask(document['offender'])
            self.sendNotification(document)
        except Exception as e:
            if e.code == 11000:
                pass
            else:
                logger.error("Unable to push leak having error: {0}".format(e))


    def main(self):
        cursor = self.db.dbObject.watch()
        logger.info('Watcher is active... looking in {0}'.format(self.db.databaseName))
        while True:
            document = next(cursor)
            if self.githubFlag == 'true':
                if document.get('ns') is not None and document.get('ns').get('coll') == self.githubCollectionName:
                    if document.get('fullDocument') is not None and document.get('operationType') is not None and document.get('operationType') == 'insert':
                        document = document.get('fullDocument')
                        if self.verify(document):
                            self.pushToDatabase(document)
                                
            elif self.confluenceFlag == 'true':
                if document.get('ns') is not None and document.get('ns').get('coll') == self.confluenceCollection:
                    if document.get('fullDocument') is not None and document.get('operationType') is not None and document.get('operationType') == 'insert':
                        document = document.get('fullDocument')
                        if self.verify(document):
                            self.pushToDatabase(document)
            else:
                logger.error('Not watching the current collection.')


if __name__ == '__main__':
    # argument parsing
    parser = argparse.ArgumentParser(usage='%(prog)s -gh true/false [-c true/false]')
    parser.add_argument('-c', '--confluence', default='false', help='whether you want to watch the confluence db or not.')
    parser.add_argument('-gh', '--github', default='false', help='whether you want to watch the github db or not.')
    parser.add_argument('-e', '--email', default='false', help='whether you want to send the notification on email.')
    parser.add_argument('-sl', '--slack', default='false', help='whether you want to send the notification on slack.')
    args = parser.parse_args()
    githubFlag = str(args.github).lower()
    confluenceFlag = str(args.confluence).lower()
    emailFlag = str(args.email).lower()
    slackFlag = str(args.slack).lower()
    rtn = realTimeNotifications(githubFlag, confluenceFlag, emailFlag, slackFlag)
    rtn.main()