import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '../views/DashboardView.vue'
import PipelineControlView from '../views/PipelineControlView.vue'
import DataCenterView from '../views/DataCenterView.vue'
import EnergyDetectionView from '../views/EnergyDetectionView.vue'
import RealtimeEnergyDetectionView from '../views/RealtimeEnergyDetectionView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: DashboardView
    },
    {
      path: '/pipeline',
      name: 'pipeline',
      component: PipelineControlView
    },
    {
      path: '/data',
      name: 'data',
      component: DataCenterView
    },
    {
      path: '/energy',
      name: 'energy',
      component: EnergyDetectionView
    },
    {
      path: '/realtime-energy',
      name: 'realtime-energy',
      component: RealtimeEnergyDetectionView
    }
  ]
})

export default router