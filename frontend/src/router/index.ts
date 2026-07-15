/** Vue Router configuration. */
import { createRouter, createWebHistory } from "vue-router"
import { useAuthStore } from "@/stores/authStore"

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/login",
      name: "Login",
      component: () => import("@/views/auth/LoginPage.vue"),
      meta: { requiresAuth: false },
    },
    {
      path: "/register",
      name: "Register",
      component: () => import("@/views/auth/RegisterPage.vue"),
      meta: { requiresAuth: false },
    },
    {
      path: "/",
      component: () => import("@/layouts/MainLayout.vue"),
      meta: { requiresAuth: true },
      children: [
        {
          path: "",
          redirect: "/dashboard",
        },
        {
          path: "dashboard",
          name: "Dashboard",
          component: () => import("@/views/dashboard/DashboardPage.vue"),
        },
        {
          path: "organizations",
          name: "Organizations",
          component: () => import("@/views/organization/OrganizationPage.vue"),
        },
        {
          path: "organizations/departments",
          name: "Departments",
          component: () => import("@/views/organization/DepartmentPage.vue"),
        },
        // HR Routes
        {
          path: "hr/employees",
          name: "Employees",
          component: () => import("@/views/hr/EmployeeListPage.vue"),
        },
        {
          path: "hr/employees/:empId",
          name: "EmployeeDetail",
          component: () => import("@/views/hr/EmployeeDetailPage.vue"),
        },
        {
          path: "hr/attendance",
          name: "Attendance",
          component: () => import("@/views/hr/AttendancePage.vue"),
        },
        {
          path: "hr/leave",
        {
          path: "hr/training/courses",
          name: "TrainingCourses",
          component: () => import("@/views/hr/training/CourseListPage.vue"),
        },
        {
          path: "hr/training/plans",
          name: "TrainingPlans",
          component: () => import("@/views/hr/training/PlanListPage.vue"),
        },
        {
          path: "hr/training/instructors",
          name: "TrainingInstructors",
          component: () => import("@/views/hr/training/InstructorPage.vue"),
        },
        {
          path: "hr/training/registrations",
          name: "TrainingRegistrations",
          component: () => import("@/views/hr/training/RegistrationPage.vue"),
        },
        {
          path: "hr/training/evaluations",
          name: "TrainingEvaluations",
          component: () => import("@/views/hr/training/EvaluationPage.vue"),
        },
        {
          path: "hr/training/certificates",
          name: "TrainingCertificates",
          component: () => import("@/views/hr/training/CertificatePage.vue"),
        },
          name: "Leave",
          component: () => import("@/views/hr/LeavePage.vue"),
        },
        // Task Management
        {
          path: "tasks",
          name: "Tasks",
          component: () => import("@/views/tasks/TaskListPage.vue"),
        },
        // Wiki / Knowledge Base
        {
          path: "wiki",
          name: "Wiki",
          component: () => import("@/views/wiki/WikiPage.vue"),
        },
        {
          path: "wiki/pages/:pageId",
          name: "WikiEditor",
          component: () => import("@/views/wiki/WikiEditorPage.vue"),
        },
        // Audit Logs
        {
          path: "audit-logs",
          name: "AuditLogs",
          component: () => import("@/views/audit/AuditLogPage.vue"),
        },
      ],
    },
  ],
})

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth !== false && !authStore.isLoggedIn) {
    next({ name: "Login", query: { redirect: to.fullPath } })
  } else if (to.name === "Login" && authStore.isLoggedIn) {
    next({ name: "Dashboard" })
  } else {
    next()
  }
})

export default router
