<!-- src/components/Login.vue -->
<template>
    <div class="login-container">
      <div class="title">
        <h2 class="logintitle">充电站管理系统</h2>
      </div>
      <div class="form-container">
        <div class="tab-buttons">
          <button @click="isLogin = true" :class="{ active: isLogin }">登录</button>
          <button @click="isLogin = false" :class="{ active: !isLogin }">注册</button>
        </div>
        
        <form @submit.prevent="handleSubmit">
          <input v-model="username" placeholder="用户名" required />
          <input v-model="password" type="password" placeholder="密码" required />
          
          <div v-if="!isLogin">
            <input v-model="carType" placeholder="车辆类型" />
            <input v-model="phone" placeholder="手机号" />
          </div>
          
          <button type="submit">{{ isLogin ? '登录' : '注册' }}</button>
        </form>
        
        <div v-if="message" class="message">{{ message }}</div>
      </div>
    </div>
</template>
  
<script>
  export default {
    data() {
      return {
        isLogin: true,
        username: '',
        password: '',
        carType: '',
        phone: '',
        message: ''
      }
    },
    methods: {
      async handleSubmit() {
        try {
          const url = this.isLogin ? '/api/login' : '/api/register'
          const payload = {
            username: this.username,
            password: this.password,
            ...(this.isLogin ? {} : { car_type: this.carType, phone: this.phone })
          }
          
          const response = await fetch(`http://localhost:5000${url}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          })
          
          const result = await response.json()
          
          if (result.success) {
            const userData = this.isLogin ? result : { user_id: result.user_id, role: 'user' }
            localStorage.setItem('user', JSON.stringify(userData))
            console.log('用户数据:', userData)
            
            // 根据角色跳转
            if (userData.role === 'admin') {
              this.$router.push('/admin')
            } else {
              this.$router.push('/user')
            }
          } else {
            this.message = result.message || '操作失败'
          }
        } catch (error) {
          this.message = '网络错误: ' + error.message
        }
      }
    }
  }
</script>
<style>
.login-container {
  position: relative;
  width: 100%;
  min-height: 100vh;
  background-color: #f8f9fa;
  padding-top:200px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.title {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 140px; /* 标题栏高度 */
  padding: 1rem;
  text-align: center;
  background-color: #007bff; /* 蓝色背景 */
  color: white;
  border-radius: 0 0 10px 10px;
}


.logintitle {
  font-size: 2rem;
  color:rgb(255, 255, 255);
  margin-bottom: 1.5rem;
}


.form-container {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 400px;
}

.tab-buttons {
  display: flex;
  margin-bottom: 1rem;
}

.tab-buttons button {
  flex: 1;
  padding: 0.5rem;
  border: 1px solid #dee2e6;
  background-color: #f8f9fa;
  cursor: pointer;
  font-size: 1rem;
  font-weight: bold;
  color: #495057;
  transition: background-color 0.2s, color 0.2s;
}

.tab-buttons button.active {
  background-color:rgba(0, 123, 255, 0.87);
  color: white;
}

.tab-buttons button:hover {
  background-color: #e9ecef;
}

.form-container input {
  width: 100%;
  padding: 0.75rem;
  margin-bottom: 1rem;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  box-sizing: border-box;
  font-size: 1rem;
}

.form-container input:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 5px rgba(0, 123, 255, 0.5);
}

.form-container button[type="submit"] {
  width: 100%;
  padding: 0.75rem;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
  font-weight: bold;
  transition: background-color 0.2s;
}

.form-container button[type="submit"]:hover {
  background-color: #0056b3;
}

.message {
  margin-top: 1rem;
  padding: 0.5rem;
  border-radius: 4px;
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
  text-align: center;
}
</style>