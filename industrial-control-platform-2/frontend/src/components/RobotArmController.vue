<template>
  <div class="robot-arm-container">
    <div ref="threeContainer" class="three-canvas"></div>

    <div class="control-panel">
      <h3>机械臂控制</h3>

              <el-alert
        v-if="errorMessage"
        :title="errorMessage"
        type="error"
        show-icon
        closable
        @close="errorMessage = ''"
        style="
          margin-bottom: 20px;
          white-space: normal;
          line-height: 1.5;
          min-height: 60px;
        "
      />

      <div v-for="(joint, index) in joints" :key="index" class="joint-control">
        <label>关节 {{ index + 1 }} (ID: {{ index + 3 }})</label>
        <div class="slider-container">
          <el-slider
            v-model="joint.angle"
            :min="joint.min"
            :max="joint.max"
            :step="1"
            :disabled="isBusy"
            @change="(value) => updateJoint(index, value)"
          />
          <span class="angle-display">{{ joint.angle }}°</span>
        </div>
      </div>

      <div class="presets">
        <el-button
          v-for="(preset, i) in presets"
          :key="i"
          :disabled="isBusy"
          @click="applyPreset(preset)"
        >
          {{ preset.name }}
        </el-button>
      </div>

      <div class="emergency-stop">
        <el-button type="danger" @click="handleEmergencyStop" :disabled="!isBusy">
          <el-icon><SwitchButton /></el-icon> 紧急停止
        </el-button>
      </div>

      <div class="status">
        <p>位置: X:{{ position.x.toFixed(1) }} Y:{{ position.y.toFixed(1) }} Z:{{ position.z.toFixed(1) }}</p>
        <p>温度: {{ temperature }}°C</p>
        <p>状态: <el-tag :type="statusType">{{ statusText }}</el-tag></p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed } from 'vue';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { SwitchButton } from '@element-plus/icons-vue';
import {
  setJointAngle,
  runSequence,
  emergencyStop
} from '../api/robotArmApi';

const threeContainer = ref<HTMLElement | null>(null);
let scene: THREE.Scene, camera: THREE.PerspectiveCamera, renderer: THREE.WebGLRenderer;
let controls: OrbitControls;
let armGroup: THREE.Group;

const joints = ref([
  { name: 'Base', angle: 0, min: -90, max: 90 },
  { name: 'Shoulder', angle: 0, min: -90, max: 90 },
  { name: 'Elbow', angle: 90, min: 0, max: 180 },
  { name: 'Wrist', angle: 90, min: 0, max: 180 },
  { name: 'Gripper', angle: 130, min: 0, max: 180 }
]);

const position = ref({ x: 0, y: 0, z: 0 });
const temperature = ref(32.5);
const isBusy = ref(false);
const errorMessage = ref('');

const presets = ref([
  { name: '初始位置', angles: [-75, 60, 45, 90, 130] },
  { name: '抓取位置', angles: [-20, -45, 60, -15, 130] },
  { name: '放置位置', angles: [-20, 30, -45, 20, 130] },
  { name: '检测位置', angles: [-70, 90, 70, 90, 130] }
]);

const statusType = computed(() => {
  if (isBusy.value) return 'warning';
  return 'success';
});

const statusText = computed(() => {
  return isBusy.value ? '运行中' : '待机';
});

function initThree() {
  if (!threeContainer.value) return;

  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x1a1d29);

  camera = new THREE.PerspectiveCamera(
    75,
    threeContainer.value.clientWidth / threeContainer.value.clientHeight,
    0.1,
    1000
  );
  camera.position.set(0, 2, 5);

  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(
    threeContainer.value.clientWidth,
    threeContainer.value.clientHeight
  );
  threeContainer.value.appendChild(renderer.domElement);

  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;

  const ambientLight = new THREE.AmbientLight(0x404040);
  scene.add(ambientLight);

  const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
  directionalLight.position.set(1, 1, 1);
  scene.add(directionalLight);

  const axesHelper = new THREE.AxesHelper(2);
  scene.add(axesHelper);

  createRobotArm();

  animate();
}

