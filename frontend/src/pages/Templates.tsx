import { WorkspaceLayout } from '../layouts/WorkspaceLayout';
import { LayoutTemplate, Code2, Server, Database, Cloud, LineChart, Palette, ShieldAlert, TestTube } from 'lucide-react';
import { motion } from 'framer-motion';

const templates = [
  {
    id: 'frontend',
    title: 'Frontend Engineer',
    description: 'Scaffolds a modern React application with Tailwind CSS, Vite, and routing.',
    icon: Code2,
    color: 'text-blue-500'
  },
  {
    id: 'backend',
    title: 'Backend Architect',
    description: 'Designs and builds a scalable REST API using FastAPI and PostgreSQL.',
    icon: Server,
    color: 'text-green-500'
  },
  {
    id: 'data',
    title: 'Data Scientist',
    description: 'Cleans datasets, performs EDA, and trains an XGBoost predictive model.',
    icon: Database,
    color: 'text-purple-500'
  },
  {
    id: 'devops',
    title: 'DevOps Specialist',
    description: 'Configures automated CI/CD pipelines using GitHub Actions and Docker.',
    icon: Cloud,
    color: 'text-cyan-500'
  },
  {
    id: 'pm',
    title: 'Product Manager',
    description: 'Analyzes competitor feature sets and generates a comprehensive PRD.',
    icon: LineChart,
    color: 'text-orange-500'
  },
  {
    id: 'ux',
    title: 'UX Designer',
    description: 'Creates an accessible design system and reusable component library.',
    icon: Palette,
    color: 'text-pink-500'
  },
  {
    id: 'security',
    title: 'Security Auditor',
    description: 'Scans the codebase for vulnerabilities and applies automated patches.',
    icon: ShieldAlert,
    color: 'text-red-500'
  },
  {
    id: 'qa',
    title: 'QA Automation',
    description: 'Writes end-to-end tests using Playwright for all critical user flows.',
    icon: TestTube,
    color: 'text-yellow-500'
  }
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.06,
    }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 16, scale: 0.92 },
  visible: { 
    opacity: 1, 
    y: 0, 
    scale: 1,
    transition: {
      type: "spring" as const,
      stiffness: 260,
      damping: 20
    }
  }
};

export default function Templates() {
  return (
    <WorkspaceLayout>
      <div className="flex flex-col h-full max-w-5xl mx-auto w-full pt-12 px-6 pb-20">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: "easeOut" }}
        >
          <h1 className="text-3xl font-bold mb-3 flex items-center gap-3 tracking-tight text-do-text-primary">
            <LayoutTemplate className="w-8 h-8 text-do-text-secondary" />
            Agent Templates
          </h1>
          <p className="text-do-text-secondary mb-10 max-w-2xl leading-relaxed">
            Quick-start your autonomous missions. Select a template below to instantly load the agent with a pre-configured persona, toolset, and execution strategy tailored to specific domains.
          </p>
        </motion.div>

        <motion.div 
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4"
          variants={containerVariants}
          initial="hidden"
          animate="visible"
        >
          {templates.map((template) => {
            const Icon = template.icon;
            return (
              <motion.div
                key={template.id}
                variants={itemVariants}
                whileHover={{ y: -4, scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="p-6 bg-white dark:bg-do-bg-secondary rounded-2xl border border-do-bg-tertiary shadow-sm hover:shadow-md hover:border-do-text-tertiary cursor-pointer transition-all flex flex-col h-full"
              >
                <div className="w-12 h-12 rounded-full bg-do-bg-tertiary flex items-center justify-center mb-4">
                  <Icon className={`w-6 h-6 ${template.color}`} />
                </div>
                <h3 className="font-semibold mb-2 text-do-text-primary">{template.title}</h3>
                <p className="text-sm text-do-text-secondary flex-grow leading-relaxed">
                  {template.description}
                </p>
                <div className="mt-4 pt-4 border-t border-do-bg-tertiary flex justify-between items-center text-xs font-medium text-do-text-tertiary">
                  <span>Pre-configured</span>
                  <span className="text-do-active group-hover:underline">Use Template →</span>
                </div>
              </motion.div>
            );
          })}
        </motion.div>
      </div>
    </WorkspaceLayout>
  );
}
