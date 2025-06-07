from enum import Enum
from datetime import datetime, time as dtime, timedelta
import time
from typing import Dict, List, Optional, Tuple, Union
import uuid
import threading
import json
import heapq


class Config:
    # 充电桩数量配置
    FAST_CHARGING_PILE_NUM = 2  # 快充电桩数量
    TRICKLE_CHARGING_PILE_NUM = 3  # 慢充电桩数量

    # 等候区和充电队列配置
    WAITING_AREA_SIZE = 6  # 等候区最大车位容量
    CHARGING_QUEUE_LEN = 2  # 充电桩排队队列长度

    # 充电功率配置(度/小时)
    FAST_CHARGING_POWER = 30  # 快充功率
    TRICKLE_CHARGING_POWER = 7  # 慢充功率
    
    # 费率配置
    SERVICE_FEE_RATE = 0.8  # 服务费单价(元/度)
    PEAK_PRICE = 1.0  # 峰时电价(元/度)
    FLAT_PRICE = 0.7  # 平时电价(元/度)
    VALLEY_PRICE = 0.4  # 谷时电价(元/度)

class CHARGING_MODE(Enum):
    FAST = "F"  # 快充模式
    TRICKLE = "T"  # 慢充模式

class PILE_STATUS(Enum):
    AVAILABLE = 0  # 可用状态
    CHARGING = 1  # 充电中状态
    FAULT = 2  # 故障状态
    OFF = 3  # 断开状态



class TIME_PERIOD:
    def __init__(self, timestamp):
        # 支持传入datetime对象或时间戳
        if isinstance(timestamp, datetime):
            self.current_time = timestamp
        else:
            self.current_time = datetime.fromtimestamp(timestamp)

    def is_peak_time(self):
        return(
            dtime(10, 0) <= self.current_time.time() < dtime(15, 0) or
            dtime(18, 0) <= self.current_time.time() < dtime(21, 0)
        )
    def is_valley_time(self):
        return(
            dtime(23, 0) <= self.current_time.time() or
            self.current_time.time() <= dtime(7, 0)
        )
    def is_flat_time(self):
        return(
            dtime(7, 0) <= self.current_time.time() < dtime(10, 0) or
            dtime(15, 0) <= self.current_time.time() < dtime(18, 0) or
            dtime(21, 0) <= self.current_time.time() < dtime(23, 0)
        )
    
    def get_period(self):
        if self.is_peak_time():
            return "PEAK"
        elif self.is_valley_time():
            return "VALLEY"
        elif self.is_flat_time():
            return "FLAT"
        else:
            return "UNKNOWN"
        
    def calculate_time_period(self, start_time: datetime, end_time: datetime):
        peak_duration = timedelta(0)
        valley_duration = timedelta(0)
        flat_duration = timedelta(0)

        current_time = start_time

        while current_time < end_time:
            # 修改这里：直接传入datetime对象
            period = TIME_PERIOD(current_time).get_period()
            next_minute = current_time + timedelta(minutes=1)

            minute_duration = min(next_minute, end_time) - current_time
            
            if period == "PEAK":
                peak_duration += minute_duration
            elif period == "VALLEY":
                valley_duration += minute_duration
            elif period == "FLAT":
                flat_duration += minute_duration

            current_time = next_minute

        return peak_duration, valley_duration, flat_duration
    

class ChargingPile:
    """充电桩类"""

    def __init__(self, pile_id: str, mode: CHARGING_MODE):
        self.pile_id = pile_id # 充电桩ID
        self.mode = mode # 充电模式
        self.status = PILE_STATUS.AVAILABLE # 充电桩状态
        self.power = Config.FAST_CHARGING_POWER if mode == CHARGING_MODE.FAST else Config.TRICKLE_CHARGING_POWER # 充电功率
        self.queue = [] # 排队队列
        self.charging_vehicle = None # 当前充电车辆

