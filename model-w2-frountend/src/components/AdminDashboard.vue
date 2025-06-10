<!-- src/components/AdminDashboard.vue -->
<template>
  <div class="dashboard">
    <header>
      <div class="title">
          <h2 class="Usertitle">管理员控制台</h2>
          <button @click="logout">退出登录</button>
      </div>
    </header>
    
    <div class="content">
      <div class="sidebar">
        <ul>
          <li @click="selectPilesView"  :class="{ active: currentView === 'piles' }">
            充电桩管理
          </li>
          <li @click="selectQueueView" :class="{ active: currentView === 'queue' }">
            排队车辆信息
          </li>
          <li @click="selectReportView" :class="{ active: currentView === 'report' }">
            报表统计
          </li>
        </ul>
      </div>
      
      <div class="main-content">
        <!-- 充电桩管理 -->
        <div v-if="currentView === 'piles'">
          <h3>充电桩状态管理</h3>
          <div class="pile-grid">
            <div v-for="pile in pileStatus" :key="pile.pile_id" class="pile-card">
              <h4>充电桩 {{ pile.pile_id }}</h4>
              <p><strong>类型:</strong> {{ pile.mode }}</p>
              <p><strong>状态:</strong> {{ pile.status }}</p>
              <p><strong>正在充电车辆:</strong> {{ pile.charging_vehicle }}</p>
              <p><strong>排队长度:</strong>{{ pile.queue_length }}</p>
              <p><strong>充电次数:</strong> {{ pile.total_charging_times }}</p>
              <p><strong>总时长:</strong> {{ pile.total_charging_duration }}小时</p>
              <p><strong>总电量:</strong> {{ pile.total_charging_amount }}度</p>
              
              <div class="controls">
                <button @click="setPileStatus(pile.pile_id, 'available')" 
                        :disabled="pile.status === 'available'">
                  启动
                </button>
                <button @click="setPileStatus(pile.pile_id, 'off')"
                        :disabled="pile.status === 'off'">
                  关闭
                </button>
                <button @click="setPileStatus(pile.pile_id, 'fault')"
                        :disabled="pile.status === 'fault'">
                  故障
                </button>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 排队车辆信息 -->
        <div v-if="currentView === 'queue'">
        <h3>等候车辆信息</h3>
        <div class="queue-controls">
          <label>选择充电桩:</label>
          <select v-model="selectedPileId" @change="fetchQueueCars">
            <!-- <option value="">全部充电桩</option> -->
            <option v-for="pile in pileStatus" :key="pile.pile_id" :value="pile.pile_id">
              {{ pile.pile_id }}
            </option>
          </select>
          <button @click="fetchQueueCars">刷新</button>
        </div>

        <div v-if="queueCars.length === 0" class="empty-state">
          暂无排队车辆
        </div>
        <div v-else>
          <div v-for="car in queueCars" :key="car.user_id + '_' + (car.pile_id || car.queue_number)" class="queue-card">
            <div class="car-status" :class="{
              'status-charging': car.status === 'charging',
              'status-queuing': car.status === 'queuing_at_pile',
              'status-waiting': car.status === 'waiting_area'
            }">
              {{ car.status === 'charging' ? '正在充电' : 
                 car.status === 'queuing_at_pile' ? '排队中' : '等候区' }}
              {{ car.mode ? `(${car.mode === 'FAST' || car.mode === 'F' ? '快充' : '慢充'})` : '' }}
            </div>
            <p><strong>用户ID:</strong> {{ car.user_id }}</p>
            <p v-if="car.pile_id"><strong>充电桩:</strong> {{ car.pile_id }}</p>
            <p><strong>电池容量:</strong> {{ car.battery_capacity }}度</p>
            <p><strong>请求电量:</strong> {{ car.request_amount }}度</p>
            <p><strong>排队时长:</strong> {{ Math.floor(car.queue_time / 60) }}分钟</p>
          </div>
        </div>
      </div>
        
        <!-- 报表统计 -->
        <div v-if="currentView === 'report'">
          <h3>报表统计</h3>
          <div class="report-controls">
            <select v-model="reportPeriod">
              <option value="day">按天</option>
              <option value="week">按周</option>
              <option value="month">按月</option>
            </select>
            <button @click="generateReport">生成报表</button>
          </div>
          
          <div v-if="reportData.length > 0" class="report-table">
            <table>
              <thead>
                <tr>
                  <th>充电桩编号</th>
                  <th>充电次数</th>
                  <th>充电时长(小时)</th>
                  <th>充电电量(度)</th>
                  <th>充电费用(元)</th>
                  <th>服务费用(元)</th>
                  <th>总费用(元)</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in reportData" :key="item.pile_id">
                  <td>{{ item.pile_id }}</td>
                  <td>{{ item.total_charging_times }}</td>
                  <td>{{ item.total_charging_duration }}</td>
                  <td>{{ item.total_charging_amount }}</td>
                  <td>{{ item.total_charging_fee }}</td>
                  <td>{{ item.total_service_fee }}</td>
                  <td>{{ item.total_fee }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      currentView: 'piles',
      pileStatus: [],
      queueCars: [],
      reportData: [],
      reportPeriod: 'day',
      selectedPileId: '',
      start_report_time:""
    }
  },
  mounted() {
    this.fetchPileStatus()
  },
  methods: {
    selectPilesView() {
      this.currentView = 'piles'
      this.fetchPileStatus()
    },
    selectQueueView() {
      this.currentView = 'queue'
      this.fetchQueueCars()
    },
    selectReportView() {
      this.currentView = 'report'
      this.generateReport()
    },
    async fetchPileStatus() {
      try {
        const response = await fetch('http://localhost:5000/api/admin/get-pile-status')
        const result = await response.json()
        if (result.success) {
          this.pileStatus = Array.isArray(result.status) ? result.status : [result.status]
        }
      } catch (error) {
        console.error('获取充电桩状态失败:', error)
      }
    },
    async fetchQueueCars() {
      try {
        let url = 'http://localhost:5000/api/admin/pile-queue-cars'
        if (this.selectedPileId) {
          url += `?pile_id=${this.selectedPileId}`
        }

        const response = await fetch(url)
        const result = await response.json()
        if (result.success) {
          // 合并充电桩队列和等候区的车辆
          let allCars = result.cars || [];
          
          // 如果有等候区数据，将其添加到队列中
          if (result.waiting_area && typeof result.waiting_area === 'object') {
            // 遍历等候区数据（快充和慢充）
            for (const mode in result.waiting_area) {
              if (Array.isArray(result.waiting_area[mode])) {
                // 对每个等候区车辆添加标识
                const waitingCars = result.waiting_area[mode].map(car => ({
                  ...car,
                  status: "waiting_area",
                  mode: mode // 添加充电模式
                }));
                allCars = allCars.concat(waitingCars);
              }
            }
          }
          
          this.queueCars = allCars;
        } else {
          console.log('获取排队车辆信息:', result.message)
          this.queueCars = []
        }
      } catch (error) {
        console.error('获取排队车辆失败:', error)
        this.queueCars = []
      }
    },
    
    async setPileStatus(pileId, status) {
      try {
        const response = await fetch('http://localhost:5000/api/admin/set-pile-status', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          
          body: JSON.stringify({ pile_id: pileId, status })
        })
        const result = await response.json()
        if (result.success) {
          this.fetchPileStatus() // 刷新状态
          alert('充电桩状态更新成功')
        } else {
          alert('更新失败: ' + result.message)
        }
      } catch (error) {
        console.log('网络错误: ' + error)
      }
    },
    
    async generateReport() {
      try {
        const now = Date.now() / 1000
        const oneDayAgo = now - 86400
        const oneWeekAgo = now - 604800
        const oneMonthAgo = now - 2592000
        if (this.reportPeriod === 'day') {
          this.start_report_time = oneDayAgo
        } else if (this.reportPeriod === 'week') {
          this.start_report_time = oneWeekAgo
        } else if (this.reportPeriod === 'month') {
          this.start_report_time = oneMonthAgo
        }
        
        const response = await fetch('http://localhost:5000/api/admin/report', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            start_time: this.start_report_time,
            end_time: now,
            period: this.reportPeriod
          })
        })
        
        const result = await response.json()
        if (result.success) {
          this.reportData = result.report
        }
      } catch (error) {
        console.error('生成报表失败:', error)
      }
    },
    
    logout() {
      console.log('管理员退出登录')
      localStorage.removeItem('admin')
      this.$router.push('/')
      window.location.href = '/'
    }
  }
}
</script>

