import { createRouter, createWebHistory } from 'vue-router'
import { installRouteGuards } from './guards'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { guestOnly: true },
    },
    {
      path: '/',
      component: () => import('../layouts/AppLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        { path: '', redirect: { name: 'projects' } },
        {
          path: 'projects',
          name: 'projects',
          component: () => import('../views/ProjectManagementRoute.vue'),
        },
        {
          path: 'projects/:projectId/requirements',
          name: 'project-requirements',
          component: () => import('../views/ProjectRequirementsRoute.vue'),
          meta: { projectRoute: true },
        },
        {
          path: 'projects/:projectId/tasks/board',
          name: 'project-task-board',
          component: () => import('../views/TeamTaskBoard.vue'),
          meta: { projectRoute: true },
        },
        {
          path: 'projects/:projectId/tasks/gantt',
          name: 'project-task-gantt',
          component: () => import('../views/TeamTaskGantt.vue'),
          meta: { projectRoute: true },
        },
        {
          path: 'projects/:projectId/versions',
          name: 'project-versions',
          component: () => import('../views/VersionSchedulingRoute.vue'),
          meta: { projectRoute: true },
        },
        {
          path: 'projects/:projectId/versions/:versionId/list',
          name: 'project-version-list',
          component: () => import('../views/VersionSchedulingRoute.vue'),
          meta: { projectRoute: true },
        },
        {
          path: 'projects/:projectId/versions/:versionId/gantt',
          name: 'project-version-gantt',
          component: () => import('../views/VersionSchedulingRoute.vue'),
          meta: { projectRoute: true },
        },
        {
          path: 'admin/departments',
          name: 'admin-departments',
          component: () => import('../views/DepartmentManagement.vue'),
          meta: { adminOnly: true },
        },
        {
          path: 'admin/invitations',
          name: 'admin-invitations',
          component: () => import('../views/InvitationManagementRoute.vue'),
          meta: { adminOnly: true },
        },
        {
          path: 'not-found',
          name: 'not-found',
          component: () => import('../views/NotFoundView.vue'),
        },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: { name: 'not-found' } },
  ],
})

installRouteGuards(router)
