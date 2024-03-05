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
        notificationTracker.create_index([('offender', 1)], unique=True)

class notificationTracker(mongoengine.Document):
    offender = mongoengine.StringField(required=True, unique=True)