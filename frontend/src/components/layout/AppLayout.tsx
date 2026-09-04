import { useState } from 'react'
import { Outlet } from 'react-router-dom'

import './AppLayout.css'

import Header from './Header'
import Sidebar from './Sidebar'
import { CurrencyProvider } from '../../context/CurrencyContext'

export default function AppLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] =
    useState(false)

  return <CurrencyProvider>
    <div className="app-layout">
      <div className="app-layout__body">
        <Sidebar
          collapsed={sidebarCollapsed}
        />

        <div className="app-layout__shell">
          <Header
            collapsed={sidebarCollapsed}
            onToggleSidebar={() =>
              setSidebarCollapsed((value) => !value)
            }
          />

          <main className="app-layout__content">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  </CurrencyProvider>
}
