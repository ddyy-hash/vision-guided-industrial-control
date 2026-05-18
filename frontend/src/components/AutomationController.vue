<template>
  <div class="automation-control">
    <h3>自定义机械臂动作序列</h3>

    <div class="sequence-editor">
      <div class="sequence-list">
        <div class="sequence-list-header">
          <h4>预设序列</h4>
          <el-button
            type="primary"
            size="small"
            @click="createNewSequence"
            class="new-sequence-btn"
          >
            <el-icon><Plus /></el-icon> 新建序列
          </el-button>
        </div>
        <div
          v-for="(sequence, index) in sequences"
          :key="index"
          class="sequence-item"
          :class="{ active: activeSequenceIndex === index }"
          @click="selectSequence(index)"
        >
          <h4>
            {{ sequence.name }}
            <span>{{ sequence.steps.length }} 步</span>
          </h4>
          <div class="steps">
            <ol>
              <li v-for="(step, stepIndex) in sequence.steps" :key="stepIndex">
                {{ step.name }} ({{ step.duration }}ms)
                <div class="step-actions-list">
                  <div v-for="(action, actionIndex) in step.actions" :key="actionIndex">
                    <span class="action-tag">关节{{ action.jointId }} → {{ action.angle }}°</span>
                  </div>
                </div>
              </li>
            </ol>
          </div>
          <div class="actions">
            <el-button size="small" @click.stop="runSequence(sequence)">执行</el-button>
            <el-button size="small" type="primary" @click.stop="applySequenceToPipeline(sequence)">
              应用到流水线
            </el-button>
            <el-button size="small" type="danger" @click.stop="deleteSequence(index)">删除</el-button>
          </div>
        </div>
      </div>

      <div class="sequence-config">
        <div class="form-row">
          <label>序列名称</label>
          <el-input v-model="currentSequence.name" placeholder="输入序列名称" />
        </div>

        <div class="step-list">
          <h4>动作步骤</h4>
          <div v-for="(step, index) in currentSequence.steps" :key="index" class="step-item">
            <div class="step-info">
              <div>{{ step.name }}</div>
              <div style="font-size: 12px; color: #90a4ae;">
                <span v-for="(action, actionIndex) in step.actions" :key="actionIndex" class="action-tag">
                  关节{{ action.jointId }} → {{ action.angle }}°
                </span>
                <div>{{ step.duration }}ms</div>
              </div>
            </div>
            <div class="step-actions">
              <el-button size="small" @click="editStep(index)">编辑</el-button>
              <el-button size="small" type="danger" @click="removeStep(index)">删除</el-button>
            </div>
          </div>

          <div v-if="currentSequence.steps.length === 0" class="empty-steps">
            <el-icon><InfoFilled /></el-icon>
            暂无步骤，请添加动作步骤
          </div>
        </div>

        <div class="step-form">
          <h4>{{ editingStepIndex === null ? '添加新步骤' : '编辑步骤' }}</h4>
          <div class="form-row">
            <label>步骤名称</label>
            <el-input v-model="newStep.name" placeholder="例如: 移动到取料位置" />
          </div>

          <div class="form-row">
            <label>持续时间 (ms)</label>
            <el-slider v-model="newStep.duration" :min="500" :max="5000" :step="100" show-input />
          </div>

          <div class="actions-list">
            <div class="actions-header">
              <h5>舵机动作</h5>
              <el-button type="primary" size="small" @click="addAction">
                <el-icon><Plus /></el-icon> 添加舵机
              </el-button>
            </div>

            <div v-for="(action, index) in newStep.actions" :key="index" class="action-item">
              <div class="action-controls">
                <el-select v-model="action.jointId" placeholder="选择关节" size="small">
                  <el-option label="夹爪 (关节1)" :value="1" />
                  <el-option label="关节3" :value="3" />
                  <el-option label="关节4" :value="4" />
                  <el-option label="关节5" :value="5" />
                  <el-option label="关节6" :value="6" />
                </el-select>

                <el-input-number
                  v-model="action.angle"
                  :min="0"
                  :max="180"
                  :step="1"
                  size="small"
                />

                <el-button
                  type="danger"
                  size="small"
                  circle
                  @click="removeAction(index)"
                >
                  <el-icon><Close /></el-icon>
                </el-button>
              </div>
            </div>

            <div v-if="newStep.actions.length === 0" class="no-actions">
              <el-icon><Warning /></el-icon>
              请至少添加一个舵机动作
            </div>
          </div>

          <div class="form-row actions">
            <el-button type="primary" @click="addStep">
              {{ editingStepIndex === null ? '添加步骤' : '更新步骤' }}
            </el-button>
            <el-button v-if="editingStepIndex !== null" @click="cancelEdit">取消</el-button>
          </div>

          <div v-if="newStep.name" class="step-preview">
            <strong>步骤预览:</strong>
            {{ newStep.name }} - 持续 {{ newStep.duration }} 毫秒
            <div v-for="(action, index) in newStep.actions" :key="index" class="action-preview">
              关节{{ action.jointId }} → {{ action.angle }}°
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="automation-actions">
      <el-button class="save-btn" @click="saveSequence">
        <el-icon><DocumentAdd /></el-icon> {{ activeSequenceIndex === null ? '添加序列' : '保存序列' }}
      </el-button>
      <el-button class="run-btn" @click="runSequence(currentSequence)"
                 :disabled="isAutomating || currentSequence.steps.length === 0">
        <el-icon><VideoPlay /></el-icon> 执行序列
      </el-button>
      <el-button class="apply-btn" @click="applySequenceToPipeline(currentSequence)"
                 :disabled="isAutomating || currentSequence.steps.length === 0"
                 type="warning">
        <el-icon><Connection /></el-icon> 应用到流水线
      </el-button>
    </div>

    <div class="status-indicator" v-if="isAutomating">
      <el-progress
        :percentage="automationProgress"
        :color="automationProgressColor"
        :format="formatAutomationProgress"
      />
      <p class="current-step">{{ currentAutomationStep }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted, onMounted } from 'vue';
