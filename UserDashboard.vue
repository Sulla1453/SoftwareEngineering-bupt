<template>
    <div class="dashboard">
      <header>
        <div class="title">
          <h2 class="usertitle">用户控制台</h2>
          <button @click="logout">退出登录</button>
        </div>
      </header>
      <div class="content">
        <div class="sidebar">
          <ul>
            <li @click="currentView = 'bills'" :class="{ active: currentView === 'bills' }">查看充电详单</li>
            <li @click="currentView = 'request'" :class="{ active: currentView === 'request' }">提交充电请求</li>
            <li @click="currentView = 'modify'" :class="{ active: currentView === 'modify' }">修改充电数量</li>
            <li @click="currentView = 'modifyMode'" :class="{ active: currentView === 'modifyMode' }">修改充电模式</li>
            <li @click="currentView = 'queue_number'" :class="{ active: currentView === 'queue_number' }">查看本车排队号码</li>
            <li @click="currentView = 'waiting_count'" :class="{ active: currentView === 'waiting_count' }">查看前车等待数量</li>
            <li @click="currentView = 'cancel_charging'" :class="{ active: currentView === 'cancel_charging' }">取消充电</li>
            <li @click="currentView = 'end_charging'" :class="{ active: currentView === 'end_charging' }">结束充电</li>
          </ul>
        </div>
        <div class="main-content">
          <!-- 充电详单视图 -->
          <div v-if="currentView === 'bills'">
            <h3>充电详单</h3>
            <div v-if="!bills.length" class="empty-state">暂无充电记录</div>
            <div v-else>
              <div v-for="bill in bills" :key="bill.bill_id" class="bill-card">
                <p><strong>详单编号:</strong> {{ bill.bill_id }}</p>
                <p><strong>充电桩编号:</strong> {{ bill.pile_id }}</p>
                <p><strong>充电电量:</strong> {{ bill.charging_amount }}度</p>
                <p><strong>充电时长:</strong> {{ bill.charging_duration }}小时</p>
                <p><strong>开始时间:</strong> {{ formatTime(bill.start_time) }}</p>
                <p><strong>结束时间:</strong> {{ formatTime(bill.end_time) }}</p>
                <p><strong>充电费用:</strong> ¥{{ bill.charging_fee }}</p>
                <p><strong>服务费用:</strong> ¥{{ bill.service_fee }}</p>
                <p><strong>总费用:</strong> ¥{{ bill.total_fee }}</p>
              </div>
            </div>
          </div>
          <!-- 提交充电请求视图 -->
          <div v-if="currentView === 'request'">
            <h3>提交充电请求</h3>
            <div v-if="hasActiveRequest" class="alert alert-warning">
              <p><strong>注意:</strong> 您当前有活跃的充电请求，无法提交新请求。</p>
              <p>请先结束当前充电或通过修改功能调整您的请求。</p>
            </div>
            <form @submit.prevent="submitRequest">
              <div class="form-group">
                <label>充电模式:</label>
                <select v-model="requestForm.mode">
                  <option value="FAST">快充</option>
                  <option value="TRICKLE">慢充</option>
                </select>
              </div>
              <div class="form-group">
                <label>充电电量(度):</label>
                <input v-model.number="requestForm.amount" type="number" step="0.1" required />
              </div>
              <div class="form-group">
                <label>电池容量(度):</label>
                <input v-model.number="requestForm.batteryCapacity" type="number" step="0.1" />
              </div>
              <button type="submit":disabled="hasActiveRequest"
                  :class="{ 'btn-disabled': hasActiveRequest }">
            {{ hasActiveRequest ? '当前有活跃请求' : '提交请求' }}</button>
            </form>
          </div>
          <!-- 修改充电请求视图 -->
          <div v-if="currentView === 'modify'">
            <h3>修改充电请求</h3>
            <form @submit.prevent="modifyRequest">
              <div class="form-group">
                <label>新充电电量(度):</label>
                <input v-model.number="modifyForm.newAmount" type="number" step="0.1" required />
              </div>
              <button type="submit">修改请求</button>
            </form>
          </div>
          <div v-if="currentView === 'modifyMode'">
            <h3>修改充电模式</h3>
            <form @submit.prevent="modifyChargingMode">
                <div class="form-group">
                <label>新充电模式:</label>
                <select v-model="modifyForm.newMode">
                    <option value="FAST">快充</option>
                    <option value="TRICKLE">慢充</option>
                </select>
                </div>
                <button type="submit">修改模式</button>
            </form>
          </div>
          <!-- 查看本车排队号码视图 -->
          <div v-if="currentView === 'queue_number'">
            <h3>本车排队号码</h3>
            <div v-if="!queueNumber" class="empty-state">暂无排队号码</div>
            <div v-else class="info-card">
              <p><strong>排队号码:</strong> {{ queueNumber }}</p>
            </div>
            <button @click="fetchQueueNumber">刷新</button>
          </div>
          <!-- 查看前车等待数量视图 -->
          <div v-if="currentView === 'waiting_count'">
            <h3>前车等待数量</h3>
            <div v-if="waitingCount < 0" class="empty-state">获取失败</div>
            <div v-else class="info-card">
              <p><strong>前方等待车辆数量:</strong> {{ waitingCount }}</p>
            </div>
            <button @click="fetchWaitingCount">刷新</button>
          </div>
          <!-- 结束充电视图 -->
          <div v-if="currentView === 'end_charging'">
            <h3>结束充电</h3>
            <button @click="endCharging">结束充电</button>
            <div v-if="endBill" class="bill-card">
              <h4>充电账单</h4>
              <p><strong>详单编号:</strong> {{ endBill.bill_id }}</p>
              <p><strong>充电桩编号:</strong> {{ endBill.pile_id }}</p>
              <p><strong>充电电量:</strong> {{ endBill.charging_amount }}度</p>
              <p><strong>充电时长:</strong> {{ endBill.charging_duration }}小时</p>
              <p><strong>开始时间:</strong> {{ formatTime(endBill.start_time) }}</p>
              <p><strong>结束时间:</strong> {{ formatTime(endBill.end_time) }}</p>
              <p><strong>充电费用:</strong> ¥{{ endBill.charging_fee }}</p>
              <p><strong>服务费用:</strong> ¥{{ endBill.service_fee }}</p>
              <p><strong>总费用:</strong> ¥{{ endBill.total_fee }}</p>
            </div>
          </div>

          <!-- 取消充电视图 -->
          <div v-if="currentView === 'cancel_charging'">
            <h3>取消充电</h3>
            <div v-if="!hasActiveRequest" class="empty-state">
              您当前没有活跃的充电请求，无法执行取消操作。
            </div>
            <div v-else class="info-card">
              <p>您确定要取消当前的充电请求吗？</p>
              <p>取消后将退出排队，如需充电需重新提交请求。</p>
              <button @click="cancelCharging" class="btn-danger">确认取消</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </template>
  
  <script>
  export default {
    name: "UserDashboard",
    data() {
      return {
        currentView: "bills",
        user: null,
        bills: [],
        requestForm: {
          mode: "FAST",
          amount: 10,
          batteryCapacity: 70
        },
        hasActiveRequest: false,
        modifyForm: {
          newAmount: 0,
          newMode:"FAST"
        },
        queueNumber: "",
        waitingCount: -1,
        endBill: null
      };
    },
    mounted() {
      this.user = JSON.parse(localStorage.getItem("user"));
      this.fetchBills();
      this.checkActiveRequest();
    },
    methods: {
      async checkActiveRequest() {
        try {
          const response = await fetch(`http://localhost:5000/api/queue-number/${this.user.user_id}`);
          const result = await response.json();
          this.hasActiveRequest =result.queue_number;
        } catch (error) {
          console.error("检查活跃请求失败:", error);
          this.hasActiveRequest = false;
        }
      },
      async fetchBills() {
        try {
          const response = await fetch(`http://localhost:5000/api/bills/${this.user.user_id}`);
          const result = await response.json();
          if (result.success) {
            this.bills = result.bills;
          }
        } catch (error) {
          console.error("获取账单失败:", error);
        }
      },
      async submitRequest() {
        if (this.hasActiveRequest) {
          alert("您当前有活跃的充电请求，请先结束当前请求或进行修改");
          return;
        }
        try {
          const response = await fetch("http://localhost:5000/api/charging-request", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              user_id: this.user["user_id"],
              mode: this.requestForm.mode,
              amount: this.requestForm.amount,
              battery_capacity: this.requestForm.batteryCapacity
            })
          });
          const result = await response.json();
          if (result.success) {
            alert(`充电请求提交成功！排队号码: ${result.queue_number}`);
            await this.checkActiveRequest()
          } else {
            alert("提交失败: " + result.message);
          }
        } catch (error) {
          alert("网络错误: " + error.message);
        }
      },
      async modifyRequest() {
        try {
          const response = await fetch("http://localhost:5000/api/charging-amount", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              user_id: this.user.user_id,
              new_amount: this.modifyForm.newAmount
            })
          });
          const result = await response.json();
          if (result.success) {
            alert("充电请求修改成功！");
            this.fetchBills();
          } else {
            alert("修改失败: " + result.message);
          }
        } catch (error) {
          alert("网络错误: " + error.message);
        }
      },
      async modifyChargingMode() {
        try {
            const response = await fetch("http://localhost:5000/api/charging-mode", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                user_id: this.user.user_id,
                new_mode: this.modifyForm.newMode
            })
            });
            const result = await response.json();
            if (result.success) {
            alert(`充电模式修改成功！新排队号码: ${result.new_queue_number}`);
            } else {
            alert("修改失败: 请检查是否提交过请求或您的车辆正在充电" + result.message);
            }
        } catch (error) {
            alert("网络错误: " + error.message);
        }
        },
      async fetchQueueNumber() {
        try {
          const response = await fetch(`http://localhost:5000/api/queue-number/${this.user.user_id}`);
          const result = await response.json();
          if (result.success) {
            this.queueNumber = result.queue_number;
          } else {
            this.queueNumber = "";
            alert(result.message || "获取排队号码失败，您没有提交请求");
          }
        } catch (error) {
          alert("网络错误: " + error.message);
        }
      },
      async fetchWaitingCount() {
        try {
          const response = await fetch(`http://localhost:5000/api/waiting-count/${this.user.user_id}`);
          const result = await response.json();
          if (result.success) {
            this.waitingCount = result.waiting_count;
          } else {
            this.waitingCount = -1;
            alert(result.message || "获取等待数量失败，您没有提交请求");
          }
        } catch (error) {
          alert("网络错误: " + error.message);
        }
      },
      async endCharging() {
        try {
          const response = await fetch("http://localhost:5000/api/end-charging", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: this.user["user_id"] })
          });
          const result = await response.json();
          if (result.success) {
            this.endBill = result.bill;
            alert("结束充电成功！");
            this.fetchBills(); // 刷新详单
            await this.checkActiveRequest()
          } else {
            alert("结束充电失败: 没有正在进行的申请" + result.message);
          }
        } catch (error) {
          alert("网络错误: " + error.message);
        }
      },
      async cancelCharging() {
        try {
          const response = await fetch("http://localhost:5000/api/cancel-charging", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: this.user["user_id"] })
          });
          const result = await response.json();
          if (result.success) {
            alert("充电请求已成功取消！");
            // 更新状态
            this.hasActiveRequest = false;
            this.queueNumber = "";
            this.waitingCount = -1;
            // 切换到请求视图以便用户可以提交新请求
            this.currentView = 'request';
          } else {
            alert("取消充电失败: " + (result.message || "您没有活跃的充电请求或已在充电中"));
          }
        } catch (error) {
          alert("网络错误: " + error.message);
        }
      },
      formatTime(timestamp) {
        // 如果传入的是 datetime 对象直接调用 toLocaleString，否则先转换
        if (timestamp instanceof Date) return timestamp.toLocaleString();
        return new Date(timestamp).toLocaleString();
      },
      logout() {
        localStorage.removeItem("user");
        this.$router.push("/");
      }
    }
  };
  </script>
  
  <style scoped>
  /* 整体布局 */
  .dashboard {
    display: flex;
    flex-direction: column;
    height: 100vh;
    width: 100%;
    padding-top:70px;
    background-color: #f8f9fa;
  }
  header {
    flex-shrink: 0;
  }
  .title {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
    padding: 0.5rem 1rem;
    background-color: #007bff;
    color: white;
  }
  .title h2 {
    margin: 0;
    font-size: 1.8rem;
  }
  .title button {
    padding: 0.5rem 1rem;
    background-color: white;
    color: #007bff;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.2s;
  }
  .title button:hover {
    background-color: #e9ecef;
  }
  /* 内容区：侧边栏固定宽度，主要内容填充剩余空间 */
  .content {
    display: flex;
    flex: 1;
    margin-top: 60px;
  }
  .sidebar {
    width: 250px;
    background-color: #343a40;
    padding: 1rem;
    color: white;
    overflow-y: auto;
  }
  .sidebar ul {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  .sidebar li {
    padding: 0.75rem;
    cursor: pointer;
    border-bottom: 1px solid #495057;
    transition: background-color 0.3s;
  }
  .sidebar li:hover {
    background-color: #495057;
  }
  .sidebar li.active {
    background-color: #007bff;
  }
  .main-content {
    flex: 1;
    padding: 2rem;
    background-color: #fff;
    overflow-y: auto;
  }
  /* 卡片与表单样式 */
  .bill-card,
  .queue-card,
  .info-card {
    margin-bottom: 1rem;
    padding: 1rem;
    border: 1px solid #dee2e6;
    border-radius: 4px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  }
  .empty-state {
    color: #888;
    font-style: italic;
    margin-top: 1rem;
  }
  form .form-group {
    margin-bottom: 1rem;
  }
  form .form-group label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: bold;
  }
  form input,
  form select {
    width: 100%;
    padding: 0.5rem;
    border: 1px solid #dee2e6;
    border-radius: 4px;
    box-sizing: border-box;
  }

  /* 按钮样式 */
  button {
    padding: 0.75rem 1.5rem;
    background-color: #007bff;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 1rem;
    font-weight: bold;
    transition: background-color 0.2s;
    margin: 0.5rem 0;
  }

  button:hover {
    background-color: #0069d9;
  }

  button:disabled {
    background-color: #cccccc;
    cursor: not-allowed;
  }

  .btn-danger {
    background-color: #dc3545;
  }

  .btn-danger:hover {
    background-color: #c82333;
  }

  .alert {
    padding: 1rem;
    margin-bottom: 1rem;
    border-radius: 4px;
  }

  .alert-warning {
    background-color: #fff3cd;
    border: 1px solid #ffeeba;
    color: #856404;
  }
  </style>