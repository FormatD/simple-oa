<template>
  <div class="dashboard">
    <h2 class="page-title">工作台</h2>

    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">0</div>
          <div class="stat-label">待办任务</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">0</div>
          <div class="stat-label">待审批</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">0</div>
          <div class="stat-label">今日考勤</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">0</div>
          <div class="stat-label">通知</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <el-col :span="12">
        <el-card shadow="never" class="section-card">
          <template #header>
            <span>快捷操作</span>
          </template>
          <el-space wrap>
            <el-button type="primary" icon="Plus">创建任务</el-button>
            <el-button type="success" icon="Upload">打卡</el-button>
            <el-button type="warning" icon="Edit">请假申请</el-button>
            <el-button icon="DocumentAdd">新建文档</el-button>
          </el-space>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card shadow="never" class="section-card">
          <template #header>
            <span>最近动态</span>
          </template>
          <el-empty description="暂无动态" :image-size="60" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped lang="scss">
.dashboard {
  .page-title {
    margin: 0 0 20px;
    font-size: 22px;
    color: #303133;
  }

  .stats-row {
    margin-bottom: 20px;
  }

  .stat-card {
    text-align: center;
    .stat-value {
      font-size: 36px;
      font-weight: 700;
      color: #409eff;
      line-height: 1.2;
    }
    .stat-label {
      font-size: 14px;
      color: #909399;
      margin-top: 8px;
    }
  }

  .section-card {
    margin-bottom: 20px;
  }
}
</style>