import {
  DocumentAdd, VideoPlay, InfoFilled, Plus, Close, Warning
} from '@element-plus/icons-vue';
import { ElNotification, ElMessage } from 'element-plus';

interface JointAction {
  jointId: number;
  angle: number;
}

interface Step {
  name: string;
  duration: number;
  actions: JointAction[];
}


const isAutomating = ref(false);
const automationProgress = ref(0);
const currentAutomationStep = ref('');

const sequences = ref([
  {
    name: "取放工件流程",
    steps:
      [
  {
    "name": "初始位置",
    "duration": 1000,
    "actions": [
      { "jointId": 1, "angle": 130 },
      { "jointId": 3, "angle": -75 },
      { "jointId": 4, "angle": 60 },
      { "jointId": 5, "angle": 45 },
      { "jointId": 6, "angle": 90 }
    ]
  },
  {
    "name": "检测位置",
    "duration": 1000,
    "actions": [
      { "jointId": 1, "angle": 130 },
      { "jointId": 3, "angle": -70 },
      { "jointId": 4, "angle": 90 },
      { "jointId": 5, "angle": 80 },
      { "jointId": 6, "angle": 90 }
    ]
  },
  {
    "name": "过渡到抓取",
    "duration": 500,
    "actions": [
      { "jointId": 1, "angle": 130 },
      { "jointId": 3, "angle": -45 },
      { "jointId": 4, "angle": 85 },
      { "jointId": 5, "angle": 110 },
      { "jointId": 6, "angle": 90 }
    ]
  },
  {
    "name": "抓取位置",
    "duration": 1000,
    "actions": [
      { "jointId": 1, "angle": 130 },
      { "jointId": 3, "angle": -20 },
      { "jointId": 4, "angle": 80 },
      { "jointId": 5, "angle": 140 },
      { "jointId": 6, "angle": 90 }
    ]
  },
  {
    "name": "抓取物体",
    "duration": 500,
    "actions": [
      { "jointId": 1, "angle": 0 }
    ]
  },
  {
    "name": "抬升转向1",
    "duration": 500,
    "actions": [
      { "jointId": 1, "angle": 0 },
      { "jointId": 3, "angle": -10 },
      { "jointId": 4, "angle": 75 },
      { "jointId": 5, "angle": 120 },
      { "jointId": 6, "angle": 70 }
    ]
  },
  {
    "name": "抬升转向2",
    "duration": 500,
    "actions": [
      { "jointId": 1, "angle": 0 },
      { "jointId": 3, "angle": -10 },
      { "jointId": 4, "angle": 70 },
      { "jointId": 5, "angle": 100 },
      { "jointId": 6, "angle": 45 }
    ]
  },
  {
    "name": "抬升转向3",
    "duration": 500,
    "actions": [
      { "jointId": 1, "angle": 0 },
      { "jointId": 3, "angle": -10 },
      { "jointId": 4, "angle": 65 },
      { "jointId": 5, "angle": 120 },
      { "jointId": 6, "angle": 20 }
    ]
  },
  {
    "name": "放置位置",
    "duration": 1000,
    "actions": [
      { "jointId": 1, "angle": 0 },
      { "jointId": 3, "angle": -20 },
      { "jointId": 4, "angle": 60 },
      { "jointId": 5, "angle": 140 },
      { "jointId": 6, "angle": 0 }
    ]
  },
  {
    "name": "放开物体",
    "duration": 1500,
    "actions": [
      { "jointId": 1, "angle": 130 }
    ]
  },
  {
    "name": "返回转向1",
    "duration": 500,
    "actions": [
      { "jointId": 1, "angle": 130 },
      { "jointId": 3, "angle": -32 },
      { "jointId": 4, "angle": 70 },
      { "jointId": 5, "angle": 120 },
      { "jointId": 6, "angle": 30 }
    ]
  },
  {
    "name": "返回转向2",
    "duration": 500,
    "actions": [
      { "jointId": 1, "angle": 130 },
      { "jointId": 3, "angle": -45 },
      { "jointId": 4, "angle": 70 },
      { "jointId": 5, "angle": 100 },
      { "jointId": 6, "angle": 45 }
    ]
  },
  {
    "name": "返回转向3",
    "duration": 500,
    "actions": [
      { "jointId": 1, "angle": 130 },
      { "jointId": 3, "angle": -57 },
      { "jointId": 4, "angle": 80 },
      { "jointId": 5, "angle": 90 },
      { "jointId": 6, "angle": 60 }
    ]
  },
  {
    "name": "返回检测位置",
    "duration": 1000,
    "actions": [
      { "jointId": 1, "angle": 130 },
      { "jointId": 3, "angle": -70 },
      { "jointId": 4, "angle": 90 },
      { "jointId": 5, "angle": 80 },
      { "jointId": 6, "angle": 90 }
    ]
  }

    ] as Step[]
  },
]);