#    数据统计
        self.total_charging_times = 0 # 总充电次数
        self.total_charging_duration = 0 # 总充电时长
        self.total_charging_amount = 0 # 总充电量

    def is_queue_full(self):
        """判断队列是否已满"""
        return len(self.queue) >= Config.CHARGING_QUEUE_LEN - 1 # 减1是因为当前充电位不算在队列中
    
    def is_queue_empty(self):
        """判断队列是否为空"""
        return len(self.queue) == 0 and not self.charging_vehicle
    
    def add_to_queue(self, user_id: str, queue_number: str, request: dict) -> bool:
        """添加车辆到队列"""
        if self.is_queue_full():
            return False
        
        # 若队列为空且当前没有车在充电，直接加入排队队列 
        if self.is_queue_empty() and self.status == PILE_STATUS.AVAILABLE:
            self.charging_vehicle = (user_id, queue_number, request, time.time())
            self.status = PILE_STATUS.CHARGING
        # 否则加入排队队列
        else :
            self.queue.append((user_id, queue_number, request))
        
        return True
    
    def remove_from_queue(self, user_id: str, queue_number: str) -> bool:
        """从队列中移除车辆"""
        if self.charging_vehicle and self.charging_vehicle[0] == user_id and self.charging_vehicle[1] == queue_number:
            self.finish_charging()
            return True
        
        for i, (uid, qn, _) in enumerate(self.queue):
            if uid == user_id and qn == queue_number:
                self.queue.pop(i)
                return True
            
        return False

    
    def finish_charging(self) -> Optional[dict]:
        """结束当前充电过程，生成详单，并从队列中移动下一个车辆到充电状态"""
        if not self.charging_vehicle:
            return None
        
        user_id, queue_number, request_data, start_time = self.charging_vehicle
        end_time = time.time()
        charging_duration = (end_time - start_time) / 3600  # 转换为小时
        
        # 计算实际充电量（可能小于等于请求量）
        real_charging_amount = min(request_data["amount"], charging_duration * self.power)
        real_charging_duration = real_charging_amount / self.power
        
        # 更新统计数据
        self.total_charging_times += 1
        self.total_charging_duration += real_charging_duration
        self.total_charging_amount += real_charging_amount
        
        # 生成详单
        bill = self._generate_bill(
            user_id, 
            start_time, 
            start_time + real_charging_duration * 3600,  # 实际结束时间
            real_charging_amount, 
            real_charging_duration,
            queue_number
        )
        
        # 清空当前充电车辆
        self.charging_vehicle = None
        
        # 如果队列不为空，将下一个车辆移到充电位
        if self.queue and self.status == PILE_STATUS.AVAILABLE:
            self.charging_vehicle = (*self.queue.pop(0), time.time())
            self.status = PILE_STATUS.CHARGING
        elif not self.queue:
            self.status = PILE_STATUS.AVAILABLE
            
        return bill
    
    def start_next_charging(self) -> bool:
        """开始下一个排队的车辆的充电"""
        if self.charging_vehicle or not self.queue or self.status != PILE_STATUS.AVAILABLE:
            return False
        
        # 若队列中还有车，则将下一个车辆移动到充电状态
        if self.queue :
            self.charging_vehicle = (*self.queue.pop(0) , time.time())
            self.status = PILE_STATUS.CHARGING
        else:
            self.status = PILE_STATUS.AVAILABLE
            # todo request_add_queue()
        return True
    
    
    def generate_bill(self, user_id: str, start_time: float, end_time: float,
                       charging_amount: float, charging_duration: float, queue_number: str,) -> dict:
        """生成账单"""
        start_time = datetime.fromtimestamp(start_time)
        end_time = datetime.fromtimestamp(end_time)

        # 获取各时间段持续时间（分钟）
        time_calculator = TIME_PERIOD(start_time)

        peak_duration, valley_duration, flat_duration = time_calculator.calculate_time_period(start_time, end_time)
        # 总时长（分钟）
        total_minutes = peak_duration + valley_duration + flat_duration

        # 按占比划分总电量
        peak_amount = charging_amount * (peak_duration / total_minutes)
        valley_amount = charging_amount * (valley_duration / total_minutes)
        flat_amount = charging_amount * (flat_duration / total_minutes)
        
        # 分别计算电价
        charging_fee = (
            peak_amount * Config.PEAK_PRICE +
            valley_amount * Config.VALLEY_PRICE +
            flat_amount * Config.FLAT_PRICE
        )
        service_fee = charging_amount * Config.SERVICE_FEE_RATE
        
        bill = {
            "bill_id": str(uuid.uuid4()),
            "user_id": user_id,
            "queue_number": queue_number,
            "generated_time": time.time(),
            "pile_id":self.pile_id,
            "charging_amount": charging_amount,
            "charging_duration": charging_duration,
            "start_time": start_time,
            "end_time": end_time,
            "charging_fee": charging_fee,
            "service_fee": service_fee,
            "total_fee": charging_fee + service_fee,
        }

        return bill
    
    
    def set_status(self, status: PILE_STATUS) -> None:
        old_status = self.status
        self.status = status

        if old_status == PILE_STATUS.FAULT and status == PILE_STATUS.AVAILABLE:
            if  not self.charging_vehicle and self.queue:
                self.start_next_charging()
        
        if status == PILE_STATUS.FAULT and self.charging_vehicle:
            return self.finish_charging()

    def get_charging_time_estimate(self, amount: float) -> float:
        """估算充电时间"""
        return amount / self.power    
    
    def get_waiting_time_estimate(self) -> float:
        """估算排队时间"""
        waiting_time = 0

        if self.charging_vehicle:
            user_id,queue_number,request_data,start_time = self.charging_vehicle
            elapsed_time = (time.time() - start_time) / 3600 # 已充电时间（小时）
            total_time = request_data["amount"] / self.power # 总充电时间（小时）
            remainning_time = max(total_time - elapsed_time, 0) # 剩余充电时间（小时）
            waiting_time += remainning_time

        for _, _, request_data in self.queue:
            waiting_time += request_data["amount"] / self.power # 排队时间（小时）

        return waiting_time

    def get_queue_cars_info(self) -> List[dict]:
        """获取排队车辆信息"""
        result = []
        
        # 添加当前充电车辆信息
        if self.charging_vehicle:
            user_id, queue_number, request_data, start_time = self.charging_vehicle
            result.append({
                "user_id": user_id,
                "queue_number": queue_number,
                "battery_capacity": request_data.get("battery_capacity", 0),
                "request_amount": request_data["amount"],
                "queue_time": time.time() - start_time
            })

        for user_id, queue_number, request_data in self.queue:
            queue_time = time.time() - request_data.get("queue_start_time", time.time())
            result.append({
                "user_id": user_id,
                "queue_number": queue_number,
                "battery_capacity": request_data.get("battery_capacity", 0),
                "request_amount": request_data["amount"],
                "queue_time": queue_time
            })
        
        return result
    
    def get_status_info(self) -> dict:
        """获取充电桩状态信息"""
        return {
            "pile_id": self.pile_id,
            "mode": self.mode.value,
            "status": self.status.name,
            "total_charging_times": self.total_charging_times,
            "total_charging_duration": self.total_charging_duration,
            "total_charging_amount": self.total_charging_amount,
            "queue_length": len(self.queue) + (1 if self.charging_vehicle else 0),
            "charging_vehicle": self.charging_vehicle[1] if self.charging_vehicle else None,
        }

