import subprocess
import json
from datetime import datetime
import argparse
import os
import pandas as pd
import re
import requests
import boto3
from helper.logger import get_logger

logger = get_logger(__name__)


def upload_s3(filename, destFilename):
    try:
        s3 = boto3.client('s3')
        with open(filename, 'rb') as data:
            s3.upload_fileobj(data, os.getenv('BUCKET_NAME'), destFilename)
        logger.info('successfully uploaded to bucket')
        if os.path.exists(filename):
            os.remove(filename)
    except Exception as e:
        logger.error('unable to put data in bucket: {0}'.format(e))


def create_excel_and_upload(filename, platformIdentifier):
    bucketPath = platformIdentifier + '/'
    destFilename = bucketPath+filename
    upload_s3(filename, destFilename)


def updateExcel(excelPath, outPath, uploadToS3, platformIdentifier):
    try:
        VERITAS_URL = os.getenv('VERITAS_URL')
        df = pd.read_excel(excelPath)
        for index, row in df.iterrows():
            if 'jwt' in str(row['tags']).lower():
                jwtRegex = """\\b(ey[a-zA-Z0-9]{17,}\\.ey[a-zA-Z0-9\\/\\\\_-]{17,}\\.(?:[a-zA-Z0-9\\/\\\\_-]{10,}={0,2})?)\\b"""
                text = row['offender']
                x = re.search(re.compile(jwtRegex), text)
                if x is not None:
                    tag = 'jwt'
                    data = {"tag": tag, "key": x.group()}
                    try:
                        res = requests.post(VERITAS_URL, json=data)
                        if res.json()['status'] == 'False':
                            df.at[index, 'status'] = 'invalid'
                        else:
                            df.at[index, 'status'] = 'valid'
                    except Exception as e:
                        logger.error(e)
                else:
                    df.at[index, 'status'] = 'invalid'
            elif 'npm' in str(row['tags']).lower():
                npmRegex = """(?i)\\b(npm_[a-z0-9]{36})\\b"""
                text = row['offender']
                x = re.search(re.compile(npmRegex), text)
                if x is not None:
                    tag = 'npm'
                    data = {"tag": tag, "key": x.group()}
                    try:
                        res = requests.post(VERITAS_URL, json=data)
                        if res.json()['status'] == 'False':
                            df.at[index, 'status'] = 'invalid'
                        else:
                            df.at[index, 'status'] = 'valid'
                    except Exception as e:
                        logger.error(e)
                else:
                    df.at[index, 'status'] = 'invalid'
            elif 'google' in str(row['tags']).lower():
                text = row['offender']
                tag = 'google'
                data = {"tag": tag, "key": text}
                try:
                    res = requests.post(VERITAS_URL, json=data)
                    if res.json()['status'] == 'False':
                        df.at[index, 'status'] = 'invalid'
                    else:
                        df.at[index, 'status'] = 'valid'
                except Exception as e:
                    logger.error(e)
            elif 'github' in str(row['tags']).lower():
                text = row['offender']
                tag = 'github'
                data = {"tag": tag, "key": text}
                try:
                    res = requests.post(VERITAS_URL, json=data)
                    if res.json()['status'] == 'False':
                        df.at[index, 'status'] = 'invalid'
                    else:
                        df.at[index, 'status'] = 'valid'
                except Exception as e:
                    logger.error(e)
            elif 'slack' in str(row['tags']).lower():
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
                text = row['offender']
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
                                df.at[index, 'status'] = 'invalid'
                            else:
                                df.at[index, 'status'] = 'valid'
                        except Exception as e:
                            logger.error(e)
                if flag == False:
                    df.at[index, 'status'] = 'invalid'
            else:
                continue
        df.to_excel(outPath, index=False)
        if uploadToS3 == 'true':
            create_excel_and_upload(outPath, platformIdentifier)
    except Exception as e:
        logger.error('Cannot process the excel file {0}'.format(e))

if __name__ == "__main__":
    # argument parsing
    parser = argparse.ArgumentParser(usage='%(prog)s -p input_file_path -o output_file_path [-us3 true/false] [-platformIdentifier github/confluence]')
    parser.add_argument('-p', '--input_file_path', default='input.xlsx', help='Path of the file which contains the link of the credentials findings')
    parser.add_argument('-o', '--output_file_path', default='output.xlsx', help='output file')
    parser.add_argument('-us3', '--uploadToS3', default='false', help='whether you want to upload the results to the s3 bucket or not.')
    parser.add_argument('-platformIdentifier', '--platformIdentifier', default='temp', help='To identify which platform is calling it.')
    args = parser.parse_args()
    excelPath = args.input_file_path
    outPath = args.output_file_path
    uploadToS3 = args.uploadToS3
    platformIdentifier = args.platformIdentifier
    updateExcel(excelPath, outPath, uploadToS3, platformIdentifier)