import { NavLink } from "react-router-dom";
import { useAuthStore } from "../../store/auth";

const navGroups = [
  {
    label: "Principale",
    items: [
      { to: "/", label: "Dashboard", icon: "⊞", roles: null },
      { to: "/reporting", label: "Reporting", icon: "📊", roles: null },
      { to: "/tasks", label: "Task", icon: "☑", roles: null },
    ],
  },
  {
    label: "Compliance",
    items: [
      { to: "/controls", label: "Controlli", icon: "✓", roles: null },
      { to: "/gap-analysis", label: "Gap Analysis", icon: "⇌", roles: null },
      { to: "/documents", label: "Documenti", icon: "📄", roles: null },
      { to: "/audit-prep", label: "Audit Prep", icon: "📋", roles: null },
    ],
  },
  {
    label: "Rischio",
    items: [
      { to: "/risk", label: "Risk", icon: "⬡", roles: null },
      { to: "/assets", label: "Asset IT/OT", icon: "⚙", roles: null },
      { to: "/bia", label: "BIA", icon: "📉", roles: null },
      { to: "/bcp", label: "BCP", icon: "🛡", roles: null },
    ],
  },
  {
    label: "Operazioni",
    items: [
      { to: "/incidents", label: "Incidenti", icon: "⚠", roles: null },
      { to: "/lessons", label: "Lessons", icon: "💡", roles: null },
      { to: "/suppliers", label: "Fornitori", icon: "🏢", roles: null },
      { to: "/training", label: "Formazione", icon: "🎓", roles: null },
      { to: "/pdca", label: "PDCA", icon: "↻", roles: null },
    ],
  },
  {
    label: "Governance",
    items: [
      { to: "/governance", label: "Governance", icon: "◈", roles: null },
      { to: "/management-review", label: "Revisione Dir.", icon: "📝", roles: ["super_admin", "compliance_officer", "risk_manager"] },
      { to: "/plants", label: "Siti", icon: "🏭", roles: ["super_admin", "compliance_officer"] },
      { to: "/users", label: "Utenti", icon: "👥", roles: ["super_admin"] },
      { to: "/audit-trail", label: "Audit Trail", icon: "📜", roles: ["super_admin", "internal_auditor", "external_auditor"] },
    ],
  },
];

export function Sidebar() {
  const userRole = useAuthStore(s => s.user?.role ?? "");

  function isVisible(roles: string[] | null): boolean {
    if (!roles) return true;
    return roles.includes(userRole);
  }

  return (
    <aside className="w-56 min-h-screen bg-primary-900 text-white flex flex-col">
      <div className="px-4 py-5 border-b border-primary-700">
        <h1 className="text-lg font-bold tracking-tight">GRC Platform</h1>
        <p className="text-xs text-primary-300 mt-0.5">Compliance & Risk</p>
      </div>
      <nav className="flex-1 px-2 py-4 space-y-4 overflow-y-auto">
        {navGroups.map(group => {
          const visibleItems = group.items.filter(item => isVisible(item.roles));
          if (visibleItems.length === 0) return null;
          return (
            <div key={group.label}>
              <p className="px-3 mb-1 text-xs font-semibold uppercase tracking-wider text-primary-400">
                {group.label}
              </p>
              <div className="space-y-0.5">
                {visibleItems.map(item => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === "/"}
                    className={({ isActive }) =>
                      `flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                        isActive
                          ? "bg-primary-700 text-white"
                          : "text-primary-200 hover:bg-primary-800 hover:text-white"
                      }`
                    }
                  >
                    <span className="text-base w-5 text-center">{item.icon}</span>
                    {item.label}
                  </NavLink>
                ))}
              </div>
            </div>
          );
        })}
      </nav>
    </aside>
  );
}
