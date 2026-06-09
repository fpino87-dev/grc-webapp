import { NavLink } from "react-router-dom";
import { useAuthStore } from "../../store/auth";
import { useUiStore } from "../../store/ui";
import { useTranslation } from "react-i18next";

type NavItem = { to: string; labelKey: string; icon: string; roles: string[] | null };
type NavGroup = { labelKey: string; items: NavItem[] };

const navGroups: NavGroup[] = [
  {
    labelKey: "sidebar.groups.main",
    items: [
      { to: "/", labelKey: "sidebar.items.dashboard", icon: "⊞", roles: null },
      { to: "/cockpit", labelKey: "sidebar.items.cockpit", icon: "🎛", roles: ["super_admin", "compliance_officer", "risk_manager", "internal_auditor", "plant_manager"] },
      { to: "/reporting", labelKey: "sidebar.items.reporting", icon: "📊", roles: null },
      { to: "/kpi", labelKey: "sidebar.items.kpi_operational", icon: "📈", roles: null },
      { to: "/tasks", labelKey: "sidebar.items.tasks", icon: "☑", roles: null },
      { to: "/checklists/runs", labelKey: "sidebar.items.checklist_runs", icon: "✔", roles: null },
    ],
  },
  {
    labelKey: "sidebar.groups.compliance",
    items: [
      { to: "/controls", labelKey: "sidebar.items.controls", icon: "✓", roles: null },
      { to: "/gap-analysis", labelKey: "sidebar.items.gap_analysis", icon: "⇌", roles: null },
      { to: "/documents", labelKey: "sidebar.items.documents", icon: "📄", roles: null },
      { to: "/audit-prep", labelKey: "sidebar.items.audit_prep", icon: "🎯", roles: null },
    ],
  },
  {
    labelKey: "sidebar.groups.risk_continuity",
    items: [
      { to: "/bia", labelKey: "sidebar.items.bia", icon: "📉", roles: null },
      { to: "/risk", labelKey: "sidebar.items.risk", icon: "⬡", roles: null },
      { to: "/assets", labelKey: "sidebar.items.assets", icon: "🖥", roles: null },
      { to: "/bcp", labelKey: "sidebar.items.bcp", icon: "🛡", roles: null },
    ],
  },
  {
    labelKey: "sidebar.groups.operations",
    items: [
      { to: "/incidents", labelKey: "sidebar.items.incidents", icon: "⚠", roles: null },
      { to: "/lessons", labelKey: "sidebar.items.lessons", icon: "💡", roles: null },
      { to: "/suppliers", labelKey: "sidebar.items.suppliers", icon: "🏢", roles: null },
      { to: "/training", labelKey: "sidebar.items.training", icon: "🎓", roles: null },
      { to: "/pdca", labelKey: "sidebar.items.pdca", icon: "↻", roles: null },
    ],
  },
  {
    labelKey: "sidebar.groups.planning",
    items: [
      { to: "/schedule/activity", labelKey: "sidebar.items.activity_schedule", icon: "📅", roles: null },
      { to: "/schedule/documents", labelKey: "sidebar.items.required_documents", icon: "📑", roles: null },
      { to: "/schedule/policy", labelKey: "sidebar.items.schedule_policy", icon: "⏱", roles: ["super_admin", "compliance_officer"] },
      { to: "/checklists/templates", labelKey: "sidebar.items.checklist_templates", icon: "🗒", roles: ["super_admin", "compliance_officer", "ciso", "risk_manager"] },
    ],
  },
  {
    labelKey: "sidebar.groups.organisation",
    items: [
      { to: "/governance", labelKey: "sidebar.items.governance", icon: "◈", roles: null },
      { to: "/management-review", labelKey: "sidebar.items.management_review", icon: "📝", roles: ["super_admin", "compliance_officer", "risk_manager"] },
      { to: "/plants", labelKey: "sidebar.items.plants", icon: "🏭", roles: ["super_admin", "compliance_officer"] },
      { to: "/users", labelKey: "sidebar.items.users", icon: "👥", roles: ["super_admin"] },
      { to: "/competency", labelKey: "sidebar.items.competency", icon: "◎", roles: ["super_admin", "compliance_officer", "ciso"] },
      { to: "/audit-trail", labelKey: "sidebar.items.audit_trail", icon: "📜", roles: ["super_admin", "internal_auditor", "external_auditor"] },
      { to: "/settings/mfa", labelKey: "sidebar.items.mfa", icon: "🔐", roles: null },
    ],
  },
  {
    labelKey: "sidebar.groups.security",
    items: [
      { to: "/osint", labelKey: "sidebar.items.osint", icon: "🔍", roles: ["super_admin", "ciso", "compliance_officer"] },
    ],
  },
  {
    labelKey: "sidebar.groups.settings",
    items: [
      { to: "/settings/email", labelKey: "sidebar.items.email_settings", icon: "✉️", roles: ["super_admin"] },
      { to: "/settings/notifications", labelKey: "sidebar.items.notification_rules", icon: "🔔", roles: ["super_admin"] },
      { to: "/settings/ai", labelKey: "sidebar.items.ai_engine", icon: "🤖", roles: ["super_admin"] },
      { to: "/settings/backups", labelKey: "sidebar.items.backups", icon: "💾", roles: ["super_admin"] },
    ],
  },
];

