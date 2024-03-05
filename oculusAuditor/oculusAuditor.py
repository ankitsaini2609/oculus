import argparse
from githubAuditor import *
from confluenceScanner import *

def main(isDatabaseStorage, githubFlag, confluenceFlag):
    if githubFlag == 'true':
        auditor = oculusAuditor('false', 'input.txt', isDatabaseStorage)
        auditor.runGitleaks()

    if confluenceFlag == 'true':
        cs = confluenceScanner(isDatabaseStorage)
        cs.main()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(usage='%(prog)s -gh true/false -c true/false [-db true/false]')
    parser.add_argument('-gh', '--githubFlag', default='true', help='Whether you want to run the scans on github or not.')
    parser.add_argument('-c', '--confluenceFlag', default='true', help='Whether you want to run the scans on confluence or not.')
    parser.add_argument('-db', '--database', default='false', help='Whether you want to store data in the db or not. It will take boolean value')
    args = parser.parse_args()
    isDatabaseStorage = str(args.database).lower()
    githubFlag = str(args.githubFlag).lower()
    confluenceFlag = str(args.confluenceFlag).lower()
    main(isDatabaseStorage, githubFlag, confluenceFlag)