function createRobotArm() {
  armGroup = new THREE.Group();

  const baseGeometry = new THREE.CylinderGeometry(0.8, 0.8, 0.4, 32);
  const baseMaterial = new THREE.MeshPhongMaterial({ color: 0x2a4e6c });
  const base = new THREE.Mesh(baseGeometry, baseMaterial);
  base.position.y = 0.2;
  armGroup.add(base);

  let prevPart: THREE.Object3D = base;
  const colors = [0x3465a4, 0x4e9a06, 0xc17d11, 0x729fcf, 0xcc0000];
  const lengths = [1, 0.8, 0.6, 0.4, 0.3];

  joints.value.forEach((_, i) => {
    const jointGroup = new THREE.Group();
    jointGroup.name = `joint-${i}`;

    const jointGeometry = new THREE.SphereGeometry(0.2, 16, 16);
    const jointMaterial = new THREE.MeshPhongMaterial({ color: colors[i] });
    const joint = new THREE.Mesh(jointGeometry, jointMaterial);
    jointGroup.add(joint);

    const armGeometry = new THREE.BoxGeometry(0.15, lengths[i], 0.15);
    const armMaterial = new THREE.MeshPhongMaterial({ color: colors[i] });
    const arm = new THREE.Mesh(armGeometry, armMaterial);
    arm.position.y = -lengths[i]/2;
    jointGroup.add(arm);

    if (i === 0) {
      jointGroup.position.y = 0.4;
    } else {
      jointGroup.position.y = -lengths[i-1];
    }

    prevPart.add(jointGroup);
    prevPart = jointGroup;
  });

  scene.add(armGroup);

  const endEffectorGeometry = new THREE.BoxGeometry(0.2, 0.2, 0.2);
  const endEffectorMaterial = new THREE.MeshPhongMaterial({ color: 0xcc0000 });
  const endEffector = new THREE.Mesh(endEffectorGeometry, endEffectorMaterial);
  endEffector.position.y = -lengths[lengths.length-1];
  prevPart.add(endEffector);

  const gripperGeometry = new THREE.BoxGeometry(0.15, 0.2, 0.1);
  const gripperMaterial = new THREE.MeshPhongMaterial({ color: 0xcc0000 });
  const gripper = new THREE.Mesh(gripperGeometry, gripperMaterial);
  gripper.position.y = -0.1;
  prevPart.add(gripper);
}

function updateArm() {
  if (!armGroup) return;

  joints.value.forEach((joint, i) => {
    const jointGroup = armGroup.getObjectByName(`joint-${i}`);
    if (jointGroup) {
      jointGroup.rotation.z = THREE.MathUtils.degToRad(joint.angle);
    }
  });

  const angles = joints.value.map(j => THREE.MathUtils.degToRad(j.angle));
  let x = 0, y = 0.4, z = 0;
  const lengths = [1, 0.8, 0.6, 0.4, 0.3];

  for (let i = 0; i < angles.length; i++) {
    y -= lengths[i] * Math.cos(angles[i]);
    z += lengths[i] * Math.sin(angles[i]);
  }

  position.value = { x, y: parseFloat(y.toFixed(2)), z: parseFloat(z.toFixed(2)) };
}

async function updateJoint(index: number, angle: number) {
  const jointIdMap = [3, 4, 5, 6, 1];
  const jointId = jointIdMap[index];

  try {
    isBusy.value = true;

    const result = await setJointAngle(jointId, angle);

    if (!result.success) {
      errorMessage.value = `关节 ${jointId} 控制失败: ${result.message}`;
      return;
    }

    joints.value[index].angle = angle;
    updateArm();

  } catch (error) {
    errorMessage.value = `控制请求失败: ${error.message || '网络错误'}`;
    console.error('控制关节失败:', error);
  } finally {
    isBusy.value = false;
  }
}