const activeSequenceIndex = ref<number | null>(0);
const currentSequence = ref({
  name: "新序列",
  steps: [] as Step[]
});

const newStep = ref<Step>({
  name: "",
  duration: 1000,
  actions: [{ jointId: 3, angle: 0 }]
});

const editingStepIndex = ref<number | null>(null);

const addAction = () => {
  newStep.value.actions.push({ jointId: 3, angle: 0 });
};

const removeAction = (index: number) => {
  newStep.value.actions.splice(index, 1);
};

const createNewSequence = () => {
  activeSequenceIndex.value = null;
  currentSequence.value = {
    name: "新序列",
    steps: []
  };
  newStep.value = {
    name: "",
    duration: 1000,
    actions: [{ jointId: 3, angle: 0 }]
  };
  editingStepIndex.value = null;

  ElNotification.info({
    title: '新序列已创建',
    message: '请配置新序列的名称和步骤',
    duration: 2000
  });
};

const selectSequence = (index: number) => {
  activeSequenceIndex.value = index;
  currentSequence.value = JSON.parse(JSON.stringify(sequences.value[index]));
};

const addStep = () => {
  if (!newStep.value.name) {
    ElNotification.warning({ title: '步骤名称不能为空', duration: 2000 });
    return;
  }

  if (newStep.value.actions.length === 0) {
    ElNotification.warning({ title: '请至少添加一个舵机动作', duration: 2000 });
    return;
  }

  if (editingStepIndex.value !== null) {
    currentSequence.value.steps[editingStepIndex.value] = JSON.parse(JSON.stringify(newStep.value));
    editingStepIndex.value = null;
  } else {
    currentSequence.value.steps.push(JSON.parse(JSON.stringify(newStep.value)));
  }

  newStep.value = {
    name: "",
    duration: 1000,
    actions: [{ jointId: 3, angle: 0 }]
  };
};

