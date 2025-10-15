import React from "react";
import { NavLink } from "react-router-dom";
import {
  FaTachometerAlt,
  FaUserCog,
  FaPhoneAlt,
  FaChartLine,
  FaComments,
  FaChevronLeft,
  FaChevronRight,
} from "react-icons/fa";

type SidebarProps = {
  collapsed: boolean;
  onToggle: () => void;
};

const linkBase =
  "flex items-center gap-3 px-3 py-2 rounded-lg transition hover:bg-white/10";
const linkActive = "bg-white/15 ring-1 ring-white/20";

const Sidebar: React.FC<SidebarProps> = ({ collapsed, onToggle }) => {
  return (
    <aside
      className={`fixed left-0 top-0 h-screen bg-brand text-white transition-all duration-300 ${
        collapsed ? "w-20" : "w-64"
      }`}
    >
      <div className="flex items-center justify-between px-4 pt-4 pb-2">
        <div className="font-extrabold tracking-tight">
          {collapsed ? "AI" : "AI Call Agent"}
        </div>
        <button
          onClick={onToggle}
          className="p-2 rounded-md hover:bg-white/10"
          aria-label="Toggle sidebar"
          title="Toggle sidebar"
        >
          {collapsed ? <FaChevronRight /> : <FaChevronLeft />}
        </button>
      </div>

      <nav className="mt-4 px-3 space-y-2">
        <NavLink
          to="/dashboard"
          className={({ isActive }) => `${linkBase} ${isActive ? linkActive : ""}`}
          title="Dashboard"
          aria-label="Dashboard"
        >
          <FaTachometerAlt />
          {!collapsed && <span>Dashboard</span>}
        </NavLink>

        <NavLink
          to="/agent-config"
          className={({ isActive }) => `${linkBase} ${isActive ? linkActive : ""}`}
          title="Agent Config"
          aria-label="Agent Config"
        >
          <FaUserCog />
          {!collapsed && <span>Agent Config</span>}
        </NavLink>

        <NavLink
          to="/call-trigger"
          className={({ isActive }) => `${linkBase} ${isActive ? linkActive : ""}`}
          title="Call Trigger"
          aria-label="Call Trigger"
        >
          <FaPhoneAlt />
          {!collapsed && <span>Call Trigger</span>}
        </NavLink>

        <NavLink
          to="/conversations"
          className={({ isActive }) => `${linkBase} ${isActive ? linkActive : ""}`}
          title="Conversations"
          aria-label="Conversations"
        >
          <FaComments />
          {!collapsed && <span>Conversations</span>}
        </NavLink>

        <NavLink
          to="/analytics"
          className={({ isActive }) => `${linkBase} ${isActive ? linkActive : ""}`}
          title="Analytics"
          aria-label="Analytics"
        >
          <FaChartLine />
          {!collapsed && <span>Analytics</span>}
        </NavLink>
      </nav>

      {!collapsed && (
        <div className="absolute bottom-4 left-0 right-0 px-4 text-xs text-white/80">
          <div className="border-t border-white/20 pt-3">
            v0.1 • © AI Call Agent
          </div>
        </div>
      )}
    </aside>
  );
};

export default Sidebar;
