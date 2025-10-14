import React, { useState, useMemo } from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "../Sidebar/Sidebar";

const Layout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const leftPad = useMemo(() => (collapsed ? "pl-20" : "pl-64"), [collapsed]);

  return (
    <div className="page-wrap">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((v) => !v)} />
      <div className={`${leftPad} transition-all duration-300`}>
        {/* top bar */}
        <header className="sticky top-0 z-40 backdrop-blur bg-white/70 border-b">
          <div className="flex items-center justify-between px-6 py-3">
            <h1 className="text-lg font-semibold text-brand">AI Call Agent</h1>
            <div className="flex items-center gap-3 text-sm text-[var(--muted)]">
              <span>Welcome</span>
              <div className="h-8 w-8 rounded-full bg-accent/30 grid place-items-center text-accent font-bold">
                A
              </div>
            </div>
          </div>
        </header>

        
        <main className="p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default Layout;
