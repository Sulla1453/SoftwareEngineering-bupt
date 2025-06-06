from flask import Flask, request, jsonify
from flask_cors import CORS
from model_copy import ChargingStationAPI
import time

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 初始化充电站API
api = ChargingStationAPI()
api.station.init_admin_accounts()
        
# 注册一些用户
api.register_user("user1", "password1", car_type="Tesla Model 3")
api.register_user("user2", "password2", car_type="NIO ES6")
api.register_user("user3", "password3", car_type="BYD Han")

# 用户认证相关API
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    result = api.register_user(
        username=data['username'],
        password=data['password'],
        car_type=data.get('car_type', ''),
        phone=data.get('phone', '')
    )
    return jsonify(result)

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    result = api.login(data['username'], data['password'])
    return jsonify(result)

# 用户功能API
@app.route('/api/bills/<user_id>', methods=['GET'])
def get_bills(user_id):
    result = api.get_bills(user_id)
    return jsonify(result)

@app.route('/api/charging-request', methods=['POST'])
def submit_charging_request():
    data = request.get_json()
    result = api.submit_charging_request(
        user_id=data['user_id'],
        mode=data['mode'],
        amount=data['amount'],
        battery_capacity=data.get('battery_capacity')
    )
    return jsonify(result)

@app.route('/api/queue-number/<user_id>', methods=['GET'])
def get_queue_number(user_id):
    result = api.get_queue_number(user_id)
    return jsonify(result)

@app.route('/api/waiting-count/<user_id>', methods=['GET'])
def get_waiting_count(user_id):
    result = api.get_waiting_count(user_id)
    return jsonify(result)

@app.route('/api/charging-amount', methods=['PUT'])
def modify_charging_amount():
    data = request.get_json()
    result = api.modify_charging_amount(data['user_id'], data['new_amount'])
    return jsonify(result)

@app.route('/api/charging-mode', methods=['PUT'])
def modify_charging_mode():
    data = request.get_json()
    result = api.modify_charging_mode(data['user_id'], data['new_mode'])
    return jsonify(result)

@app.route('/api/end-charging', methods=['POST'])
def end_charging():
    data = request.get_json()
    result = api.end_charging(data['user_id'])
    return jsonify(result)

# 管理员功能API
@app.route('/api/admin/pile-status', methods=['GET'])
def get_pile_status():
    pile_id = request.args.get('pile_id')
    result = api.get_pile_status(pile_id)
    return jsonify(result)

@app.route('/api/admin/pile-status', methods=['PUT'])
def set_pile_status():
    data = request.get_json()
    result = api.set_pile_status(data['pile_id'], data['status'])
    return jsonify(result)

@app.route('/api/admin/pile-queue-cars', methods=['GET'])
def get_pile_queue_cars():
    pile_id = request.args.get('pile_id')
    result = api.get_pile_queue_cars(pile_id)
    return jsonify(result)

@app.route('/api/admin/report', methods=['POST'])
def generate_report():
    data = request.get_json()
    result = api.generate_report(
        start_time=data['start_time'],
        end_time=data['end_time'],
        period=data.get('period', 'day')
    )
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=5000)