export function Sidebar() {
  const userRole = useAuthStore(s => s.user?.role ?? "");
  const { t } = useTranslation();

  function isVisible(roles: string[] | null): boolean {
    if (!roles) return true;
    return roles.includes(userRole);
  }

  const collapsed = useUiStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useUiStore((s) => s.toggleSidebar);

  return (
    <aside
      className={`${collapsed ? "w-14" : "w-56"} min-h-screen bg-primary-900 text-white flex flex-col transition-all duration-200`}
    >
      <div
        className={`border-b border-primary-700 flex items-center ${collapsed ? "px-2 justify-center" : "px-4"}`}
        style={{ gap: "10px", paddingTop: "20px", paddingBottom: "20px", imageRendering: "crisp-edges" }}
      >
        <svg width="36" height="36" viewBox="0 0 40 40" fill="none" aria-hidden="true" className="shrink-0">
          <rect x="0.75" y="0.75" width="38.5" height="38.5" rx="9" fill="#ffffff" stroke="rgba(255,255,255,0.2)" strokeWidth="1.5" />
          <rect x="10" y="10" width="8" height="8" rx="1.5" fill="#185FA5" fillOpacity="0.95" />
          <rect x="22" y="10" width="8" height="8" rx="1.5" fill="#185FA5" fillOpacity="0.45" />
          <rect x="10" y="22" width="8" height="8" rx="1.5" fill="#185FA5" fillOpacity="0.45" />
          <rect x="22" y="22" width="8" height="8" rx="1.5" fill="#185FA5" fillOpacity="0.95" />
        </svg>
        {!collapsed && (
          <div>
            <div style={{ fontSize: "22px", letterSpacing: "-0.5px", lineHeight: 1.1, textTransform: "lowercase", WebkitFontSmoothing: "antialiased", textRendering: "optimizeLegibility" }}>
              <span style={{ color: "#ffffff", fontWeight: 400 }}>gov</span>
              <span style={{ color: "#85B7EB", fontWeight: 500 }}>rico</span>
            </div>
            <div style={{ color: "#85B7EB", opacity: 0.6, fontSize: "11px", marginTop: "2px" }}>
              Compliance & Risk
            </div>
          </div>
        )}
      </div>
      <nav className="flex-1 px-2 py-4 space-y-4 overflow-y-auto pb-10">
        {navGroups.map((group, groupIndex) => {
          const visibleItems = group.items.filter(item => isVisible(item.roles));
          if (visibleItems.length === 0) return null;
          // Toggle collassa/espandi sulla riga del primo gruppo ("Principale"),
          // allineato a destra; in modalità rail resta centrato come prima voce.
          const toggleButton = (
            <button
              onClick={toggleSidebar}
              title={t(collapsed ? "sidebar.expand" : "sidebar.collapse")}
              aria-label={t(collapsed ? "sidebar.expand" : "sidebar.collapse")}
              className="px-1.5 rounded text-primary-300 hover:bg-primary-800 hover:text-white text-sm font-mono leading-none"
            >
              {collapsed ? "»" : "«"}
            </button>
          );
          return (
            <div key={group.labelKey}>
              {collapsed ? (
                groupIndex === 0 ? (
                  <div className="flex justify-center mb-1">{toggleButton}</div>
                ) : (
                  <div className="border-t border-primary-800 mx-1 mb-1" />
                )
              ) : (
                <div className="px-3 mb-1 flex items-center justify-between">
                  <p className="text-xs font-semibold uppercase tracking-wider text-primary-400">
                    {t(group.labelKey)}
                  </p>
                  {groupIndex === 0 && toggleButton}
                </div>
              )}
              <div className="space-y-0.5">
                {visibleItems.map(item => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === "/"}
                    title={collapsed ? t(item.labelKey) : undefined}
                    className={({ isActive }) =>
                      `flex items-center rounded-md text-sm font-medium transition-colors ${
                        collapsed ? "justify-center px-0 py-2" : "gap-3 px-3 py-2"
                      } ${
                        isActive
                          ? "bg-primary-700 text-white"
                          : "text-primary-200 hover:bg-primary-800 hover:text-white"
                      }`
                    }
                  >
                    <span className="text-base w-5 text-center shrink-0">{item.icon}</span>
                    {!collapsed && t(item.labelKey)}
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
