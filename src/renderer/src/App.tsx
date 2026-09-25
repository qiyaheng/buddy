import { createHashRouter, Navigate, RouterProvider } from 'react-router-dom'
import WorkbenchLayout from './layouts/WorkbenchLayout'
import ChatPage from './pages/ChatPage'
import ExpertsPage from './pages/ExpertsPage'
import SettingsPage from './pages/settings/SettingsPage'

// 桌面应用（生产为 file://）使用 HashRouter
const router = createHashRouter([
  {
    path: '/',
    element: <WorkbenchLayout />,
    children: [
      { index: true, element: <Navigate to="/chat" replace /> },
      { path: 'chat/:taskId?', element: <ChatPage /> },
      { path: 'experts', element: <ExpertsPage /> },
      { path: 'settings', element: <SettingsPage /> },
    ],
  },
])

export default function AppRouter() {
  return <RouterProvider router={router} future={{ v7_startTransition: true }} />
}
