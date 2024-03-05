# oculus Auditor
This repository contains credentials auditor for different platforms like Github for organisations. For now only Github and Confluence is supported.
- **githubAuditor.py**: It will run the audits on Github.
- **confluenceScanner.py**: It will run the audits on Confluence.
- **excelUpdater.py**: If you are using file based approach to store the results, It will take excel file as input, validate the credentials with the help of Veritas and generate a new file with _verified appended in the end. It also supports uploading of the results in the database.
- **databaseUpdater.py**: If you are using database based approach to store the results, It will validate the credentials and update the database accordingly. It also supports uploading of the result in the database.
- **realTimeNotification.py**: It will actively monitor the database and incase of any new valid insertion it will notify the user on slack or email. Check help to know more.

```
usage: githubAuditor.py -d true/false [-p file_path] [-db true/false]

options:
  -h, --help            show this help message and exit
  -d DEBUG, --debug DEBUG
                        It will accept boolean value
  -p FILE_PATH, --file_path FILE_PATH
                        Path of the file which contains the list of the repositories to scan, each line will contain a repo link
  -db DATABASE, --database DATABASE
                        Whether you want to store data in the db or not. It will take boolean value

-d: true/false
true -> It will take value from input.txt, If you want to pass a different file use -p option.
false -> It will run the scans directly on the organization. 

-db: true/false 
true -> It will store everything in the database.
For now, Only **mongodb** is supported.
```
For excel updater:
```
usage: excelUpdater.py -p input_file_path -o output_file_path [-us3 true/false] [-platformIdentifier github/confluence]

options:
  -h, --help            show this help message and exit
  -p INPUT_FILE_PATH, --input_file_path INPUT_FILE_PATH
                        Path of the file which contains the link of the credentials findings
  -o OUTPUT_FILE_PATH, --output_file_path OUTPUT_FILE_PATH
                        output file
  -us3 UPLOADTOS3, --uploadToS3 UPLOADTOS3
                        whether you want to upload the results to the s3 bucket or not.
  -platformIdentifier PLATFORMIDENTIFIER, --platformIdentifier PLATFORMIDENTIFIER
                        To identify which platform is calling it.
```
Currently supported values for platformIdentifier is github and confluence only.
You can use -h option with any of the module to get the help.
 

## Prerequisite
- Run [veritas](https://github.com/ankitsaini2609/veritas) before running Oculus.
- Replace the <ORGANIZATION_NAME> with the org name you want to test in config.cfg.
- Replace the REMOTE_GITLEAKS_FALSE_POSITIVE_REPO_PATH in the config.cfg. (Remember to put '@' and starts with github.com/...)
- For Github, Generate a classic token with full read access.
- Setup the GITHUB_USERNAME, GITHUB_TOKEN and VERITAS_URL(ip, where it is running along with the endpoint) as environment variables.
- Build the [Gitleaks](https://github.com/ankitsaini2609/gitleaks). If you want to add more regexes you can add it in [this file](https://github.com/ankitsaini2609/gitleaks/blob/main/config/default.go). Rest of the instructions are mentioned in the Gitleak's README.md.
- It is also using [Gitleaks False Positive repo](https://github.com/ankitsaini2609/gitleaks_false_positives) to whitelist false positive credentials.
- If you have opted to use Database, make sure to set the following environment variables:
    - GITHUB_COLLECTION_NAME = scan_results (make sure if you are changing these values, add the meta data for the same in the class.)
    - GITHUB_MASKED_COLLECTION_NAME = masked_scan_results (make sure if you are changing these values, add the meta data for the same in the class.)
    - databaseName = databaseName
    - connectionString = mongodb://username:password@host_ip:port/databaseName
    - set **BUCKET_NAME** env variable, If you have decided to use s3 upload feature. By keeping security in the mind, It will work when your **instance will have role based access**.
- For Confluence set the below values in environment variables along with databaseName and connectionString: 
    - CONFLUENCE_COLLECTION = confluence_results (make sure if you are changing these values, add the meta data for the same in the class.)
    - CONFLUENCE_TOKEN (format -> base64(email:APIToken))
    - Update the domain in config.cfg
- For Notification you have to set the below values in the environment variables along with databaseName and connectionString: 
    - NOTIFICATION_TRACKER = notification_tracker (This collection will track for which offender the notification has been sent.)
    - Update the values in the config.cfg for notificationEmailConfig and notificationSlackConfig.
    - set the values for GITHUB_COLLECTION_NAME, VERITAS_URL, CONFLUENCE_COLLECTION and SLACK_TOKEN in the environment variable.
    - sendEmail is based on AWS SES so make sure the role attached to the instance will have appropriate access.

## How to Run
```
pip3 install -r requirements.txt
python3 githubAuditor.py -d false 
python3 confluenceScanner.py 
```

## Future Scope
- Can be extended to other services like Gitlab, Bitbucket, JIRA etc.
- You can maintain the count in the notification tracker and send the number of notifications based on that. In case you want to send more than one notification.