class chargingStation:
    """充电站类"""

    def __init__(self):
        self.piles = {} 
        self._init_charging_piles()

        self.waiting_area = {
            CHARGING_MODE.FAST: [], # 快充等候区
            CHARGING_MODE.TRICKLE: [], # 慢充等候区
        }

        # 排队号码计数器
        self.queue_counter = {
            CHARGING_MODE.FAST: 1,
            CHARGING_MODE.TRICKLE: 1,
        }
        
        # 详单记录
        self.bills = {} # 用户ID -> [详单列表]
        
        # 用户信息
        self.users = {} # 用户ID -> 用户信息

        # 线程锁
        self.lock = threading.RLock()

        # 标记等候区叫号服务是否暂停
        self.call_number_paused = False

        # 调度线程
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()

        # 标记等候区叫号服务是否暂停
        self.call_number_paused = False

    def _init_charging_piles(self):
        """初始化充电桩"""
        # 初始化快充电桩
        for i in range(Config.FAST_CHARGING_PILE_NUM):
            pile_id = chr(ord('A') + i)
            self.piles[pile_id] = ChargingPile(pile_id, CHARGING_MODE.FAST)

        # 初始化慢充电桩
        offset = Config.FAST_CHARGING_PILE_NUM
        for i in range(Config.TRICKLE_CHARGING_PILE_NUM):
            pile_id = chr(ord('A') + offset + i)
            self.piles[pile_id] = ChargingPile(pile_id, CHARGING_MODE.TRICKLE)

    def register_user(self, user_info: dict) -> dict:
        """注册用户"""
        with self.lock:
            user_id = str(uuid.uuid4())
            self.users[user_id] = user_info
            self.bills[user_id] = []
            return {"user_id": user_id}

    def login(self, username: str, password: str) -> Optional[dict]:
        """用户登录"""
        with self.lock:
            for user_id, user_info in self.users.items():
                if user_info["password"] == password and user_info["username"] == username:
                   return user_id
            return None

    def submit_charging_request(self, user_id: str, mode: CHARGING_MODE, amount: float,
                                 battery_capacity: Optional[float] = None) -> Optional[dict]:
        """提交充电请求"""
        with self.lock:
            # 检查用户是否存在
            if user_id not in self.users:
                return None
            
            # 检查等候区是否已满
            if sum(len(queue) for queue in self.waiting_area.values()) >= Config.WAITING_AREA_SIZE:
                return None
            
            # 生成排队号码
            queue_number = f"{mode.value}{self.queue_counter[mode]}"
            self.queue_counter[mode] += 1
            
            # 生成请求数据
            request_data = {
                "mode": mode,
                "amount": amount,
                "battery_capacity": battery_capacity,
                "queue_start_time": time.time()
            }
            
            # 加入等候区
            self.waiting_area[mode].append((user_id, queue_number, request_data))
            
            return {"queue_number": queue_number}
    def get_queue_number(self, user_id: str) -> Optional[str]:
        """获取用户的排队号码"""
        with self.lock:
            # 检查用户是否在等候区
            for mode in self.waiting_area:
                for u_id, queue_number, _ in self.waiting_area[mode]:
                    if u_id == user_id:
                        return queue_number

            # 检查用户是否在充电区
            for pile_id, pile in self.piles.items():
                if pile.charging_vehicle and pile.charging_vehicle[0] == user_id:
                    return pile.charging_vehicle[1]
            
                for u_id, queue_number, _ in pile.queue:
                    if u_id == user_id:
                        return queue_number
            
            return None

    def get_waiting_count(self, user_id: str) -> int:
        """获取该模式下前车等待数量"""
        with self.lock:
            queue_number = self.get_queue_number(user_id)
            if not queue_number:
                return -1
            
            mode = CHARGING_MODE.FAST if queue_number.startswith("F") else CHARGING_MODE.TRICKLE
            count = 0

            # 计算前车等待数量
            for u_id, q_number, _ in self.waiting_area[mode]:
                if q_number == queue_number:
                    break
                count += 1
            return count
        
    def modify_charging_mode(self, user_id: str, new_mode: CHARGING_MODE) -> Optional[str]:
        """修改充电模式"""
        with self.lock:
            # 在等候区修改
            found = False
            old_queue_number = None
            
            for mode in self.waiting_area:
                for i, (u_id, queue_number, _) in enumerate(self.waiting_area[mode]):
                    if u_id == user_id:
                        # 删除旧请求
                        old_queue_number = queue_number
                        request_data = self.waiting_area[mode].pop(i)[2]
                        found = True
                        break
                
                if found:
                    break
            
            if found:
                # 更新请求模式
                request_data["mode"] = new_mode
                
                # 生成新排队号码
                new_queue_number = f"{new_mode.value}{self.queue_counter[new_mode]}"
                self.queue_counter[new_mode] += 1
                
                # 添加到新模式的等候区末尾
                self.waiting_area[new_mode].append((user_id, new_queue_number, request_data))
                
                return new_queue_number
            
            return None  # 用户不在等候区
            
    def modify_charging_amount(self, user_id: str, new_amount: float) -> bool:
        """修改充电量"""
        with self.lock:
            #在等待区修改
            for mode in self.waiting_area:
                for i, (u_id, queue_number, request_data) in enumerate(self.waiting_area[mode]):
                    if u_id == user_id:
                        # 更新充电量
                        request_data["amount"] = new_amount
                        self.waiting_area[mode][i] = (u_id, queue_number, request_data)
                        return True
                    
            return False

    def cancel_charging(self, user_id: str) -> bool:
        """取消充电"""
        with self.lock:
            # 检查用户是否在等候区
            for mode in self.waiting_area:
                for i, (u_id, _, _) in enumerate(self.waiting_area[mode]):
                    if u_id == user_id:
                        self.waiting_area[mode].pop(i)
                        return True
            
            # 检查用户是否在充电区
            for pile_id, pile in self.piles.items():
                if pile.remove_from_queue(user_id, self.get_queue_number(user_id)):
                    return True
            
            return False

    def end_charging(self, user_id: str) -> Optional[dict]:
        """结束充电"""
        with self.lock:
            queue_number = self.get_queue_number(user_id)
            if not queue_number:
                return None
            
            # 查找用户在哪个充电桩
            for pile_id, pile in self.piles.items():
                if pile.charging_vehicle and pile.charging_vehicle[0] == user_id:
                    bill = pile.finish_charging()

                    # 记录账单
                    if bill:
                        if user_id not in self.bills:
                            self.bills[user_id] = []
                        self.bills[user_id].append(bill)

                    return bill
                
            return None
        
    def get_bills(self, user_id: str) -> List[dict]:
        """获取用户的账单"""
        with self.lock:
            return self.bills.get(user_id, [])
        
    def set_pile_status(self, pile_id: str, status: PILE_STATUS) -> Optional[dict]:
        """设置充电桩状态"""
        with self.lock:
            if pile_id not in self.piles:
                return None
            
            bill = self.piles[pile_id].set_status(status)
            
            # 如果充电桩状态变为故障，需要处理故障队列
            if status == PILE_STATUS.FAULT:
                self._handle_pile_fault(pile_id)
            # 如果充电桩状态从故障恢复，需要重新调度
            elif self.piles[pile_id].status == PILE_STATUS.AVAILABLE and status == PILE_STATUS.AVAILABLE:
                self._handle_pile_recovery(pile_id)
            
            # 保存详单
            if bill:
                user_id = bill["user_id"]
                if user_id not in self.bills:
                    self.bills[user_id] = []
                self.bills[user_id].append(bill)
            
            return bill
    
    def get_pile_status(self, pile_id: Optional[str] = None) -> Union[dict, List[dict]]:
        """获取充电桩状态"""
        with self.lock:
            if pile_id:
                if pile_id in self.piles:
                    return self.piles[pile_id].get_status_info()
                return None
            
            # 返回所有充电桩状态
            return [pile.get_status_info() for pile in self.piles.values()]
    
    def get_pile_queue_cars(self, pile_id: Optional[str] = None) -> Union[List[dict], Dict[str, List[dict]]]:
        """获取充电桩排队车辆信息"""
        with self.lock:
            if pile_id:
                if pile_id in self.piles:
                    return self.piles[pile_id].get_queue_cars_info()
                return []
            
            # 返回所有充电桩排队车辆信息
            result = {}
            for p_id, pile in self.piles.items():
                result[p_id] = pile.get_queue_cars_info()
            return result
    
    def generate_report(self, start_time: float, end_time: float, period: str = "day") -> List[dict]:
        """生成报表"""
        with self.lock:
            # 筛选时间范围内的详单
            period_bills = []
            for user_bills in self.bills.values():
                for bill in user_bills:
                    if start_time <= bill["start_time"] <= end_time:
                        period_bills.append(bill)
            
            # 按照充电桩分组统计
            pile_stats = {}
            for bill in period_bills:
                pile_id = bill["pile_id"]
                if pile_id not in pile_stats:
                    pile_stats[pile_id] = {
                        "total_times": 0,
                        "total_duration": 0,
                        "total_amount": 0,
                        "total_charging_fee": 0,
                        "total_service_fee": 0,
                        "total_fee": 0
                    }
                
                pile_stats[pile_id]["total_times"] += 1
                pile_stats[pile_id]["total_duration"] += bill["charging_duration"]
                pile_stats[pile_id]["total_amount"] += bill["charging_amount"]
                pile_stats[pile_id]["total_charging_fee"] += bill["charging_fee"]
                pile_stats[pile_id]["total_service_fee"] += bill["service_fee"]
                pile_stats[pile_id]["total_fee"] += bill["total_fee"]
            
            # 生成报表
            report = [] 
            for pile_id, stats in pile_stats.items():
                report.append({
                    "time_period": period,
                    "pile_id": pile_id,
                    "total_charging_times": stats["total_times"],
                    "total_charging_duration": stats["total_duration"],
                    "total_charging_amount": stats["total_amount"],
                    "total_charging_fee": stats["total_charging_fee"],
                    "total_service_fee": stats["total_service_fee"],
                    "total_fee": stats["total_fee"]
                })
            
            return report
    
    def _scheduler_loop(self):
        """调度循环"""
        while True:
            try:
                with self.lock:
                    if not self.call_number_paused:
                        self._schedule_vehicles()
                
                # 每秒调度一次
                time.sleep(1)
            except Exception as e:
                print(f"Scheduling error: {e}")
                time.sleep(5)  # 出错时等待5秒再继续
    
    def _schedule_vehicles(self):
        """调度车辆进入充电区"""
        # 检查每个充电桩是否有空位
        for pile_id, pile in self.piles.items():
            if pile.status != PILE_STATUS.AVAILABLE or pile.is_queue_full():
                continue
            
            mode = pile.mode
            
            # 如果相应模式的等候区有车辆，进行调度
            if self.waiting_area[mode]:
                # 从等候区取出第一辆车
                user_id, queue_number, request_data = self.waiting_area[mode].pop(0)
                
                # 查找最适合的充电桩（完成充电所需时长最短）
                best_pile = None
                min_completion_time = float('inf')
                
                for p_id, p in self.piles.items():
                    if p.mode == mode and p.status == PILE_STATUS.AVAILABLE and not p.is_queue_full():
                        # 计算等待时间
                        waiting_time = p.get_waiting_time_estimate()
                        # 计算自己充电时间
                        charging_time = p.get_charging_time_estimate(request_data["amount"])
                        # 总完成时间
                        completion_time = waiting_time + charging_time
                        
                        if completion_time < min_completion_time:
                            min_completion_time = completion_time
                            best_pile = p_id
                
                if best_pile:
                    # 将车辆添加到充电桩队列
                    self.piles[best_pile].add_to_queue(user_id, queue_number, request_data)
    
    def _handle_pile_fault(self, fault_pile_id: str):
        """处理充电桩故障"""
        # 暂停等候区叫号服务
        self.call_number_paused = True
        
        fault_pile = self.piles[fault_pile_id]
        mode = fault_pile.mode
        
        # 优先级调度：将故障充电桩的等候队列车辆重新调度
        if fault_pile.queue:
            fault_queue = fault_pile.queue.copy()
            fault_pile.queue = []  # 清空故障充电桩队列
            
            # 按照策略选择处理方式：1为优先级调度，2为时间顺序调度
            strategy = 1  # 可配置
            
            if strategy == 1:  # 优先级调度
                # 首先尝试调度故障队列中的车辆
                for user_id, queue_number, request_data in fault_queue:
                    self._schedule_fault_vehicle(user_id, queue_number, request_data, mode)
            
            elif strategy == 2:  # 时间顺序调度
                # 收集所有同类型充电桩中尚未充电的车辆
                all_waiting_vehicles = []
                
                # 加入故障充电桩的排队车辆
                for user_id, queue_number, request_data in fault_queue:
                    all_waiting_vehicles.append((user_id, queue_number, request_data))
                
                # 收集其他同类型充电桩中尚未充电的车辆
                for p_id, p in self.piles.items():
                    if p_id != fault_pile_id and p.mode == mode:
                        for user_id, queue_number, request_data in p.queue:
                            all_waiting_vehicles.append((user_id, queue_number, request_data))
                        # 清空其他充电桩队列
                        p.queue = []
                
                # 按照排队号码排序（先来先到）
                all_waiting_vehicles.sort(key=lambda x: int(x[1][1:]))  # 排除首字母，按数字排序
                
                # 按顺序重新调度
                for user_id, queue_number, request_data in all_waiting_vehicles:
                    self._schedule_fault_vehicle(user_id, queue_number, request_data, mode)
        
        # 重新开启等候区叫号服务
        self.call_number_paused = False
    
    def _handle_pile_recovery(self, recovered_pile_id: str):
        """处理充电桩恢复"""
        # 暂停等候区叫号服务
        self.call_number_paused = True
        
        recovered_pile = self.piles[recovered_pile_id]
        mode = recovered_pile.mode
        
        # 检查其他同类型充电桩是否有车辆排队
        has_waiting_vehicles = False
        for p_id, p in self.piles.items():
            if p_id != recovered_pile_id and p.mode == mode and p.queue:
                has_waiting_vehicles = True
                break
        
        if has_waiting_vehicles:
            # 收集所有同类型充电桩中尚未充电的车辆
            all_waiting_vehicles = []
            
            # 收集所有同类型充电桩中尚未充电的车辆
            for p_id, p in self.piles.items():
                if p.mode == mode:
                    for user_id, queue_number, request_data in p.queue:
                        all_waiting_vehicles.append((user_id, queue_number, request_data))
                    # 清空充电桩队列
                    p.queue = []
            
            # 按照排队号码排序（先来先到）
            all_waiting_vehicles.sort(key=lambda x: int(x[1][1:]))  # 排除首字母，按数字排序
            
            # 按顺序重新调度
            for user_id, queue_number, request_data in all_waiting_vehicles:
                self._schedule_fault_vehicle(user_id, queue_number, request_data, mode)
        
        # 重新开启等候区叫号服务
        self.call_number_paused = False
    
    def _schedule_fault_vehicle(self, user_id: str, queue_number: str, request_data: dict, mode: CHARGING_MODE):
        """调度故障车辆到其他充电桩"""
        # 查找最适合的充电桩（完成充电所需时长最短）
        best_pile = None
        min_completion_time = float('inf')
        
        for p_id, p in self.piles.items():
            if p.mode == mode and p.status == PILE_STATUS.AVAILABLE and not p.is_queue_full():
                # 计算等待时间
                waiting_time = p.get_waiting_time_estimate()
                # 计算自己充电时间
                charging_time = p.get_charging_time_estimate(request_data["amount"])
                # 总完成时间
                completion_time = waiting_time + charging_time
                
                if completion_time < min_completion_time:
                    min_completion_time = completion_time
                    best_pile = p_id
        
        if best_pile:
            # 将车辆添加到充电桩队列
            self.piles[best_pile].add_to_queue(user_id, queue_number, request_data)
        else:
            # 如果没有合适的充电桩，将车辆放回等候区
            self.waiting_area[mode].insert(0, (user_id, queue_number, request_data))
    
    def batch_schedule_vehicles(self, mode: CHARGING_MODE) -> bool:
        """扩展功能：单次调度总充电时长最短"""
        with self.lock:
            # 检查该模式下有多少个空位
            available_slots = 0
            available_piles = []
            for pile_id, pile in self.piles.items():
                if pile.mode == mode and pile.status == PILE_STATUS.AVAILABLE:
                    # 每个充电桩可用的空位数
                    available_space = Config.CHARGING_QUEUE_LEN - len(pile.queue) - (1 if pile.charging_vehicle else 0)
                    if available_space > 0:
                        available_slots += available_space
                        available_piles.append((pile_id, available_space))
            
            # 如果没有空位，返回
            if available_slots == 0:
                return False
            
            # 取等候区该模式下的车辆，最多取available_slots个
            waiting_vehicles = self.waiting_area[mode][:available_slots]
            if not waiting_vehicles:
                return False
            
            # 从等候区移除这些车辆
            self.waiting_area[mode] = self.waiting_area[mode][len(waiting_vehicles):]
            
            # 计算所有可能的分配方案，找出总充电时长最短的方案
            best_assignment = self._find_optimal_assignment(waiting_vehicles, available_piles)
            
            # 执行最优分配方案
            if best_assignment:
                for pile_id, assigned_vehicles in best_assignment.items():
                    for user_id, queue_number, request_data in assigned_vehicles:
                        self.piles[pile_id].add_to_queue(user_id, queue_number, request_data)
                return True
            
            # 如果没有找到合适的方案，将车辆放回等候区
            self.waiting_area[mode] = waiting_vehicles + self.waiting_area[mode]
            return False
    
    def _find_optimal_assignment(self, vehicles, available_piles):
        """寻找最优分配方案"""
        # 这是一个复杂的组合优化问题，使用简化的贪心算法
        # 实际应用中可能需要使用更复杂的算法如匈牙利算法或线性规划
        
        if not vehicles or not available_piles:
            return {}
        
        # 将车辆按照充电量排序（从大到小）
        vehicles.sort(key=lambda x: x[2]["amount"], reverse=True)
        
        # 将充电桩按照当前负载排序（从小到大）
        available_piles.sort(key=lambda x: self.piles[x[0]].get_waiting_time_estimate())
        
        # 贪心分配：将每辆车分配到当前负载最小的合适充电桩
        assignment = {pile_id: [] for pile_id, _ in available_piles}
        pile_loads = {pile_id: self.piles[pile_id].get_waiting_time_estimate() for pile_id, _ in available_piles}
        pile_spaces = {pile_id: space for pile_id, space in available_piles}
        
        for vehicle in vehicles:
            user_id, queue_number, request_data = vehicle
            mode = request_data["mode"]
            
            # 寻找负载最小且还有空间的充电桩
            best_pile = None
            min_load = float('inf')
            
            for pile_id in pile_loads:
                if pile_spaces[pile_id] > 0 and self.piles[pile_id].mode == mode:
                    if pile_loads[pile_id] < min_load:
                        min_load = pile_loads[pile_id]
                        best_pile = pile_id
            
            if best_pile:
                # 分配车辆到充电桩
                assignment[best_pile].append(vehicle)
                # 更新充电桩负载和空间
                pile_loads[best_pile] += self.piles[best_pile].get_charging_time_estimate(request_data["amount"])
                pile_spaces[best_pile] -= 1
        
        return assignment
    
    def batch_schedule_all_vehicles(self) -> bool:
        """扩展功能：批量调度总充电时长最短"""
        with self.lock:
            # # 计算充电区总车位数
            # total_slots = sum(Config.CHARGING_QUEUE_LEN for _ in self.piles)
            available_piles = [
                (pile_id, Config.CHARGING_QUEUE_LEN - len(pile.queue) - (1 if pile.charging_vehicle else 0)) 
                for pile_id, pile in self.piles.items()
                if pile.status == PILE_STATUS.AVAILABLE
            ]
            total_slots = sum(space for _, space in available_piles)
            # 收集所有等候区车辆
            all_vehicles = []
            for mode in self.waiting_area:
                all_vehicles.extend(self.waiting_area[mode])
            
            # 如果车辆数量不足，返回
            if len(all_vehicles) < total_slots:
                return False
            
            # 取前total_slots个车辆
            selected_vehicles = all_vehicles[:total_slots]
            
            # 从等候区移除这些车辆
            for mode in self.waiting_area:
                self.waiting_area[mode] = []
            
            remaining_vehicles = all_vehicles[total_slots:]
            for user_id, queue_number, request_data in remaining_vehicles:
                self.waiting_area[request_data["mode"]].append((user_id, queue_number, request_data))
            
            # 计算所有可能的分配方案，找出总充电时长最短的方案
            best_assignment = self._find_optimal_assignment_all(selected_vehicles)
            
            # 执行最优分配方案
            if best_assignment:
                for pile_id, assigned_vehicles in best_assignment.items():
                    for user_id, queue_number, request_data in assigned_vehicles:
                        self.piles[pile_id].add_to_queue(user_id, queue_number, request_data)
                return True
            
            # 如果没有找到合适的方案，将车辆放回等候区
            for user_id, queue_number, request_data in selected_vehicles:
                self.waiting_area[request_data["mode"]].append((user_id, queue_number, request_data))
            return False
    
    def _find_optimal_assignment_all(self, vehicles):
        """寻找最优全局分配方案（忽略充电模式限制）"""
        # 这是一个更复杂的组合优化问题，使用简化的贪心算法
        
        if not vehicles:
            return {}
        
        # 将车辆按照充电量排序（从大到小）
        vehicles.sort(key=lambda x: x[2]["amount"], reverse=True)
        
        # 将所有充电桩纳入考虑
        available_piles = [(pile_id, Config.CHARGING_QUEUE_LEN - len(pile.queue) - (1 if pile.charging_vehicle else 0)) 
                          for pile_id, pile in self.piles.items() if pile.status == PILE_STATUS.AVAILABLE]
        
        # 将充电桩按照当前负载排序（从小到大）
        available_piles.sort(key=lambda x: self.piles[x[0]].get_waiting_time_estimate())
        
        # 贪心分配：将每辆车分配到当前负载最小的充电桩
        assignment = {pile_id: [] for pile_id, _ in available_piles}
        pile_loads = {pile_id: self.piles[pile_id].get_waiting_time_estimate() for pile_id, _ in available_piles}
        pile_spaces = {pile_id: space for pile_id, space in available_piles}
        
        for vehicle in vehicles:
            user_id, queue_number, request_data = vehicle
            
            # 计算在不同充电桩上的充电时间
            charging_times = {}
            for pile_id, pile in self.piles.items():
                if pile_id in pile_spaces and pile_spaces[pile_id] > 0:
                    # 充电时间 = 充电量 / 充电功率
                    charging_time = request_data["amount"] / pile.power
                    charging_times[pile_id] = charging_time
            
            # 寻找总完成时间最短的充电桩
            best_pile = None
            min_completion_time = float('inf')
            
            for pile_id, charging_time in charging_times.items():
                if pile_spaces[pile_id] > 0:
                    completion_time = pile_loads[pile_id] + charging_time
                    if completion_time < min_completion_time:
                        min_completion_time = completion_time
                        best_pile = pile_id
            
            if best_pile:
                # 分配车辆到充电桩
                assignment[best_pile].append(vehicle)
                # 更新充电桩负载和空间
                pile_loads[best_pile] += charging_times[best_pile]
                pile_spaces[best_pile] -= 1
        
        return assignment


