from peewee import *

class RetryDatabase(MySQLDatabase):
	pass

# # SQL Connection
MYSQL_HOST = 'xxx.amazonaws.com'
MYSQL_HOST_RO = 'xxx.amazonaws.com'
MYSQL_USER = 'root'
MYSQL_PASSWORD = '......'
#
DATABASE = 'Fontys'

database = RetryDatabase(DATABASE,
						 host=MYSQL_HOST,
						 user=MYSQL_USER,
						 password=MYSQL_PASSWORD,
						 charset='utf8mb4')
database_ro = RetryDatabase(DATABASE,
							host=MYSQL_HOST_RO,
							user=MYSQL_USER,
							password=MYSQL_PASSWORD,
							charset='utf8mb4')
class UnknownField(object):
    def __init__(self, *_, **__): pass

class BaseModel(Model):
    class Meta:
        database = database

class Results(BaseModel):
    original_url = CharField(null=True)
    start_url = CharField(null=True)
    sub_url = CharField(null=True)
    text = CharField(null=True)
    is_alive = FloatField(null=True)
    level = FloatField(null=True)

    class Meta:
        table_name = 'results'




class FontysStartURL(BaseModel):
    start_url = CharField(null=True)
    id = FloatField(null=True)

    class Meta:
        table_name = 'start_urls'