const editStep = (index: number) => {
  newStep.value = JSON.parse(JSON.stringify(currentSequence.value.steps[index]));
  editingStepIndex.value = index;
};

const cancelEdit = () => {
  newStep.value = {
    name: "",
    duration: 1000,
    actions: [{ jointId: 3, angle: 0 }]
  };
  editingStepIndex.value = null;
};

const removeStep = (index: number) => {
  currentSequence.value.steps.splice(index, 1);
};

const saveSequence = () => {
  if (!currentSequence.value.name) {
    ElNotification.warning({ title: '序列名称不能为空', duration: 2000 });
    return;
  }

  if (activeSequenceIndex.value !== null) {
    sequences.value[activeSequenceIndex.value] = JSON.parse(JSON.stringify(currentSequence.value));
    ElNotification.success({
      title: '序列已更新',
      message: `"${currentSequence.value.name}" 已保存`,
      duration: 2000
    });
  } else {
    sequences.value.push(JSON.parse(JSON.stringify(currentSequence.value)));
    activeSequenceIndex.value = sequences.value.length - 1;
    ElNotification.success({
      title: '序列已添加',
      message: `"${currentSequence.value.name}" 已保存`,
      duration: 2000
    });
  }
};

const deleteSequence = (index: number) => {
  const sequenceName = sequences.value[index].name;
  sequences.value.splice(index, 1);

  if (activeSequenceIndex.value === index) {
    activeSequenceIndex.value = sequences.value.length > 0 ? 0 : null;
    currentSequence.value = sequences.value.length > 0 ?
      JSON.parse(JSON.stringify(sequences.value[activeSequenceIndex.value as number])) :
      { name: "新序列", steps: [] as Step[] };
  }

  ElNotification.info({
    title: '序列已删除',
    message: `"${sequenceName}" 已删除`,
    duration: 2000
  });
};

const runSequence = async (sequence: typeof sequences.value[0]) => {
  if (isAutomating.value) return;

  try {
    isAutomating.value = true;
    automationProgress.value = 0;
    currentAutomationStep.value = '准备执行...';

    const actions = sequence.steps.flatMap(step => {
      return {
        type: "multi_joint",
        name: step.name,
        movetime: step.duration,
        servos: step.actions.map(action => ({
          jointId: action.jointId,
          angle: action.angle
        }))
      };
    });

    await runArmSequence(actions);

    for (let i = 0; i < sequence.steps.length; i++) {
      const step = sequence.steps[i];
      currentAutomationStep.value = `${i+1}/${sequence.steps.length}: ${step.name}`;
      automationProgress.value = Math.round(((i + 1) / sequence.steps.length) * 100);

      await new Promise(resolve => setTimeout(resolve, step.duration));
    }

    currentAutomationStep.value = '序列执行完成';
    ElNotification.success({
      title: '序列执行成功',
      message: `"${sequence.name}" 已成功执行`,
      duration: 3000
    });

  } catch (error) {
    currentAutomationStep.value = '执行失败';
    ElNotification.error({
      title: '序列执行失败',
      message: error instanceof Error ? error.message : '执行过程中发生错误',
      duration: 3000
    });
  } finally {
    isAutomating.value = false;
    setTimeout(() => {
      automationProgress.value = 0;
      currentAutomationStep.value = '';
    }, 1000);
  }
};