# API服务
class ChargingStationAPI:
    """充电站API服务"""
    
    def __init__(self):
        self.station = chargingStation()
    
    # 用户相关API
    def register_user(self, username: str, password: str, **kwargs) -> dict:
        """注册用户"""
        user_info = {
            "username": username,
            "password": password,
            **kwargs
        }
        return self.station.register_user(user_info)
    
    def login(self, username: str, password: str) -> dict:
        """用户登录"""
        user_id = self.station.login(username, password)
        if user_id:
            return {"success": True, "user_id": user_id}
        return {"success": False, "message": "用户名或密码错误"}
    
    def submit_charging_request(self, user_id: str, mode: str, amount: float, battery_capacity: Optional[float] = None) -> dict:
        """提交充电请求"""
        charging_mode = CHARGING_MODE.FAST if mode.upper() == "FAST" else CHARGING_MODE.TRICKLE
        queue_number = self.station.submit_charging_request(user_id, charging_mode, amount, battery_capacity)
        if queue_number:
            return {"success": True, "queue_number": queue_number}
        return {"success": False, "message": "提交充电请求失败"}
    
    def get_queue_number(self, user_id: str) -> dict:
        """获取排队号码"""
        queue_number = self.station.get_queue_number(user_id)
        if queue_number:
            return {"success": True, "queue_number": queue_number}
        return {"success": False, "message": "未找到排队号码"}
    
    def get_waiting_count(self, user_id: str) -> dict:
        """获取前车等待数量"""
        count = self.station.get_waiting_count(user_id)
        if count >= 0:
            return {"success": True, "waiting_count": count}
        return {"success": False, "message": "查询失败"}
    
    def modify_charging_mode(self, user_id: str, new_mode: str) -> dict:
        """修改充电模式"""
        charging_mode = CHARGING_MODE.FAST if new_mode.upper() == "FAST" else CHARGING_MODE.TRICKLE
        new_queue_number = self.station.modify_charging_mode(user_id, charging_mode)
        if new_queue_number:
            return {"success": True, "new_queue_number": new_queue_number}
        return {"success": False, "message": "修改充电模式失败"}
    
    def modify_charging_amount(self, user_id: str, new_amount: float) -> dict:
        """修改请求充电量"""
        success = self.station.modify_charging_amount(user_id, new_amount)
        if success:
            return {"success": True}
        return {"success": False, "message": "修改充电量失败"}
    
    def cancel_charging(self, user_id: str) -> dict:
        """取消充电"""
        success = self.station.cancel_charging(user_id)
        if success:
            return {"success": True}
        return {"success": False, "message": "取消充电失败"}
    
    def end_charging(self, user_id: str) -> dict:
        """结束充电"""
        bill = self.station.end_charging(user_id)
        if bill:
            return {"success": True, "bill": bill}
        return {"success": False, "message": "结束充电失败"}
    
    def get_bills(self, user_id: str) -> dict:
        """获取充电详单"""
        bills = self.station.get_bills(user_id)
        return {"success": True, "bills": bills}
    
    # 管理员相关API
    def set_pile_status(self, pile_id: str, status: str) -> dict:
        """设置充电桩状态"""
        pile_status = {
            "available": PILE_STATUS.AVAILABLE,
            "fault": PILE_STATUS.FAULT,
            "off": PILE_STATUS.OFF
        }.get(status.lower())
        
        if not pile_status:
            return {"success": False, "message": "无效的状态值"}
        
        bill = self.station.set_pile_status(pile_id, pile_status)
        return {"success": True, "bill": bill if bill else None}
    
    def get_pile_status(self, pile_id: Optional[str] = None) -> dict:
        """获取充电桩状态"""
        status = self.station.get_pile_status(pile_id)
        return {"success": True, "status": status}
    
    def get_pile_queue_cars(self, pile_id: Optional[str] = None) -> dict:
        """获取充电桩排队车辆信息"""
        cars = self.station.get_pile_queue_cars(pile_id)
        return {"success": True, "cars": cars}
    
    def generate_report(self, start_time: float, end_time: float, period: str = "day") -> dict:
        """生成报表"""
        report = self.station.generate_report(start_time, end_time, period)
        return {"success": True, "report": report}
    
    # 扩展调度API
    def batch_schedule_vehicles(self, mode: str) -> dict:
        """单次调度总充电时长最短"""
        charging_mode = CHARGING_MODE.FAST if mode.upper() == "FAST" else CHARGING_MODE.TRICKLE
        success = self.station.batch_schedule_vehicles(charging_mode)
        if success:
            return {"success": True}
        return {"success": False, "message": "批量调度失败"}
    
    def batch_schedule_all_vehicles(self) -> dict:
        """批量调度总充电时长最短"""
        success = self.station.batch_schedule_all_vehicles()
        if success:
            return {"success": True}
        return {"success": False, "message": "全局批量调度失败"}


