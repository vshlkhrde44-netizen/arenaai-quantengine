import React from 'react';
import {
  LayoutDashboard,
  TrendingUp,
  Radio,
  Layers,
  Cpu,
  FlaskConical,
  PlaySquare,
  FastForward,
  Database,
  Terminal,
  ListOrdered,
  Briefcase,
  PieChart,
  ShieldCheck,
  FileCheck2,
  HeartPulse,
  Settings,
  Scale
} from 'lucide-react';

export type NavTab =
  | 'dashboard'
  | 'markets'
  | 'marketdata'
  | 'microstructure'
  | 'strategies'
  | 'research'
  | 'backtesting'
  | 'walkforward'
  | 'statistical'
  | 'datasets'
  | 'papertrading'
  | 'orders'
  | 'positions'
  | 'portfolio'
  | 'risk'
  | 'audit'
  | 'reports'
  | 'systemhealth'
  | 'settings';

interface SidebarProps {
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  openOrdersCount: number;
  activePositionsCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onSelectTab,
  openOrdersCount,
  activePositionsCount
}) => {
  const navSections = [
    {
      title: 'MONITORING',
      items: [
        { id: 'dashboard' as NavTab, label: 'Dashboard', icon: LayoutDashboard },
        { id: 'markets' as NavTab, label: 'Markets & Feeds', icon: TrendingUp },
        { id: 'marketdata' as NavTab, label: 'Market Data Engine', icon: Radio },
        { id: 'microstructure' as NavTab, label: 'Microstructure', icon: Layers },
      ]
    },
    {
      title: 'QUANT RESEARCH',
      items: [
        { id: 'strategies' as NavTab, label: 'Strategies Registry', icon: Cpu },
        { id: 'research' as NavTab, label: 'Research & Lookahead', icon: FlaskConical },
        { id: 'backtesting' as NavTab, label: 'Backtesting Lab', icon: PlaySquare },
        { id: 'walkforward' as NavTab, label: 'Walk-Forward OOS', icon: FastForward },
        { id: 'statistical' as NavTab, label: 'Statistical & Monte Carlo', icon: Scale },
        { id: 'datasets' as NavTab, label: 'Datasets & Quality', icon: Database },
      ]
    },
    {
      title: 'PAPER EXECUTION',
      items: [
        { id: 'papertrading' as NavTab, label: 'Paper Trading', icon: Terminal, highlight: true },
        { id: 'orders' as NavTab, label: 'Orders & State Machine', icon: ListOrdered, badge: openOrdersCount },
        { id: 'positions' as NavTab, label: 'Positions', icon: Briefcase, badge: activePositionsCount },
        { id: 'portfolio' as NavTab, label: 'Portfolio Accounting', icon: PieChart },
      ]
    },
    {
      title: 'GOVERNANCE & AUDIT',
      items: [
        { id: 'risk' as NavTab, label: 'Risk Engine', icon: ShieldCheck },
        { id: 'audit' as NavTab, label: 'Audit & Forensics', icon: FileCheck2 },
        { id: 'reports' as NavTab, label: 'Reports & Certification', icon: FileCheck2 },
        { id: 'systemhealth' as NavTab, label: 'System Health', icon: HeartPulse },
        { id: 'settings' as NavTab, label: 'Settings & Vault', icon: Settings },
      ]
    }
  ];

  return (
    <aside className="w-60 bg-[#090d14] border-r border-[#1e293b] flex flex-col justify-between select-none">
      <div className="py-3 overflow-y-auto max-h-[calc(100vh-80px)]">
        {navSections.map((section, idx) => (
          <div key={idx} className="mb-4">
            <div className="px-4 py-1 text-[10px] font-bold text-slate-500 tracking-wider uppercase">
              {section.title}
            </div>
            <div className="mt-1 space-y-0.5 px-2">
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => onSelectTab(item.id)}
                    className={`w-full flex items-center justify-between px-3 py-1.5 rounded text-xs transition-colors font-medium ${
                      isActive
                        ? 'bg-emerald-500/15 text-emerald-400 font-semibold border-l-2 border-emerald-400'
                        : item.highlight
                        ? 'text-emerald-300 hover:bg-[#121822] hover:text-white'
                        : 'text-slate-400 hover:bg-[#111722] hover:text-slate-200'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 truncate">
                      <Icon size={14} className={isActive ? 'text-emerald-400' : 'text-slate-400'} />
                      <span className="truncate">{item.label}</span>
                    </div>

                    {item.badge !== undefined && item.badge > 0 && (
                      <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                        {item.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Footer Info */}
      <div className="p-3 border-t border-[#1e293b] text-[10px] text-slate-500 font-mono">
        <div className="flex justify-between items-center">
          <span>SANDBOX MODE</span>
          <span className="text-emerald-400 font-bold">ACTIVE</span>
        </div>
        <div className="text-[9px] text-slate-600 mt-1 truncate">
          Engine: Local Windows 127.0.0.1
        </div>
      </div>
    </aside>
  );
};