const applySequenceToPipeline = async (sequence: typeof sequences.value[0]) => {
  try {
    const { setCustomArmSequence } = await import('../api/pipelineApi');

    currentAutomationStep.value = '正在应用序列到流水线...';

    const result = await setCustomArmSequence(sequence.steps);

    if (result.success) {
      ElNotification.success({
        title: '应用成功',
        message: `"${sequence.name}" 已成功应用到流水线控制`,
        duration: 3000
      });
      currentAutomationStep.value = '序列已应用到流水线';
    } else {
      throw new Error(result.message);
    }

  } catch (error) {
    currentAutomationStep.value = '应用失败';
    ElNotification.error({
      title: '应用失败',
      message: error instanceof Error ? error.message : '应用序列到流水线失败',
      duration: 3000
    });
  } finally {
    setTimeout(() => {
      currentAutomationStep.value = '';
    }, 2000);
  }
};

const formatAutomationProgress = () => {
  return `${automationProgress.value}%`;
};

const automationProgressColor = computed(() => {
  if (automationProgress.value > 80) return '#67c23a';
  if (automationProgress.value > 50) return '#e6a23c';
  return '#409eff';
});

const runArmSequence = async (actions: any[]) => {
  try {
    const response = await fetch('http://localhost:5000/api/robot_arm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        command: "run_sequence",
        params: { actions }
      })
    });

    if (!response.ok) throw new Error('API请求失败');
    return await response.json();
  } catch (error) {
    throw new Error(error instanceof Error ? error.message : '未知错误');
  }
};


</script>