async function applyPreset(preset: { angles: number[] }) {
  try {
    isBusy.value = true;

    joints.value = joints.value.map((joint, i) => ({
      ...joint,
      angle: preset.angles[i] || 0
    }));

    updateArm();

    const actions = joints.value.map((joint, i) => ({
      type: 'set_joint_angle',
      params: {
        joint: i + 3,
        angle: joint.angle,
        movetime: 1000
      }
    }));

    const result = await runSequence(actions);

    if (!result.success) {
      errorMessage.value = `执行预设失败: ${result.message}`;
    }

  } catch (error) {
    errorMessage.value = `执行预设失败: ${error.message || '网络错误'}`;
    console.error('执行预设失败:', error);
  } finally {
    isBusy.value = false;
  }
}

async function handleEmergencyStop() {
  try {
    const result = await emergencyStop();

    if (result.success) {
      joints.value = joints.value.map(joint => ({ ...joint, angle: 0 }));
      updateArm();

      isBusy.value = false;
    } else {
      errorMessage.value = `紧急停止失败: ${result.message}`;
    }
  } catch (error) {
    errorMessage.value = `紧急停止失败: ${error.message || '网络错误'}`;
    console.error('紧急停止失败:', error);
  }
}

function animate() {
  requestAnimationFrame(animate);
  if (controls) controls.update();
  if (renderer && scene && camera) renderer.render(scene, camera);
}

onMounted(() => {
  if (threeContainer.value) {
    initThree();
    window.addEventListener('resize', handleResize);
  }
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize);
  if (renderer) {
    renderer.dispose();
  }
});

function handleResize() {
  if (!threeContainer.value || !camera || !renderer) return;

  camera.aspect = threeContainer.value.clientWidth / threeContainer.value.clientHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(
    threeContainer.value.clientWidth,
    threeContainer.value.clientHeight
  );
}
</script>

<style scoped lang="scss">
.robot-arm-container {
  display: flex;
  height: 500px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  overflow: hidden;

  .three-canvas {
    flex: 1;
    height: 100%;
    border-right: 1px solid rgba(255, 255, 255, 0.1);
  }

  .control-panel {
    width: 340px;
    padding: 20px;
    background: rgba(255, 255, 255, 0.05);
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    max-height: 100%;

    h3 {
      margin-top: 0;
      color: #409eff;
      padding-bottom: 10px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
      position: sticky;
      top: 0;
      background: rgba(255, 255, 255, 0.05);
      z-index: 1;
    }

    .joint-control {
      margin-bottom: 20px;

      label {
        display: block;
        margin-bottom: 8px;
        font-size: 14px;
        color: rgba(255, 255, 255, 0.8);
      }

      .slider-container {
        display: flex;
        align-items: center;
        gap: 15px;

        .el-slider {
          flex: 1;
          min-width: 0;
        }

        .angle-display {
          min-width: 50px;
          text-align: center;
          font-weight: bold;
          background: rgba(255, 255, 255, 0.1);
          padding: 5px 10px;
          border-radius: 4px;
          flex-shrink: 0;
        }
      }
    }

    .presets {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 10px;
      margin: 15px 0;

      button {
        width: 100%;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
    }

    .emergency-stop {
      margin: 20px 0;
      position: sticky;
      bottom: 0;
      background: rgba(255, 255, 255, 0.05);
      padding: 10px 0;
      z-index: 1;

      button {
        width: 100%;
        padding: 12px;
        font-size: 16px;
        font-weight: bold;
      }
    }

    .status {
      background: rgba(255, 255, 255, 0.05);
      padding: 15px;
      border-radius: 6px;
      margin-top: auto;
      font-size: 14px;
      min-height: 100px;

      p {
        margin: 8px 0;
        display: flex;
        align-items: center;

        .el-tag {
          margin-left: 10px;
        }
      }
    }
  }
}

@media (max-width: 900px) {
  .robot-arm-container {
    flex-direction: column;
    height: auto;

    .three-canvas {
      height: 400px;
      border-right: none;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }

    .control-panel {
      width: 100%;
    }
  }
}
</style>