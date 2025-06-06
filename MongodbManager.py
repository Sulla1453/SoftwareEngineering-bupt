from pymongo import MongoClient
from datetime import datetime, timedelta
import uuid
import bcrypt

class MongoDBManager:
    def __init__(self, connection_string="mongodb://localhost:27017/", db_name="SE"):
        self.client = MongoClient(connection_string)
        self.db = self.client[db_name]
        self.users_collection = self.db.users
        self.bills_collection = self.db.bills
        
        # 创建索引
        self.users_collection.create_index("username", unique=True)
        self.users_collection.create_index("user_id", unique=True)
    def register_user(self, user_info: dict) -> dict:# 需要username password car_type phone
        """注册用户到MongoDB"""
        try:
            # 生成用户ID
            user_id = str(uuid.uuid4())
            
            # 密码加密
            hashed_password = bcrypt.hashpw(user_info["password"].encode('utf-8'), bcrypt.gensalt())
            
            # 构建用户文档
            user_doc = {
                "user_id": user_id,
                "username": user_info["username"],
                "password": hashed_password,
                "role": user_info.get("role", "user"),
                "car_type": user_info.get("car_type", ""),
                "phone": user_info.get("phone", ""),
                "created_at": datetime.now()
            }
            
            # 插入用户
            self.users_collection.insert_one(user_doc)
            return {"success": True, "user_id": user_id}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
        
    def register_admin(self, user_info: dict) -> dict:# 需要username password car_type phone
        """注册管理员到MongoDB"""
        try:
            # 生成用户ID
            user_id = str(uuid.uuid4())
            
            # 密码加密
            hashed_password = bcrypt.hashpw(user_info["password"].encode('utf-8'), bcrypt.gensalt())
            
            # 构建用户文档
            user_doc = {
                "user_id": user_id,
                "username": user_info["username"],
                "password": hashed_password,
                "role": user_info.get("role", "admin"),
                "car_type": user_info.get("car_type", ""),
                "phone": user_info.get("phone", ""),
                "created_at": datetime.now()
            }
            
            # 插入用户
            self.users_collection.insert_one(user_doc)
            return {"success": True, "user_id": user_id}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    def login(self,username:str,password:str)->dict:
        """用户登录验证"""
        try:
            # 查找用户
            user = self.users_collection.find_one({"username": username})
            if not user:
                return {"success": False, "error": "用户不存在"}
            
            # 验证密码
            if bcrypt.checkpw(password.encode('utf-8'), user["password"]):
                return {
                    "success": True,
                    "user_id": user["user_id"],
                    "username": user["username"],
                    "role": user["role"]
                }
            else:
                return {"success": False, "error": "密码错误"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    def get_user_by_id(self, user_id: str) -> dict:# {success:xx,{info}}
        """根据用户ID获取用户信息"""
        try:
            user = self.users_collection.find_one({"user_id": user_id})
            if user:
                # 不返回密码
                user.pop("password", None)
                user.pop("_id", None)
                return {"success": True, "user": user}
            return {"success": False, "error": "用户不存在"}
        except Exception as e:
            return {"success": False, "error": str(e)}
        
    def save_bill(self, bill: dict) -> bool:
        """保存账单到MongoDB"""
        try:
            self.bills_collection.insert_one(bill)
            return True
        except Exception as e:
            print(f"保存账单失败: {e}")
            return False
    
    def get_user_bills(self, user_id: str) -> list:
        """获取用户账单"""
        try:
            bills = list(self.bills_collection.find({"user_id": user_id}, {"_id": 0}))
            return bills
        except Exception as e:
            print(f"获取账单失败: {e}")
            return []
    def get_all_bills(self) -> list:
        """获取所有账单"""
        try:
            bills = list(self.bills_collection.find({}))
            return bills
        except Exception as e:
            print(f"获取所有账单失败: {e}")
            return []