# 创建一个示例应用
def create_example_application():
    """创建示例应用并初始化一些数据"""
    api = ChargingStationAPI()
    
    # 注册一些用户
    api.register_user("user1", "password1", car_type="Tesla Model 3")
    api.register_user("user2", "password2", car_type="NIO ES6")
    api.register_user("user3", "password3", car_type="BYD Han")
    
    # 登录
    user1 = api.login("user1", "password1")["user_id"]
    user2 = api.login("user2", "password2")["user_id"]
    user3 = api.login("user3", "password3")["user_id"]
    
    # 提交充电请求
    api.submit_charging_request(user1, "FAST", 30.0, 70.0)
    api.submit_charging_request(user2, "TRICKLE", 20.0, 60.0)
    api.submit_charging_request(user3, "FAST", 25.0, 65.0)
    
    return api

def complex_test(api):
    print("\n====== [样例1] 注册用户并登录 ======")
    u1 = api.register_user("u1", "123")["user_id"]
    u2 = api.register_user("u2", "123")["user_id"]
    u3 = api.register_user("u3", "123")["user_id"]
    print("注册成功：", u1, u2, u3)

    u1 = api.login("u1", "123")["user_id"]
    u2 = api.login("u2", "123")["user_id"]
    u3 = api.login("u3", "123")["user_id"]
    print("登录成功：", u1, u2, u3)

    print("\n====== [样例2] 提交充电请求 ======")
    print(api.submit_charging_request(u1, "FAST", 30.0))
    print(api.submit_charging_request(u2, "FAST", 25.0))
    print(api.submit_charging_request(u3, "TRICKLE", 15.0))

    print("\n====== [样例3] 修改u2为慢充模式 ======")
    print(api.modify_charging_mode(u2, "TRICKLE"))

    print("\n====== [样例4] 模拟部分调度运行后充电桩A故障 ======")
    import time as systime
    systime.sleep(3)  # 等待调度线程运行
    print(api.set_pile_status("A", "fault"))
    print("=== 当前桩状态 ===")
    for pile_id, pile in api.station.piles.items():
        print(f"{pile_id}: {pile.status.name}, queue_len={len(pile.queue)}, charging={pile.charging_vehicle is not None}")
        print(f"  {pile.queue}")
    print("\n====== [样例5] 批量调度测试（20个用户） ======")
    user_ids = []
    for i in range(20):
        uid = api.register_user(f"user{i+20}", "pwd")["user_id"]
        mode = "FAST" if i % 2 == 0 else "TRICKLE"
        api.submit_charging_request(uid, mode, 20 + i)
        user_ids.append(uid)

    print("批量调度结果：", api.batch_schedule_all_vehicles())

    print("\n====== [样例6] 修改u3充电量 ======")
    print("u3 当前排队号码：", api.get_queue_number(u3))
    api.submit_charging_request(u3, "TRICKLE", 15.0)
    print(api.modify_charging_amount(u3, 40.0))

    print("\n====== [样例7] 取消u3的充电请求 ======")
    print(api.cancel_charging(u3))

    print("\n====== [样例8] 显示充电桩状态 ======")
    print(json.dumps(api.get_pile_status(), indent=2))

    print("\n====== [样例9] 显示各桩排队车辆信息 ======")
    print(json.dumps(api.get_pile_queue_cars(), indent=2))

    print("\n====== [样例10] 跨时间段计费验证（23:30~01:30） ======")
    from datetime import datetime, timedelta
    start = datetime.strptime("2025-06-01 23:30", "%Y-%m-%d %H:%M")
    end = start + timedelta(hours=2)
    t_calc = TIME_PERIOD(start)
    peak, valley, flat = t_calc.calculate_time_period(start, end)
    print(f"峰：{peak}, 谷：{valley}, 平：{flat}")


# 测试代码
# if __name__ == "__main__":
#     api = create_example_application()
    
#     # 获取充电桩状态
#     print(json.dumps(api.get_pile_status(), indent=2))
    
#     # 模拟时间流逝（系统会自动调度车辆进入充电区）
#     print("等待调度...")
#     time.sleep(3)
    
#     # 获取充电桩队列
#     print(json.dumps(api.get_pile_queue_cars(), indent=2))
    
#     # 模拟故障
#     print("模拟充电桩A故障...")
#     api.set_pile_status("A", "fault")
    
#     # 再次获取充电桩状态
#     print(json.dumps(api.get_pile_status(), indent=2))
    
#     # 测试批量调度
#     print("测试批量调度...")
#     api.batch_schedule_vehicles("FAST")
    
#     print("系统运行完成")
    
if __name__ == "__main__":
    api = ChargingStationAPI()
    complex_test(api)