<style scoped lang="scss">
.automation-control {
  padding: 20px;

  h3 {
    margin-top: 0;
    color: #67c23a;
    font-size: 20px;
    padding-bottom: 15px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  }

  .sequence-editor {
    display: flex;
    gap: 20px;
    margin: 25px 0;

    @media (max-width: 900px) {
      flex-direction: column;
    }
  }

  .sequence-list {
    flex: 1;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    padding: 15px;
    max-height: 500px;
    overflow-y: auto;

    .sequence-list-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 15px;

      h4 {
        margin: 0;
        color: #64b5f6;
      }
    }
  }

  .sequence-item {
    padding: 12px;
    margin-bottom: 10px;
    background: rgba(0, 0, 0, 0.2);
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.3s;
    position: relative;

    &:hover {
      background: rgba(64, 158, 255, 0.15);
    }

    &.active {
      background: rgba(76, 175, 80, 0.2);
      border-left: 4px solid #4caf50;
    }

    h4 {
      color: #64dd17;
      margin-bottom: 5px;
      display: flex;
      justify-content: space-between;
      font-size: 16px;
      padding-bottom: 0;
      border-bottom: none;
    }

    .actions {
      display: flex;
      gap: 8px;
      margin-top: 10px;
    }

    .steps {
      margin-top: 10px;
      padding-left: 15px;
      font-size: 14px;
      color: #90a4ae;

      ol {
        padding-left: 20px;
      }

      li {
        margin: 5px 0;
        list-style-type: decimal;
      }

      .step-actions-list {
        margin-top: 5px;
        display: flex;
        flex-wrap: wrap;
        gap: 5px;

        .action-tag {
          background: rgba(100, 221, 23, 0.15);
          padding: 2px 8px;
          border-radius: 4px;
          font-size: 12px;
        }
      }
    }
  }

  .sequence-config {
    width: 350px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    padding: 20px;

    @media (max-width: 900px) {
      width: 100%;
    }
  }

  .step-list {
    margin-top: 15px;
    max-height: 300px;
    overflow-y: auto;

    h4 {
      margin-top: 0;
      color: #64b5f6;
      padding-bottom: 10px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }
  }

  .step-item {
    padding: 10px;
    background: rgba(0, 0, 0, 0.2);
    border-radius: 6px;
    margin-bottom: 10px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    transition: all 0.3s;

    &:hover {
      background: rgba(64, 158, 255, 0.15);
    }

    .step-info {
      flex: 1;

      .action-tag {
        display: inline-block;
        background: rgba(100, 221, 23, 0.15);
        padding: 2px 8px;
        border-radius: 4px;
        margin-right: 5px;
        margin-top: 3px;
        font-size: 12px;
      }
    }

    .step-actions {
      display: flex;
      gap: 5px;
    }
  }

  .empty-steps {
    text-align: center;
    padding: 20px;
    color: #90a4ae;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    opacity: 0.7;
  }

  .step-form {
    margin-top: 20px;
    padding-top: 20px;
    border-top: 1px solid rgba(255, 255, 255, 0.1);

    h4 {
      margin-top: 0;
      color: #64b5f6;
      margin-bottom: 15px;
    }

    .actions-list {
      margin-top: 15px;
      padding: 15px;
      background: rgba(0, 0, 0, 0.1);
      border-radius: 8px;

      .actions-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;

        h5 {
          margin: 0;
          color: #90caf9;
          font-size: 14px;
        }
      }

      .action-item {
        margin-bottom: 10px;

        .action-controls {
          display: flex;
          gap: 10px;
          align-items: center;

          .el-select {
            flex: 2;
          }

          .el-input-number {
            flex: 1;
          }
        }
      }

      .no-actions {
        text-align: center;
        padding: 15px;
        color: #f44336;
        background: rgba(244, 67, 54, 0.1);
        border-radius: 4px;
        font-size: 13px;
      }
    }
  }

  .form-row {
    margin-bottom: 15px;

    label {
      display: block;
      margin-bottom: 8px;
      color: #90caf9;
      font-size: 14px;
    }

    &.actions {
      display: flex;
      gap: 10px;
      margin-top: 20px;
    }
  }

  .step-preview {
    margin-top: 20px;
    padding: 15px;
    background: rgba(0, 0, 0, 0.2);
    border-radius: 6px;
    font-size: 14px;

    .action-preview {
      margin-top: 5px;
      padding: 5px 10px;
      background: rgba(100, 221, 23, 0.1);
      border-radius: 4px;
    }
  }

  .automation-actions {
    text-align: center;
    margin: 30px 0;
    display: flex;
    justify-content: center;
    gap: 15px;
    position: sticky;
    bottom: 0;
    background: #0f1325;
    padding: 15px 0;
    z-index: 10;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    flex-wrap: wrap;

    .el-button {
      padding: 12px 20px;
      font-size: 14px;
      font-weight: bold;
      transition: all 0.3s;
      min-width: 120px;
    }

    .run-btn {
      background: linear-gradient(135deg, #4caf50, #2e7d32);
      border: none;
      color: white;

      &:hover {
        transform: translateY(-3px);
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
      }

      &:disabled {
        opacity: 0.6;
        cursor: not-allowed;
        transform: none;
        box-shadow: none;
      }
    }

    .save-btn {
      background: linear-gradient(135deg, #2196f3, #0d47a1);
      border: none;
      color: white;

      &:hover {
        transform: translateY(-3px);
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
      }
    }

    .apply-btn {
      background: linear-gradient(135deg, #ff9800, #f57c00);
      border: none;
      color: white;

      &:hover {
        transform: translateY(-3px);
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
      }

      &:disabled {
        opacity: 0.6;
        cursor: not-allowed;
        transform: none;
        box-shadow: none;
      }
    }
  }

  .status-indicator {
    margin-top: 25px;
    background: rgba(255, 255, 255, 0.05);
    padding: 20px;
    border-radius: 8px;

    .el-progress {
      margin-bottom: 15px;
    }

    .current-step {
      font-size: 16px;
      color: #409eff;
      font-weight: 500;
      text-align: center;
      margin: 0;
    }
  }

  .new-sequence-btn {
    margin-left: 10px;
    padding: 6px 12px;
    font-size: 13px;
  }
}
</style>