from urllib.parse import quote_plus

username = quote_plus("lehoangkhoi7705")
password = quote_plus("0333503352Lhk@")
host = "testsampledata.6ciqjs6.mongodb.net"  # thay bằng host thực tế của bạn

mongo_uri = f"mongodb+srv://{username}:{password}@{host}/?retryWrites=true&w=majority"