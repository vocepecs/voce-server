from flask_restful import Resource
from flask import request
import json

class TestServer(Resource):
    def get(self):
        return {
            'message' : 'Il server è online'
        }
        
    def post(self):
        data = request.get_json()
        hit_orders = json.loads(data['hit_orders'])
        
        print(f"rule_id : {data['rule_id']}")
        print(f"rule_name : {data['rule_name']}")
        print(f"@timestamp : {data['@timestamp']}")
        print(f"counts : {data['counts']}")
        print(f"order_index : {data['order_index']}")
        print(f"hit_order_sample : {hit_orders[0]}")
        return {
            'message' : 'Test succesfull'
        },200
