client = MongoClient("mongodb://localhost:27017/")
db = client['right_path']
users_collection = db['users']
responses_collection = db['responses']