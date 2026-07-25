import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  MessageSquare, 
  FolderGit2, 
  CheckSquare, 
  Building2,
  ChevronLeft,
  ChevronRight,
  Download
} from 'lucide-react';
import { cn } from '../utils/utils';
import { useHistory } from '../hooks/useHistory';
import { useUser } from '../hooks/useUser';

export function Sidebar() {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const location = useLocation();

  const navItems = [
    { icon: MessageSquare, label: 'Dashboard', path: '/dashboard' },
    { icon: FolderGit2, label: 'History', path: '/history' },
    { icon: CheckSquare, label: 'Templates', path: '/templates' },
    { icon: Building2, label: 'Settings', path: '/settings' },
  ];

  const { history } = useHistory();
  const { userName, email } = useUser();
  
  const recentItems = history.slice(0, 3); // Just show top 3 recent items

  return (
    <motion.aside
      initial={{ width: 260 }}
      animate={{ width: isCollapsed ? 64 : 260 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      className="h-screen bg-do-bg-secondary border-r border-do-bg-tertiary flex flex-col relative z-20 flex-shrink-0"
    >
      {/* Brand & Workspace */}
      <div className="h-16 px-4 flex items-center gap-3 shrink-0 overflow-hidden relative">
        <Link to="/dashboard" className="flex items-center gap-3 w-full hover:opacity-80 transition-opacity">
          <div className="w-5 h-5 bg-do-accent rounded-sm shrink-0 flex items-center justify-center text-do-bg-primary text-xs font-bold shadow-do-soft">
            +
          </div>
          <motion.span 
            initial={false}
            animate={{ opacity: isCollapsed ? 0 : 1 }}
            className="font-semibold tracking-wide whitespace-nowrap text-[15px]"
          >
            New chat
          </motion.span>
        </Link>
        
        {/* Collapse toggle */}
        <button 
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="absolute right-4 p-1 rounded-do-sm hover:bg-do-bg-tertiary text-do-text-secondary hover:text-do-text-primary transition-colors"
        >
          {isCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      </div>

      {/* Primary Nav */}
      <nav className="p-2 space-y-1 shrink-0 overflow-hidden">
        {navItems.map((item) => {
          const active = location.pathname === item.path;
          return (
            <Link
              key={item.label}
              to={item.path}
              className={cn(
                "w-full flex items-center gap-3 px-2 py-2 rounded-do-sm transition-all duration-150 relative group outline-none focus-visible:ring-2 focus-visible:ring-do-active focus-visible:ring-offset-2 focus-visible:ring-offset-do-bg-secondary",
                active ? "text-do-text-primary" : "text-do-text-secondary hover:bg-do-bg-tertiary hover:text-do-text-primary"
              )}
            >
              {active && (
                <motion.div 
                  layoutId="active-indicator"
                  className="absolute left-0 top-1 bottom-1 w-0.5 bg-do-accent rounded-r-full"
                />
              )}
              <item.icon size={16} strokeWidth={1.5} className="shrink-0" />
              <motion.span 
                initial={false}
                animate={{ opacity: isCollapsed ? 0 : 1 }}
                className="text-[13px] font-medium whitespace-nowrap"
              >
                {item.label}
              </motion.span>
            </Link>
          );
        })}
      </nav>

      {/* Recents Section */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden p-2 mt-4">
        <motion.div animate={{ opacity: isCollapsed ? 0 : 1 }}>
          <div className="text-[10px] font-bold text-do-text-tertiary uppercase tracking-wider px-2 mb-3">
            RECENTS
          </div>
          {recentItems.length === 0 ? (
            <div className="px-2 py-2 text-[11px] text-do-text-tertiary">
              No recent activity.
            </div>
          ) : (
            recentItems.map((item) => (
              <button 
                key={item.id} 
                className="w-full flex flex-col items-start px-2 py-2 rounded-do-sm hover:bg-do-bg-tertiary text-left transition-colors mb-1"
              >
                <span className="text-[13px] font-semibold text-do-text-primary truncate w-full">{item.title}</span>
                <span className="text-[11px] text-do-text-tertiary truncate w-full mt-0.5">{item.desc}</span>
              </button>
            ))
          )}
        </motion.div>
      </div>

      {/* User Profile */}
      <div className="p-4 border-t border-do-bg-tertiary shrink-0 overflow-hidden flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-do-text-primary text-do-bg-primary flex items-center justify-center font-semibold text-sm shrink-0 uppercase">
          {userName.charAt(0)}
        </div>
        <motion.div 
          initial={false}
          animate={{ opacity: isCollapsed ? 0 : 1 }}
          className="flex-1 flex flex-col justify-center min-w-0"
        >
          <span className="text-[13px] font-semibold text-do-text-primary truncate">{userName}</span>
          <span className="text-[11px] text-do-text-secondary truncate">{email}</span>
        </motion.div>
        <motion.button 
          initial={false}
          animate={{ opacity: isCollapsed ? 0 : 1 }}
          className="text-do-text-secondary hover:text-do-text-primary p-1"
        >
          <Download size={14} />
        </motion.button>
      </div>
    </motion.aside>
  );
}