<style scoped>
/* 整体布局 */
.dashboard {
display: flex;
flex-direction: column;
height: 100vh;
width: 100%;
padding-top: 70px;
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
background-color: #28a745; /* 改为绿色主题 */
color: white;
}

.title h2 {
margin: 0;
font-size: 1.8rem;
}

.title button {
padding: 0.5rem 1rem;
background-color: white;
color: #28a745; /* 改为绿色 */
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
width: 280px;
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
background-color: #28a745; /* 改为绿色 */
}

.main-content {
flex: 1;
padding: 2rem;
background-color: #fff;
overflow-y: auto;
}

/* 卡片与表单样式 */
.pile-card,
.report-card,
.status-card {
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

/* 表单样式 */
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

form button {
padding: 0.75rem 1.5rem;
background-color: #28a745; /* 改为绿色 */
color: white;
border: none;
border-radius: 4px;
cursor: pointer;
font-size: 1rem;
font-weight: bold;
transition: background-color 0.2s;
}

form button:hover {
background-color: #218838; /* 绿色悬停效果 */
}

/* 状态指示器 */
.status-indicator {
display: inline-block;
padding: 0.25rem 0.5rem;
border-radius: 12px;
font-size: 0.8rem;
font-weight: bold;
}

.status-available {
background-color: #d4edda;
color: #155724;
}

.status-charging {
background-color: #fff3cd;
color: #856404;
}

.status-fault {
background-color: #f8d7da;
color: #721c24;
}

.status-off {
background-color: #e2e3e5;
color: #6c757d;
}

/* 数据表格样式 */
.data-table {
width: 100%;
border-collapse: collapse;
margin-top: 1rem;
}

.data-table th,
.data-table td {
padding: 0.75rem;
text-align: left;
border-bottom: 1px solid #dee2e6;
}

.data-table th {
background-color: #f8f9fa;
font-weight: bold;
}

/* 统计卡片样式 */
.stats-grid {
display: grid;
grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
gap: 1rem;
margin-bottom: 2rem;
}

.stat-card {
background: white;
padding: 1.5rem;
border-radius: 8px;
box-shadow: 0 2px 4px rgba(0,0,0,0.1);
text-align: center;
}

.stat-value {
font-size: 2rem;
font-weight: bold;
color: #28a745; /* 改为绿色 */
}

.stat-label {
color: #6c757d;
margin-top: 0.5rem;
}

.queue-controls {
margin-bottom: 1rem;
padding: 1rem;
background-color: #f8f9fa;
border-radius: 4px;
display: flex;
align-items: center;
gap: 1rem;
}

.queue-controls label {
font-weight: bold;
}

.queue-controls select {
padding: 0.5rem;
border: 1px solid #dee2e6;
border-radius: 4px;
}

.queue-controls button {
padding: 0.5rem 1rem;
background-color: #28a745;
color: white;
border: none;
border-radius: 4px;
cursor: pointer;
}

.queue-controls button:hover {
background-color: #218838;
}

.queue-card {
margin-bottom: 1rem;
padding: 1rem;
border: 1px solid #dee2e6;
border-radius: 4px;
box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.car-status {
display: inline-block;
padding: 0.25rem 0.5rem;
border-radius: 12px;
margin-bottom: 0.5rem;
font-weight: bold;
font-size: 0.9rem;
}

.status-charging {
background-color: #d4edda;
color: #155724;
}

.status-queuing {
background-color: #fff3cd;
color: #856404;
}

.status-waiting {
background-color: #f8d7da;
color: #721c24;
}

.report-table {
width: 100%;
border-collapse: collapse;
}

.report-table thead {
background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
color: white;
}

.report-table th {
padding: 1rem;
text-align: left;
font-weight: 600;
letter-spacing: 0.5px;
}

.report-table td {
padding: 1rem;
border-bottom: 1px solid #e9ecef;
transition: background-color 0.2s;
}

.report-table tbody tr:hover {
background-color: #f8f9fa;
}

.report-table tbody tr:last-child td {
border-bottom: none;
}
</style>