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
# u1=api.login("user1", "password1")
# u2=api.login("user2", "password2")
# u3=api.login("user3", "password3")

# # 测试 提交申请
# print(api.submit_charging_request(u1["user_id"], "FAST", 50, battery_capacity=75))
# api.submit_charging_request(u2["user_id"], "FAST", 30, battery_capacity=60)
# api.submit_charging_request(u3["user_id"], "FAST", 40, battery_capacity=50)
# time.sleep(3)
# print(api.get_pile_queue_cars("A"))
# print(api.get_pile_queue_cars("B"))0

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
    print("前端请求数据:", data)
    result = api.submit_charging_request(
        user_id=data['user_id'],
        mode=data['mode'],
        amount=data['amount'],
        battery_capacity=data.get('battery_capacity')
    )
    return jsonify(result)

@app.route('/api/queue-number/<user_id>', methods=['GET'])
def get_queue_number(user_id):
    # 基本的队列号码信息
    result = api.get_queue_number(user_id)

    # 如果找到队列号码，添加更多详细信息
    if result.get("success") and result.get("queue_number"):
        queue_number = result["queue_number"]
        user_id_str = user_id

        # 检查用户是否在充电桩充电或排队
        for pile_id, pile in api.station.piles.items():
            # 检查是否正在充电
            if pile.charging_vehicle and pile.charging_vehicle[0] == user_id_str:
                # 用户正在充电桩充电
                result["position"] = "charging"
                result["pile_id"] = pile_id
                break

            # 检查是否在充电桩排队
            for i, (queue_user_id, _, _) in enumerate(pile.queue):
                if queue_user_id == user_id_str:
                    # 用户在充电桩队列中等待
                    result["position"] = "queuing"
                    result["pile_id"] = pile_id
                    result["queue_position"] = i + 1  # 队列中的位置（从1开始）
                    break

        # 如果不在充电桩，那么就在等候区
        if "position" not in result:
            for mode in api.station.waiting_area:
                for i, (waiting_user_id, _, _) in enumerate(api.station.waiting_area[mode]):
                    if waiting_user_id == user_id_str:
                        # 用户在等候区等待
                        result["position"] = "waiting_area"
                        result["waiting_position"] = i + 1  # 等候区的位置（从1开始）
                        break

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
    print(result)
    return jsonify(result)

@app.route('/api/cancel-charging', methods=['POST'])
def cancel_charging():
    data = request.get_json()
    result = api.cancel_charging(data['user_id'])
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

    # 获取充电桩车辆信息
    pile_result = api.get_pile_queue_cars(pile_id)

    # 获取等待区车辆信息
    waiting_result = api.station.get_waiting_area_info()

    # 构建结果，保持原有的充电桩数据结构
    result = {
        "success": pile_result["success"],
        "cars": pile_result["cars"],
        "waiting_area": waiting_result
    }

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