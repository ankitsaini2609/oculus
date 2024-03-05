import mongoengine
import json
import os


class initialiseDB:
    databaseName = None
    databasePath = None
    dbObject = None

    def __init__(self, databaseName, databasePath):
        self.databaseName = databaseName
        self.databasePath = databasePath
        self.dbObject = mongoengine.connect(self.databaseName, host=self.databasePath, alias='default')
        scanResults.create_index([('uniqueHash', 1)], unique=True)
        maskedScanResults.create_index([('uniqueHash', 1)], unique=True)

class scanResults(mongoengine.Document):
    line = mongoengine.StringField(required=True)
    lineNumber = mongoengine.IntField(required=True)
    offender = mongoengine.StringField(required=True)
    offenderEntropy = mongoengine.IntField(required=True)
    commit = mongoengine.StringField(required=True)
    repo = mongoengine.StringField(required=True)
    repoURL = mongoengine.URLField(required=True)
    leakURL = mongoengine.URLField(required=True)
    rule = mongoengine.StringField(required=True)
    commitMessage = mongoengine.StringField(required=True)
    author = mongoengine.StringField(required=True)
    email = mongoengine.EmailField(required=True)
    file = mongoengine.StringField(required=True)
    date = mongoengine.StringField(required=True)
    dateOfinsertion = mongoengine.StringField(required=True)
    tags = mongoengine.StringField(required=True)
    branchName = mongoengine.StringField(required=True)
    prNumber = mongoengine.IntField(required=True)
    uniqueHash = mongoengine.StringField(required=True, unique=True)
    fixedOn = mongoengine.StringField()


class maskedScanResults(mongoengine.Document):
    maskedOffender = mongoengine.StringField(required=True)
    lineNumber = mongoengine.IntField(required=True)
    commit = mongoengine.StringField(required=True)
    repoURL = mongoengine.URLField(required=True)
    branchName = mongoengine.StringField(required=True)
    leakURL = mongoengine.StringField()
    uniqueHash = mongoengine.StringField(required=True, unique=True)