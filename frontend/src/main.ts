import { createApp } from 'vue';
import { createPinia } from 'pinia';
import ElementPlus from 'element-plus';
import zhCn from 'element-plus/dist/locale/zh-cn.mjs';
import App from './App.vue';
import router from './router';
import 'element-plus/dist/index.css';
import './assets/main.css';

import { SystemAPI } from './native/system-adapter';

const app = createApp(App);

const initializeSystem = async () => {
  try {
    const platformInfo = SystemAPI.getSystemInfo();
    console.log('当前平台信息:', platformInfo);

    const hardwareAccelerated = await SystemAPI.enableHardwareAcceleration();
    console.log('硬件加速状态:', hardwareAccelerated ? '已启用' : '未启用');

    SystemAPI.startDataCollection();

    app.config.globalProperties.$platform = platformInfo;

  } catch (error) {
    console.error('系统初始化失败:', error instanceof Error ? error.message : error);
  }
};

const cleanup = () => {
  try {
    SystemAPI.stopDataCollection();
    console.log('系统清理完成');
  } catch (e) {
    console.warn('清理时发生异常:', e);
  }
};

window.addEventListener('beforeunload', cleanup);

app.use(createPinia());
app.use(router);
app.use(ElementPlus, { locale: zhCn });

initializeSystem().then(() => {
  app.mount('#app');
}).catch((err) => {
  console.error('应用启动失败:', err);
});
