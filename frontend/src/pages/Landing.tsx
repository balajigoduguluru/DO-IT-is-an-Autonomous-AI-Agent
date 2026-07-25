import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Sparkles, Zap, ShieldCheck, ArrowRight, Brain, Globe, Lock } from 'lucide-react';

export default function Landing() {
  const navigate = useNavigate();

  const scrollToSection = (e: React.MouseEvent<HTMLAnchorElement>, id: string) => {
    e.preventDefault();
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.2
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 30 },
    visible: { 
      opacity: 1, 
      y: 0,
      transition: { duration: 0.6, ease: [0.16, 1, 0.3, 1] as const }
    }
  };

  return (
    <div className="min-h-screen bg-do-bg-primary text-do-text-primary flex flex-col font-sans overflow-x-hidden">
      <header className="flex items-center justify-between p-6 max-w-7xl mx-auto w-full sticky top-0 bg-do-bg-primary/80 backdrop-blur-md z-50">
        <div className="flex items-center gap-2 font-bold text-xl tracking-tight cursor-pointer" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth'})}>
          DO IT
        </div>
        <nav className="flex items-center gap-8 text-sm font-medium">
          <a href="#features" onClick={(e) => scrollToSection(e, 'features')} className="text-do-text-secondary hover:text-do-text-primary transition-colors">Features</a>
          <a href="#about" onClick={(e) => scrollToSection(e, 'about')} className="text-do-text-secondary hover:text-do-text-primary transition-colors">About</a>
          <button 
            onClick={() => navigate('/dashboard')}
            className="bg-do-text-primary text-do-bg-primary px-5 py-2 rounded-do-radius-full hover:scale-95 transition-transform"
          >
            Launch App
          </button>
        </nav>
      </header>

      <main className="flex-1 flex flex-col w-full">
        {/* HERO SECTION */}
        <section className="min-h-[85vh] flex flex-col items-center justify-center text-center px-4 relative">
          {/* Subtle background glow */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-blue-500/5 rounded-full blur-[100px] pointer-events-none" />
          
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] as const }}
            className="max-w-4xl mx-auto relative z-10"
          >
            <motion.div 
              whileHover={{ scale: 1.05 }}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-do-bg-secondary text-sm font-medium text-do-text-secondary mb-8 border border-do-bg-tertiary cursor-pointer"
            >
              <Sparkles className="w-4 h-4 text-do-warning" />
              The Autonomous Layer for Modern Work
            </motion.div>
            
            <h1 className="text-6xl sm:text-7xl lg:text-[80px] font-bold tracking-tight mb-8 leading-[1.1]">
              Execute complex <br /> workflows instantly.
            </h1>
            
            <p className="text-xl text-do-text-secondary mb-12 max-w-2xl mx-auto leading-relaxed">
              DO IT translates high-level human intent into perfect digital execution. Just tell the agent what you want, and watch it orchestrate across your entire ecosystem.
            </p>
            
            <motion.button 
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => navigate('/dashboard')}
              className="bg-do-text-primary text-do-bg-primary text-lg font-medium px-8 py-4 rounded-do-radius-full shadow-2xl inline-flex items-center gap-3 hover:shadow-black/20 dark:hover:shadow-white/20 transition-all"
            >
              <Zap className="w-5 h-5" />
              Start Execution
            </motion.button>
          </motion.div>
        </section>

        {/* FEATURES SECTION */}
        <section id="features" className="py-32 px-4 border-t border-do-bg-tertiary/50 bg-[#fafafa] dark:bg-[#0a0a0a]">
          <div className="max-w-7xl mx-auto">
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              className="text-center mb-20"
            >
              <h2 className="text-4xl font-bold tracking-tight mb-4">Unprecedented Autonomy</h2>
              <p className="text-lg text-do-text-secondary max-w-2xl mx-auto">Built from the ground up to solve complex tasks with minimal human intervention, while keeping you perfectly informed.</p>
            </motion.div>

            <motion.div 
              variants={containerVariants}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: "-100px" }}
              className="grid grid-cols-1 md:grid-cols-3 gap-8"
            >
              <motion.div variants={itemVariants} whileHover={{ y: -5 }} className="p-8 rounded-[24px] bg-do-bg-primary border border-do-bg-tertiary shadow-sm group hover:shadow-md transition-all">
                <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <Brain className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-semibold mb-3">Transparent Reasoning</h3>
                <p className="text-do-text-secondary leading-relaxed">Watch the agent think in real-time. It explains its exact reasoning at every step, so you never have to guess what it's doing.</p>
              </motion.div>
              
              <motion.div variants={itemVariants} whileHover={{ y: -5 }} className="p-8 rounded-[24px] bg-do-bg-primary border border-do-bg-tertiary shadow-sm group hover:shadow-md transition-all">
                <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 dark:bg-emerald-900/20 dark:text-emerald-400 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <Zap className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-semibold mb-3">Lightning Execution</h3>
                <p className="text-do-text-secondary leading-relaxed">Our proprietary workflow engine processes sub-tasks in parallel, executing complex multi-step missions in absolute record time.</p>
              </motion.div>
              
              <motion.div variants={itemVariants} whileHover={{ y: -5 }} className="p-8 rounded-[24px] bg-do-bg-primary border border-do-bg-tertiary shadow-sm group hover:shadow-md transition-all">
                <div className="w-12 h-12 rounded-2xl bg-orange-50 text-orange-600 dark:bg-orange-900/20 dark:text-orange-400 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                  <ShieldCheck className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-semibold mb-3">Human-in-the-loop</h3>
                <p className="text-do-text-secondary leading-relaxed">High-risk actions like deployments or deletions require deliberate physical approval. You always retain absolute control.</p>
              </motion.div>
            </motion.div>
          </div>
        </section>

        {/* ABOUT SECTION */}
        <section id="about" className="py-32 px-4">
          <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center gap-16">
            <motion.div 
              initial={{ opacity: 0, x: -40 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.8, ease: "easeOut" }}
              className="flex-1"
            >
              <h2 className="text-4xl font-bold tracking-tight mb-6">Designed for a new paradigm of work.</h2>
              <p className="text-lg text-do-text-secondary mb-6 leading-relaxed">
                We believe that interacting with AI should no longer feel like chatting with a text box. It should feel like delegating to a highly capable senior engineer.
              </p>
              <p className="text-lg text-do-text-secondary mb-8 leading-relaxed">
                DO IT was built by a team of product engineers who were tired of managing complex prompts. We built a system that plans, reasons, and executes—allowing you to focus on high-level strategy while the agent handles the minutiae.
              </p>
              
              <ul className="space-y-4 mb-8">
                {['Bank-grade security encryption', 'SOC2 Type II Compliant', 'Zero data retention policies'].map((item, i) => (
                  <motion.li 
                    key={i}
                    initial={{ opacity: 0, x: -20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: i * 0.1 + 0.3 }}
                    className="flex items-center gap-3 text-do-text-primary font-medium"
                  >
                    <div className="w-6 h-6 rounded-full bg-do-active/10 text-do-active flex items-center justify-center">
                      <Lock size={12} />
                    </div>
                    {item}
                  </motion.li>
                ))}
              </ul>
            </motion.div>
            
            <motion.div 
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.8, ease: "easeOut" }}
              className="flex-1 w-full aspect-square md:aspect-[4/3] rounded-[32px] bg-gradient-to-br from-gray-100 to-gray-200 dark:from-do-bg-tertiary dark:to-do-bg-secondary border border-do-bg-tertiary relative overflow-hidden flex items-center justify-center"
            >
              <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 mix-blend-overlay"></div>
              <Globe className="w-32 h-32 text-do-text-tertiary/30 animate-pulse" />
            </motion.div>
          </div>
        </section>

        {/* CTA SECTION */}
        <section className="py-32 px-4 text-center">
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8 }}
            className="max-w-3xl mx-auto"
          >
            <h2 className="text-5xl font-bold tracking-tight mb-8">Ready to do less?</h2>
            <button 
              onClick={() => navigate('/dashboard')}
              className="bg-do-text-primary text-do-bg-primary text-lg font-medium px-10 py-5 rounded-do-radius-full shadow-2xl hover:scale-95 transition-transform inline-flex items-center gap-3"
            >
              Get Started Now <ArrowRight size={20} />
            </button>
          </motion.div>
        </section>
      </main>
      
      <footer className="py-12 border-t border-do-bg-tertiary">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4 text-do-text-tertiary text-sm">
          <div className="flex items-center gap-2 font-bold text-do-text-primary">
            DO IT
          </div>
          <div className="flex gap-6">
            <a href="#" className="hover:text-do-text-primary transition-colors">Privacy</a>
            <a href="#" className="hover:text-do-text-primary transition-colors">Terms</a>
            <a href="#" className="hover:text-do-text-primary transition-colors">Security</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
