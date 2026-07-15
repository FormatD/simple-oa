<template>
  <el-container class="main-layout">
    <!-- Sidebar -->
    <el-aside :width="isCollapsed ? '64px' : '240px'" class="sidebar">
      <div class="sidebar-header">
        <span v-if="!isCollapsed" class="logo-text">企业管理</span>
        <el-icon v-else :size="24"><HomeFilled /></el-icon>
      </div>

      <el-menu
        :default-active="currentRoute"
        :collapse="isCollapsed"
        :router="true"
        background-color="#001529"
        text-color="#ffffffb3"
        active-text-color="#ffffff"
        class="sidebar-menu"
      >
        <el-menu-item index="/dashboard">
          <el-icon><Odometer /></el-icon>
          <template #title>工作台</template>
        </el-menu-item>

        <el-sub-menu index="organization">
          <template #title>
            <el-icon><OfficeBuilding /></el-icon>
            <span>组织管理</span>
          </template>
          <el-menu-item index="/organizations">
            <el-icon><Management /></el-icon>
            <template #title>组织设置</template>
          </el-menu-item>
          <el-menu-item index="/organizations/departments">
            <el-icon><Share /></el-icon>
            <template #title>部门管理</template>
          </el-menu-item>
        </el-sub-menu>

        <el-sub-menu index="hr">
          <template #title>
            <el-icon><UserFilled /></el-icon>
            <span>人力资源</span>
          </template>
          <el-menu-item index="/hr/employees">
            <el-icon><Avatar /></el-icon>
            <template #title>员工管理</template>
          </el-menu-item>
          <el-menu-item index="/hr/attendance">
            <el-icon><Clock /></el-icon>
            <template #title>考勤管理</template>
          </el-menu-item>
          <el-menu-item index="/hr/leave">
            <el-icon><Tickets /></el-icon>
            <template #title>请假管理</template>
          </el-menu-item>
        </el-sub-menu>

        <!-- Team Collaboration -->
        <el-sub-menu index="collaboration">
          <template #title>
            <el-icon><List /></el-icon>
            <span>团队协作</span>
          </template>
          <el-menu-item index="/tasks">
            <el-icon><List /></el-icon>
            <template #title>任务管理</template>
          </el-menu-item>
          <el-menu-item index="/wiki">
            <el-icon><Notebook /></el-icon>
            <template #title>知识库</template>
          </el-menu-item>
          <el-menu-item index="/audit-logs">
            <el-icon><View /></el-icon>
            <template #title>审计日志</template>
          </el-menu-item>
        </el-sub-menu>

        </el-sub-menu>

        <el-sub-menu index="stage4">
          <template #title>
            <el-icon><DataAnalysis /></el-icon>
            <span>扩展功能</span>
          </template>
          <el-menu-item index="/imports">
            <el-icon><Upload /></el-icon>
            <template #title>数据导入</template>
          </el-menu-item>
          <el-menu-item index="/reports">
            <el-icon><DataAnalysis /></el-icon>
            <template #title>报表中心</template>
          </el-menu-item>
          <el-menu-item index="/training">
            <el-icon><Reading /></el-icon>
            <template #title>培训管理</template>
          </el-menu-item>
          <el-menu-item index="/benefits">
            <el-icon><Present /></el-icon>
            <template #title>福利管理</template>
          </el-menu-item>
          <el-menu-item index="/onboarding">
            <el-icon><UserFilled /></el-icon>
            <template #title>入职/离职</template>
          </el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-aside>

    <el-container>
      <!-- Navbar -->
      <el-header class="navbar">
        <div class="navbar-left">
          <el-icon
            :size="20"
            class="collapse-btn"
            @click="isCollapsed = !isCollapsed"
          >
            <Fold v-if="!isCollapsed" />
            <Expand v-else />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/dashboard' }">
              首页
            </el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentRoute !== '/dashboard'">
              {{ routeName }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="navbar-right">
          <!-- Notification Center -->
          <NotificationCenter />

          <el-dropdown trigger="click" @command="handleUserCommand">
            <span class="user-dropdown">
              <el-avatar :size="32" icon="UserFilled" />
              <span class="username">{{ authStore.user?.display_name || "用户" }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon>个人信息
                </el-dropdown-item>
                <el-dropdown-item command="settings">
                  <el-icon><Setting /></el-icon>设置
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- Main Content -->
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import { useRoute, useRouter } from "vue-router"
import { useAuthStore } from "@/stores/authStore"
import { useNotificationStore } from "@/stores/notificationStore"
import NotificationCenter from "@/components/notification/NotificationCenter.vue"

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const notificationStore = useNotificationStore()

const isCollapsed = ref(false)
const currentRoute = computed(() => route.path)
const routeName = computed(() => {
  const name = route.name
  if (typeof name === "string") return name
  return ""
})

function handleUserCommand(command: string) {
  if (command === "logout") {
    authStore.logout()
    router.push("/login")
  }
}

onMounted(() => {
  // Connect WebSocket for real-time notifications when logged in
  if (authStore.isLoggedIn && authStore.accessToken) {
    setTimeout(() => {
      notificationStore.connectWebSocket(authStore.accessToken!)
    }, 1000)
  }
})
</script>

<style scoped lang="scss">
.main-layout {
  height: 100vh;
}

.sidebar {
  background-color: #001529;
  transition: width 0.3s;
  overflow: hidden;

  .sidebar-header {
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 18px;
    font-weight: 600;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  }

  .sidebar-menu {
    border-right: none;
  }
}

.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 20px;
  height: 60px;

  .navbar-left {
    display: flex;
    align-items: center;
    gap: 16px;

    .collapse-btn {
      cursor: pointer;
      color: #606266;
      &:hover {
        color: #409eff;
      }
    }
  }

  .navbar-right {
    display: flex;
    align-items: center;
    gap: 20px;

    .user-dropdown {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      .username {
        font-size: 14px;
        color: #303133;
      }
    }
  }
}

.main-content {
  background-color: #f5f7fa;
  padding: 20px;
  overflow-y: auto;
}
</style>
