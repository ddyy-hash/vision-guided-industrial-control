<template>
  <div id="app">
    <header class="app-header">
      <img src="/vite.svg" class="logo" alt="logo" />
      <span class="title">工业数采控制平台</span>
      <nav class="nav">
        <router-link to="/">控制台</router-link>
        <router-link to="/datacenter">数据中心</router-link>
        <router-link to="/energy">能效标签识别</router-link>
        <router-link to="/pipeline">流水线控制</router-link>
        <router-link to="/realtime-energy">实时能效检测</router-link>
      </nav>
    </header>
    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped lang="scss">
#app {
  min-height: 100vh;
  background: #0f1325;
  color: #e0e0e0;
  font-family: 'Microsoft YaHei', sans-serif;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.app-header {
  display: flex;
  align-items: center;
  padding: 0 30px;
  height: 60px;
  background: rgba(0,0,0,0.25);
  border-bottom: 1px solid rgba(255,255,255,0.08);
  flex-shrink: 0;
  .logo {
    height: 36px;
    margin-right: 18px;
  }
  .title {
    font-size: 20px;
    font-weight: bold;
    margin-right: 40px;
    letter-spacing: 2px;
    color: #fff;
  }
  .nav {
    display: flex;
    gap: 20px;
    a {
      color: #e0e0e0;
      text-decoration: none;
      font-size: 16px;
      &.router-link-active {
        color: #409eff;
        font-weight: bold;
      }
    }
  }
}
.app-main {
  flex: 1;
  padding: 20px;
  overflow: auto;
  min-height: 0;
}

@media (max-width: 768px) {
  .app-header {
    padding: 0 15px;
    .title {
      font-size: 16px;
      margin-right: 20px;
    }
    .nav {
      gap: 10px;
      a {
        font-size: 14px;
      }
    }
  }

  .app-main {
    padding: 10px;
  }
}

@media (max-width: 480px) {
  .app-header {
    flex-wrap: wrap;
    height: auto;
    padding: 10px 15px;
    .title {
      margin-right: 15px;
      margin-bottom: 5px;
    }
    .nav {
      width: 100%;
      justify-content: space-around;
    }
  }
}
</style>