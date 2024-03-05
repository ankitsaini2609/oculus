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
        confluenceResults.create_index([('uniqueHash', 1)], unique=True)


class confluenceResults(mongoengine.Document):
    space = mongoengine.StringField(required=True)
    page = mongoengine.StringField(required=True)
    tags = mongoengine.StringField(required=True)
    offender = mongoengine.StringField(required=True)
    line = mongoengine.StringField()
    uniqueHash = mongoengine.StringField(required=True, unique=True)
    leakURL = mongoengine.StringField(required=True)
    fixedOn = mongoengine.StringField()
    createdBy = mongoengine.StringField()
    lastUpdatedBy = mongoengine.StringField()
    frequentlyUpdatedBy = mongoengine.StringField()
    version = mongoengine.StringField(required=True)